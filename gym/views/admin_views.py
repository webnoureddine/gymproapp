import io

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core import management
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from ..forms import GymSettingsForm, LicenseForm, StaffForm
from ..license import license_status, read_key, refresh, server_enabled, vendor_contact
from ..models import GymSettings
from ..utils import owner_required

User = get_user_model()


@owner_required
def staff_list(request):
    return render(request, "gym/admin/staff.html", {"users": User.objects.order_by("-is_active", "role", "username")})


@owner_required
def staff_edit(request, pk=None):
    obj = get_object_or_404(User, pk=pk) if pk else None
    form = StaffForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        u = form.save(commit=False)
        if obj and obj.pk == request.user.pk:
            u.is_active = True  # never lock yourself out
            u.role = User.OWNER if request.user.role == User.OWNER else u.role
        u.save()
        messages.success(request, _("Account saved."))
        return redirect("staff_list")
    return render(request, "gym/plans/form.html", {"form": form, "obj": obj, "title": _("Staff account"), "back": "staff_list"})


@owner_required
def settings_view(request):
    gym = GymSettings.get()
    form = GymSettingsForm(request.POST or None, request.FILES or None, instance=gym)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Settings saved."))
        return redirect("settings")
    return render(request, "gym/admin/settings.html", {"form": form})


def license_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    gym = GymSettings.get()
    if request.method == "POST" and request.POST.get("action") == "refresh":
        if refresh(gym, force=True):
            messages.success(request, _("License checked."))
        else:
            messages.error(request, _("Could not reach the license server. Check the internet connection."))
        return redirect("license")
    form = LicenseForm(request.POST or None)
    if request.method == "POST" and request.user.is_owner and form.is_valid():
        key = form.cleaned_data["key"].strip()
        info = read_key(key)
        if not info:
            messages.error(request, _("This license key is not valid."))
        elif info["install_id"] != gym.install_id.upper():
            messages.error(request, _("This key was made for another installation."))
        else:
            gym.license_key = key
            gym.save(update_fields=["license_key"])
            messages.success(request, _("License activated until %(date)s.") % {"date": info["expires"].strftime("%d/%m/%Y")})
            return redirect("license")
    from urllib.parse import quote
    status = license_status(gym)
    vendor = vendor_contact()
    wa_text = _("Hello, I want to activate GymPro DZ. Gym: %(gym)s — Installation ID: %(id)s") % {"gym": gym.name, "id": gym.install_id}
    return render(request, "gym/admin/license.html", {
        "form": form, "status": status, "gym_cfg": gym, "vendor": vendor, "online": server_enabled(),
        "wa_url": f"https://wa.me/{vendor['whatsapp']}?text={quote(wa_text)}" if vendor["whatsapp"] else "",
    })


@owner_required
def backup(request):
    out = io.StringIO()
    management.call_command("dumpdata", "gym", "accounts", indent=1, stdout=out)
    resp = HttpResponse(out.getvalue(), content_type="application/json")
    resp["Content-Disposition"] = f'attachment; filename="gympro_backup_{timezone.localdate()}.json"'
    return resp
