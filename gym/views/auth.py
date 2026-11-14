from django.conf import settings
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import activate
from django.views.decorators.http import require_POST


class LoginView(auth_views.LoginView):
    template_name = "gym/login.html"
    redirect_authenticated_user = True

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for f in form.fields.values():
            f.widget.attrs["class"] = "input"
        form.fields["username"].widget.attrs["autofocus"] = True
        return form


@require_POST
def set_language(request):
    lang = request.POST.get("language", "fr")
    if lang not in dict(settings.LANGUAGES):
        lang = "fr"
    nxt = request.POST.get("next") or "/"
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = "/"
    if request.user.is_authenticated and request.user.language != lang:
        request.user.language = lang
        request.user.save(update_fields=["language"])
    activate(lang)
    resp = HttpResponseRedirect(nxt)
    resp.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, max_age=365 * 24 * 3600, samesite="Lax")
    return resp
