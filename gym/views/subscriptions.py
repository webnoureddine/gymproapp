from datetime import timedelta

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..forms import OtherPaymentForm, PaymentForm, SubscriptionForm
from ..models import GymSettings, Member, Payment, Subscription, create_subscription
from ..utils import flash_form_errors, perm_required


def apply_subscription_form(request, member, form):
    """Create subscription + payment + optional registration/insurance fees. Returns first payment."""
    gym = GymSettings.get()
    d = form.cleaned_data
    with transaction.atomic():
        sub, pay = create_subscription(
            member, d["plan"], request.user, start_date=d["start_date"], discount=d["discount"], paid=d["paid"],
            method=d["method"], reference=d.get("reference", ""), notes=d.get("notes", ""), price=d["price"],
        )
        if d.get("add_registration") and gym.registration_fee > 0:
            Payment.objects.create(member=member, kind="registration", amount=gym.registration_fee,
                                   method=d["method"], received_by=request.user)
        if d.get("add_insurance") and gym.insurance_fee > 0:
            Payment.objects.create(member=member, kind="insurance", amount=gym.insurance_fee,
                                   method=d["method"], received_by=request.user)
            start = max(member.insurance_until or timezone.localdate(), timezone.localdate())
            member.insurance_until = start + timedelta(days=365)
            member.save(update_fields=["insurance_until"])
    if sub.due > 0:
        messages.warning(request, _("Remaining to pay: %(amount)s") % {"amount": f"{sub.due:,.0f}".replace(",", " ")})
    return sub, pay


@perm_required("payments")
@require_POST
def subscription_create(request, member_pk):
    member = get_object_or_404(Member, pk=member_pk)
    form = SubscriptionForm(request.POST, member=member, prefix="sub")
    if form.is_valid():
        sub, pay = apply_subscription_form(request, member, form)
        messages.success(request, _("Subscription %(plan)s added until %(date)s.") % {
            "plan": sub.plan_name, "date": sub.end_date.strftime("%d/%m/%Y")})
        if pay and request.POST.get("print") == "1":
            return redirect("receipt", pk=pay.pk)
    else:
        flash_form_errors(request, form)
    return redirect("member_detail", pk=member.pk)


@perm_required("payments")
@require_POST
def subscription_pay(request, pk):
    sub = get_object_or_404(Subscription, pk=pk)
    form = PaymentForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        pay = Payment.objects.create(member=sub.member, subscription=sub, kind="subscription", amount=d["amount"],
                                     method=d["method"], reference=d["reference"], note=d["note"], received_by=request.user)
        messages.success(request, _("Payment recorded."))
        if request.POST.get("print") == "1":
            return redirect("receipt", pk=pay.pk)
    else:
        flash_form_errors(request, form)
    return redirect("member_detail", pk=sub.member_id)


@perm_required("payments")
@require_POST
def member_other_payment(request, member_pk):
    member = get_object_or_404(Member, pk=member_pk)
    form = OtherPaymentForm(request.POST)
    if form.is_valid():
        pay = form.save(commit=False)
        pay.member = member
        pay.received_by = request.user
        pay.save()
        if pay.kind == "insurance":
            start = max(member.insurance_until or timezone.localdate(), timezone.localdate())
            member.insurance_until = start + timedelta(days=365)
            member.save(update_fields=["insurance_until"])
        messages.success(request, _("Payment recorded."))
        if request.POST.get("print") == "1":
            return redirect("receipt", pk=pay.pk)
    else:
        flash_form_errors(request, form)
    return redirect("member_detail", pk=member.pk)


@perm_required("payments")
@require_POST
def subscription_action(request, pk, action):
    sub = get_object_or_404(Subscription, pk=pk)
    if action == "freeze":
        sub.freeze()
        messages.success(request, _("Subscription paused. Days will be added back when you resume it."))
    elif action == "unfreeze":
        sub.unfreeze()
        messages.success(request, _("Subscription resumed. New end date: %(date)s") % {"date": sub.end_date.strftime("%d/%m/%Y")})
    elif action == "cancel":
        if not request.user.can("plans"):
            messages.error(request, _("You are not allowed to do this."))
        else:
            sub.cancelled = True
            sub.save(update_fields=["cancelled"])
            messages.success(request, _("Subscription cancelled."))
    elif action == "extend":
        try:
            days = int(request.POST.get("days", 0))
        except ValueError:
            days = 0
        if days:
            sub.end_date += timedelta(days=days)
            sub.save(update_fields=["end_date"])
            messages.success(request, _("End date changed to %(date)s") % {"date": sub.end_date.strftime("%d/%m/%Y")})
    return redirect("member_detail", pk=sub.member_id)


@perm_required("payments")
def receipt(request, pk):
    pay = get_object_or_404(Payment.objects.select_related("member", "subscription", "received_by", "sale"), pk=pk)
    fmt = request.GET.get("format", "ticket")
    return render(request, "gym/receipt.html", {"p": pay, "fmt": fmt, "sub": pay.subscription, "sale": pay.sale})


@perm_required("payments")
@require_POST
def payment_delete(request, pk):
    pay = get_object_or_404(Payment, pk=pk)
    if not request.user.is_owner:
        messages.error(request, _("Only the owner can delete a payment."))
    else:
        member_id = pay.member_id
        pay.delete()
        messages.success(request, _("Payment deleted."))
    nxt = request.POST.get("next", "")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("payment_list")
