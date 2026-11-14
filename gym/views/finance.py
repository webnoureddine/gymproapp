from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..forms import ExpenseForm
from ..models import Expense, ExpenseCategory, Member, Payment
from ..utils import csv_response, day_range, parse_period, perm_required


def _payments(request):
    start, end, period = parse_period(request, "today")
    a, b = day_range(start, end)
    qs = Payment.objects.filter(paid_at__gte=a, paid_at__lt=b).select_related("member", "received_by", "subscription")
    if request.GET.get("method"):
        qs = qs.filter(method=request.GET["method"])
    if request.GET.get("kind"):
        qs = qs.filter(kind=request.GET["kind"])
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(member__first_name__icontains=q) | Q(member__last_name__icontains=q)
                       | Q(member__code__iexact=q) | Q(reference__icontains=q))
    return qs, start, end, period


@perm_required("payments")
def payment_list(request):
    qs, start, end, period = _payments(request)
    by_method = {r["method"]: r["s"] for r in qs.values("method").annotate(s=Sum("amount"))}
    methods = [(k, v, by_method.get(k, 0)) for k, v in Payment.METHOD_CHOICES if by_method.get(k)]
    return render(request, "gym/finance/payments.html", {
        "page": Paginator(qs, 30).get_page(request.GET.get("page")),
        "total": qs.aggregate(s=Sum("amount"))["s"] or 0, "count": qs.count(),
        "methods": methods, "start": start, "end": end, "period": period,
        "METHODS": Payment.METHOD_CHOICES, "KINDS": Payment.KIND_CHOICES,
    })


@perm_required("payments")
def payment_export(request):
    qs, start, end, _p = _payments(request)
    rows = [[p.number, timezone.localtime(p.paid_at).strftime("%d/%m/%Y %H:%M"), p.member.full_name if p.member else "",
             p.get_kind_display(), p.get_method_display(), p.reference, p.amount,
             p.received_by.display_name if p.received_by else ""] for p in qs]
    return csv_response(f"payments_{start}_{end}.csv",
                        [_("Receipt number"), _("Date"), _("Member"), _("Type"), _("Method"), _("Reference"), _("Amount"), _("Received by")], rows)


@perm_required("debts")
def debt_list(request):
    members = Member.objects.alive().prefetch_related("subscriptions__payments", "sales__payments")
    q = request.GET.get("q", "").strip()
    if q:
        members = members.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(code__iexact=q) | Q(phone__icontains=q))
    rows = [(m, m.balance_due) for m in members]
    rows = sorted([r for r in rows if r[1] > 0], key=lambda r: -r[1])
    if request.GET.get("export"):
        return csv_response("debts.csv", [_("Member ID"), _("Name"), _("Phone"), _("Debt")],
                            [[m.code, m.full_name, m.phone, d] for m, d in rows])
    return render(request, "gym/finance/debts.html", {"rows": rows, "total": sum((d for _m, d in rows), 0)})


@perm_required("expenses")
def expense_list(request):
    start, end, period = parse_period(request, "month")
    form = ExpenseForm(request.POST or None, initial={"date": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        e = form.save(commit=False)
        e.created_by = request.user
        e.save()
        messages.success(request, _("Expense added."))
        return redirect(request.get_full_path())
    qs = Expense.objects.filter(date__gte=start, date__lte=end).select_related("category", "created_by")
    if request.GET.get("category"):
        qs = qs.filter(category_id=request.GET["category"])
    if request.GET.get("export"):
        return csv_response(f"expenses_{start}_{end}.csv", [_("Date"), _("Category"), _("Description"), _("Method"), _("Amount")],
                            [[e.date, e.category or "", e.label, e.get_method_display(), e.amount] for e in qs])
    by_cat = qs.values("category__name").annotate(s=Sum("amount")).order_by("-s")
    return render(request, "gym/finance/expenses.html", {
        "form": form, "page": Paginator(qs, 30).get_page(request.GET.get("page")),
        "total": qs.aggregate(s=Sum("amount"))["s"] or 0, "by_cat": by_cat,
        "categories": ExpenseCategory.objects.all(), "start": start, "end": end, "period": period,
    })


@perm_required("expenses")
@require_POST
def expense_delete(request, pk):
    get_object_or_404(Expense, pk=pk).delete()
    messages.success(request, _("Expense deleted."))
    return redirect("expense_list")
