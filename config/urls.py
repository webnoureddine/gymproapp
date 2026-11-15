from django.contrib import admin
from django.urls import include, path, re_path

from gym.views.media import media

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("gym.urls")),
    # Member photos & logo are served by the app itself (local install, no extra web server needed)
    re_path(r"^media/(?P<path>.+)$", media, name="media"),
]
