from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..models import CheckIn, Member
from ..templatetags.gym_tags import money, status_label
from ..utils import day_range, perm_required

REASONS = {
    "archived": "Member is archived",
    "no_subscription": "No subscription",
    "frozen": "Subscription is paused",
    "upcoming": "Subscription has not started yet",
    "expired": "Subscription expired",
    "debt": "Unpaid balance",
    "already_today": "Already checked in today",
}


def reason_text(reason):
    if reason.startswith("forced:"):
        return _("Entry forced by staff") + " — " + _(REASONS.get(reason[7:], reason[7:]))
    return _(REASONS[reason]) if reason in REASONS else reason


@perm_required("checkin")
def checkin_page(request):
    t = timezone.localdate()
    a, b = day_range(t, t)
    today_qs = CheckIn.objects.filter(at__gte=a, at__lt=b)
    return render(request, "gym/checkin.html", {
        "recent": today_qs.select_related("member", "subscription")[:30],
        "count_today": today_qs.filter(allowed=True).values("member").distinct().count(),
        "denied_today": today_qs.filter(allowed=False).count(),
    })


@perm_required("checkin")
@require_POST
def checkin_api(request):
    from ..models import checkin_member

    code = (request.POST.get("code") or "").strip()
    member = None
    if request.POST.get("member_id"):
        member = Member.objects.filter(pk=request.POST["member_id"]).first()
    elif code:
        member = Member.objects.filter(code__iexact=code).first() or Member.objects.filter(phone=code).first()
    if member is None:
        return JsonResponse({"ok": False, "found": False, "message": _("Member not found")})
    ci, ok, reason = checkin_member(member, request.user, force=request.POST.get("force") == "1")
    sub = ci.subscription
    if sub:
        sub.refresh_from_db()
    return JsonResponse({
        "ok": ok, "found": True, "reason": reason, "message": reason_text(reason) if reason else _("Welcome!"),
        "member": {
            "id": member.pk, "code": member.code, "name": member.full_name, "initials": member.initials,
            "photo": member.photo.url if member.photo else "", "status": member.status(),
            "status_label": status_label(member.status()), "medical": member.medical_notes,
            "debt": money(member.balance_due) if member.balance_due > 0 else "",
            "insurance_ok": member.insurance_ok,
        },
        "sub": {
            "plan": sub.plan_name, "end": sub.end_date.strftime("%d/%m/%Y"), "days_left": sub.days_left,
            "sessions_left": sub.sessions_left,
        } if sub else None,
        "time": timezone.localtime(ci.at).strftime("%H:%M"),
    })
