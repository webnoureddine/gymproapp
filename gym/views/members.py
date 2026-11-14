import base64
import io

from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..forms import MemberForm, OtherPaymentForm, PaymentForm, SubscriptionForm
from ..models import Activity, GymSettings, Member, Plan, next_start_date
from ..templatetags.gym_tags import status_label
from ..utils import csv_response, perm_required


def _search(qs, q):
    q = (q or "").strip()
    if not q:
        return qs
    cond = Q()
    for word in q.split():
        cond &= (Q(first_name__icontains=word) | Q(last_name__icontains=word) | Q(code__iexact=word)
                 | Q(phone__icontains=word) | Q(national_id__icontains=word))
    return qs.filter(cond | Q(code__iexact=q))


def _filtered(request):
    archived = request.GET.get("archived") == "1"
    qs = Member.objects.filter(is_archived=archived)
    qs = _search(qs, request.GET.get("q"))
    if request.GET.get("gender") in ("M", "F"):
        qs = qs.filter(gender=request.GET["gender"])
    if request.GET.get("activity"):
        qs = qs.filter(subscriptions__plan__activity_id=request.GET["activity"]).distinct()
    qs = qs.prefetch_related("subscriptions__payments", "sales__payments")
    members = list(qs)
    status = request.GET.get("status")
    if status:
        members = [m for m in members if m.status() == status]
    if request.GET.get("debt") == "1":
        members = [m for m in members if m.balance_due > 0]
    sort = request.GET.get("sort", "new")
    if sort == "name":
        members.sort(key=lambda m: (m.last_name.lower(), m.first_name.lower()))
    elif sort == "end":
        members.sort(key=lambda m: (m.current_subscription().end_date if m.current_subscription() else timezone.localdate().replace(year=1)))
    return members


@perm_required("members_view")
def member_list(request):
    members = _filtered(request)
    page = Paginator(members, 25).get_page(request.GET.get("page"))
    return render(request, "gym/members/list.html", {
        "page": page, "total": len(members), "activities": Activity.objects.filter(is_active=True),
    })


@perm_required("members_view")
def member_export(request):
    rows = []
    for m in _filtered(request):
        sub = m.current_subscription()
        rows.append([
            m.code, m.last_name, m.first_name, m.get_gender_display(), m.phone, m.email,
            m.birth_date or "", sub.plan_name if sub else "", sub.end_date if sub else "",
            status_label(m.status()), m.balance_due, m.joined_at,
        ])
    header = [_("Member ID"), _("Last name"), _("First name"), _("Gender"), _("Phone"), _("Email"), _("Birth date"),
              _("Plan"), _("End date"), _("Status"), _("Debt"), _("Join date")]
    return csv_response(f"members_{timezone.localdate()}.csv", header, rows)


def _save_webcam_photo(request, member):
    data = request.POST.get("webcam_photo", "")
    if data.startswith("data:image"):
        header, b64 = data.split(",", 1)
        member.photo.save(f"{member.code or 'm'}.jpg", ContentFile(base64.b64decode(b64)), save=True)


@perm_required("members")
def member_create(request):
    gym = GymSettings.get()
    form = MemberForm(request.POST or None, request.FILES or None)
    sub_form = SubscriptionForm(request.POST or None, prefix="sub",
                                initial={"start_date": timezone.localdate(), "method": "cash",
                                         "add_registration": gym.registration_fee > 0,
                                         "add_insurance": gym.insurance_fee > 0})
    if request.method == "POST":
        with_sub = request.POST.get("with_subscription") == "1"
        if form.is_valid() and (not with_sub or sub_form.is_valid()):
            member = form.save(commit=False)
            member.created_by = request.user
            member.save()
            _save_webcam_photo(request, member)
            if with_sub:
                from .subscriptions import apply_subscription_form
                apply_subscription_form(request, member, sub_form)
            messages.success(request, _("Member %(name)s created.") % {"name": member.full_name})
            return redirect("member_detail", pk=member.pk)
    return render(request, "gym/members/form.html", {
        "form": form, "sub_form": sub_form, "plans": Plan.objects.filter(is_active=True), "creating": True,
    })


@perm_required("members")
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    form = MemberForm(request.POST or None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        _save_webcam_photo(request, member)
        messages.success(request, _("Changes saved."))
        return redirect("member_detail", pk=member.pk)
    return render(request, "gym/members/form.html", {"form": form, "member": member, "creating": False})


@perm_required("members_view")
def member_detail(request, pk):
    member = get_object_or_404(Member.objects.prefetch_related("subscriptions__payments", "sales__payments"), pk=pk)
    sub = member.current_subscription()
    subs = list(member.subscriptions.all())
    t = timezone.localdate()
    sub_form = SubscriptionForm(member=member, prefix="sub", initial={"start_date": next_start_date(member), "method": "cash"})
    return render(request, "gym/members/detail.html", {
        "m": member,
        "sub": sub,
        "subs": subs,
        "payments": member.payments.select_related("received_by")[:50],
        "checkins": member.checkins.select_related("by")[:30],
        "visits_month": member.checkins.filter(allowed=True, at__date__gte=t.replace(day=1)).count(),
        "sales": member.sales.prefetch_related("items")[:20],
        "sub_form": sub_form,
        "pay_form": PaymentForm(),
        "other_form": OtherPaymentForm(),
        "plans": Plan.objects.filter(is_active=True),
    })


@perm_required("members")
@require_POST
def member_archive(request, pk):
    member = get_object_or_404(Member, pk=pk)
    member.is_archived = not member.is_archived
    member.save(update_fields=["is_archived"])
    messages.success(request, _("Member archived.") if member.is_archived else _("Member restored."))
    return redirect("member_detail", pk=pk)


@perm_required("members")
@require_POST
def member_delete(request, pk):
    if not request.user.is_owner:
        messages.error(request, _("Only the owner can delete a member permanently."))
        return redirect("member_detail", pk=pk)
    member = get_object_or_404(Member, pk=pk)
    member.delete()
    messages.success(request, _("Member deleted."))
    return redirect("member_list")


@perm_required("members_view")
def member_card(request, pk):
    import qrcode
    import qrcode.image.svg

    member = get_object_or_404(Member, pk=pk)
    img = qrcode.make(member.code, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=1)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode()
    svg = svg[svg.find("<svg"):]
    return render(request, "gym/members/card.html", {"m": member, "qr_svg": svg, "sub": member.current_subscription()})


@perm_required("members_view")
def member_search_api(request):
    """Autocomplete for check-in, POS and payments."""
    q = request.GET.get("q", "")
    qs = _search(Member.objects.alive(), q).prefetch_related("subscriptions__payments", "sales__payments")[:10]
    data = []
    for m in qs:
        sub = m.current_subscription()
        data.append({
            "id": m.pk, "code": m.code, "name": m.full_name, "phone": m.phone,
            "photo": m.photo.url if m.photo else "", "initials": m.initials,
            "status": m.status(), "status_label": status_label(m.status()),
            "plan": sub.plan_name if sub else "", "end": sub.end_date.strftime("%d/%m/%Y") if sub else "",
            "debt": float(m.balance_due),
        })
    return JsonResponse({"results": data})
