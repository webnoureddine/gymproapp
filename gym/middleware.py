from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation

from .license import license_status
from .models import GymSettings

ALLOWED_PREFIXES = ("/static/", "/media/", "/i18n/", "/login", "/logout", "/settings/license", "/settings/backup",
                    "/admin/", "/manifest.webmanifest", "/sw.js")


class LicenseMiddleware:
    """When trial/license is over, only the license page stays reachable."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            # each user keeps their preferred language unless they switched for this session
            if "django_language" not in request.COOKIES and user.language:
                translation.activate(user.language)
                request.LANGUAGE_CODE = user.language
            if not request.path.startswith(ALLOWED_PREFIXES):
                status = license_status(GymSettings.get())
                request.license = status
                if status["locked"]:
                    return redirect(reverse("license"))
        return self.get_response(request)
