import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from ..models import CheckIn, Expense, GymSettings, Member, Payment, Product, Subscription
from ..utils import day_range


def member_status_buckets():
    """Count members per status (python-side: status depends on several rules)."""
    counts = {"active": 0, "expiring": 0, "expired": 0, "frozen": 0, "none": 0, "upcoming": 0}
    expiring = []
    members = Member.objects.alive().prefetch_related("subscriptions__payments", "sales__payments")
    debtors = 0
    total_debt = 0
    for m in members:
        st = m.status()
        counts[st] = counts.get(st, 0) + 1
        if st == "expiring":
            expiring.append(m)
        due = m.balance_due
        if due > 0:
            debtors += 1
            total_debt += due
    expiring.sort(key=lambda m: m.current_subscription().end_date)
    return counts, expiring, debtors, total_debt


@login_required
def dashboard(request):
    t = timezone.localdate()
    a, b = day_range(t, t)
    month_start = t.replace(day=1)
    ma, mb = day_range(month_start, t)

    counts, expiring, debtors, total_debt = member_status_buckets()
    today_revenue = Payment.objects.filter(paid_at__gte=a, paid_at__lt=b).aggregate(s=Sum("amount"))["s"] or 0
    month_revenue = Payment.objects.filter(paid_at__gte=ma, paid_at__lt=mb).aggregate(s=Sum("amount"))["s"] or 0
    month_expenses = Expense.objects.filter(date__gte=month_start, date__lte=t).aggregate(s=Sum("amount"))["s"] or 0
    today_checkins = CheckIn.objects.filter(at__gte=a, at__lt=b, allowed=True).count()
    new_members_month = Member.objects.alive().filter(joined_at__gte=month_start).count()

    # charts: revenue last 12 months, check-ins last 14 days
    year_ago = (t.replace(day=1) - timedelta(days=330)).replace(day=1)
    ya, _ = day_range(year_ago, t)
    rev = {
        r["m"].date() if hasattr(r["m"], "date") else r["m"]: float(r["s"])
        for r in Payment.objects.filter(paid_at__gte=ya).annotate(m=TruncMonth("paid_at")).values("m").annotate(s=Sum("amount"))
    }
    exp = {
        r["m"]: float(r["s"])
        for r in Expense.objects.filter(date__gte=year_ago).annotate(m=TruncMonth("date")).values("m").annotate(s=Sum("amount"))
    }
    months, d = [], year_ago
    while d <= t:
        months.append(d)
        d = (d + timedelta(days=32)).replace(day=1)
    rev_chart = {
        "labels": [m.strftime("%m/%y") for m in months],
        "revenue": [rev.get(m, 0) for m in months],
        "expenses": [exp.get(m, 0) for m in months],
    }
    two_weeks = t - timedelta(days=13)
    tw, _ = day_range(two_weeks, t)
    ci = {
        r["d"]: r["c"]
        for r in CheckIn.objects.filter(at__gte=tw, allowed=True).annotate(d=TruncDate("at")).values("d").annotate(c=Count("id"))
    }
    days = [two_weeks + timedelta(days=i) for i in range(14)]
    ci_chart = {"labels": [x.strftime("%d/%m") for x in days], "values": [ci.get(x, 0) for x in days]}

    ctx = {
        "counts": counts,
        "expiring": expiring[:8],
        "debtors": debtors,
        "total_debt": total_debt,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "month_expenses": month_expenses,
        "month_profit": month_revenue - month_expenses,
        "today_checkins": today_checkins,
        "new_members_month": new_members_month,
        "recent_checkins": CheckIn.objects.select_related("member").filter(at__gte=a)[:8],
        "recent_payments": Payment.objects.select_related("member")[:6],
        "low_stock": Product.objects.filter(is_active=True, stock__lte=F("low_stock"))[:6],
        "rev_chart": json.dumps(rev_chart),
        "ci_chart": json.dumps(ci_chart),
        "gym_cfg": GymSettings.get(),
    }
    return render(request, "gym/dashboard.html", ctx)
