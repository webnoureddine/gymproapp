import csv
from datetime import date, datetime, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _


def perm_required(perm):
    """@perm_required('payments') -> must be logged in AND have the permission."""

    def deco(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.can(perm):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return deco


def owner_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_owner:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def csv_response(filename, header, rows):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.write("﻿")  # BOM so Excel opens Arabic/French accents correctly
    w = csv.writer(resp, delimiter=";")
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return resp


def parse_period(request, default="month"):
    """Read ?period=today|week|month|year|custom&start=&end= -> (start_date, end_date, period)."""
    t = timezone.localdate()
    period = request.GET.get("period", default)
    start = end = t
    if period == "today":
        pass
    elif period == "yesterday":
        start = end = t - timedelta(days=1)
    elif period == "week":
        start = t - timedelta(days=t.weekday())
    elif period == "month":
        start = t.replace(day=1)
    elif period == "last_month":
        end = t.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
    elif period == "year":
        start = t.replace(month=1, day=1)
    elif period == "all":
        start = date(2000, 1, 1)
    else:
        period = "custom"
        try:
            start = datetime.strptime(request.GET.get("start", ""), "%Y-%m-%d").date()
        except ValueError:
            start = t.replace(day=1)
        try:
            end = datetime.strptime(request.GET.get("end", ""), "%Y-%m-%d").date()
        except ValueError:
            end = t
    return start, end, period


def day_range(start, end):
    """Timezone-aware datetimes covering [start 00:00, end 23:59]."""
    tz = timezone.get_current_timezone()
    a = timezone.make_aware(datetime.combine(start, datetime.min.time()), tz)
    b = timezone.make_aware(datetime.combine(end + timedelta(days=1), datetime.min.time()), tz)
    return a, b


def flash_form_errors(request, form):
    for field, errs in form.errors.items():
        label = form.fields[field].label if field in form.fields else ""
        for e in errs:
            messages.error(request, f"{label}: {e}" if label else e)
