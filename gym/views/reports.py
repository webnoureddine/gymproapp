import json
from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate
from django.shortcuts import render
from django.utils.translation import gettext as _

from ..models import CheckIn, Expense, Member, Payment, SaleItem, Subscription
from ..utils import csv_response, day_range, parse_period, perm_required


@perm_required("reports")
def reports(request):
    start, end, period = parse_period(request, "month")
    a, b = day_range(start, end)
    pays = Payment.objects.filter(paid_at__gte=a, paid_at__lt=b)
    exps = Expense.objects.filter(date__gte=start, date__lte=end)

    revenue = pays.aggregate(s=Sum("amount"))["s"] or Decimal(0)
    expenses = exps.aggregate(s=Sum("amount"))["s"] or Decimal(0)
    kinds = dict(Payment.KIND_CHOICES)
    methods = dict(Payment.METHOD_CHOICES)
    by_kind = [(kinds.get(r["kind"], r["kind"]), r["s"]) for r in pays.values("kind").annotate(s=Sum("amount")).order_by("-s")]
    by_method = [(methods.get(r["method"], r["method"]), r["s"]) for r in pays.values("method").annotate(s=Sum("amount")).order_by("-s")]
    by_plan = (pays.filter(subscription__isnull=False).values("subscription__plan_name")
               .annotate(s=Sum("amount"), n=Count("subscription", distinct=True)).order_by("-s"))
    by_cat = exps.values("category__name").annotate(s=Sum("amount")).order_by("-s")
    by_staff = pays.values("received_by__username").annotate(s=Sum("amount"), n=Count("id")).order_by("-s")
    top_products = (SaleItem.objects.filter(sale__created_at__gte=a, sale__created_at__lt=b)
                    .values("product_name").annotate(q=Sum("quantity")).order_by("-q")[:8])

    new_members = Member.objects.filter(joined_at__gte=start, joined_at__lte=end)
    new_subs = Subscription.objects.filter(created_at__gte=a, created_at__lt=b, cancelled=False)
    renewals = new_subs.exclude(member__in=new_members).count()

    ci = CheckIn.objects.filter(at__gte=a, at__lt=b, allowed=True)
    hours = {r["h"]: r["c"] for r in ci.annotate(h=ExtractHour("at")).values("h").annotate(c=Count("id"))}
    wdays = {r["w"]: r["c"] for r in ci.annotate(w=ExtractWeekDay("at")).values("w").annotate(c=Count("id"))}
    # Django: 1=Sunday ... 7=Saturday -> show Saturday first (Algerian week)
    wd_order = [7, 1, 2, 3, 4, 5, 6]
    wd_names = {1: _("Sun"), 2: _("Mon"), 3: _("Tue"), 4: _("Wed"), 5: _("Thu"), 6: _("Fri"), 7: _("Sat")}

    # daily revenue curve
    daily = OrderedDict()
    d = start
    while d <= end and len(daily) < 400:
        daily[d] = 0
        d += timedelta(days=1)
    for r in pays.annotate(d=TruncDate("paid_at")).values("d").annotate(s=Sum("amount")):
        if r["d"] in daily:
            daily[r["d"]] = float(r["s"])

    if request.GET.get("export"):
        rows = [[_("Revenue"), revenue], [_("Expenses"), expenses], [_("Profit"), revenue - expenses], [], [_("By type")]]
        rows += [[k, v] for k, v in by_kind] + [[], [_("By method")]] + [[k, v] for k, v in by_method]
        rows += [[], [_("By plan")]] + [[r["subscription__plan_name"], r["s"]] for r in by_plan]
        rows += [[], [_("Expenses by category")]] + [[r["category__name"] or "-", r["s"]] for r in by_cat]
        return csv_response(f"report_{start}_{end}.csv", [_("Report"), f"{start} → {end}"], rows)

    charts = {
        "daily": {"labels": [x.strftime("%d/%m") for x in daily], "values": list(daily.values())},
        "hours": {"labels": [f"{h}h" for h in range(6, 24)], "values": [hours.get(h, 0) for h in range(6, 24)]},
        "wdays": {"labels": [str(wd_names[w]) for w in wd_order], "values": [wdays.get(w, 0) for w in wd_order]},
        "kinds": {"labels": [str(k) for k, _v in by_kind], "values": [float(v) for _k, v in by_kind]},
        "methods": {"labels": [str(k) for k, _v in by_method], "values": [float(v) for _k, v in by_method]},
    }
    return render(request, "gym/reports.html", {
        "start": start, "end": end, "period": period,
        "revenue": revenue, "expenses": expenses, "profit": revenue - expenses,
        "by_kind": by_kind, "by_method": by_method, "by_plan": by_plan, "by_cat": by_cat, "by_staff": by_staff,
        "top_products": top_products, "new_members": new_members.count(), "renewals": renewals,
        "visits": ci.count(), "unique_visitors": ci.values("member").distinct().count(),
        "charts": json.dumps(charts),
    })
