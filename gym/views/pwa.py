import json

from django.http import HttpResponse
from django.templatetags.static import static

from ..models import GymSettings


def manifest(request):
    """Lets Chrome/Edge/Android/iPhone 'install' the app from its link (desktop + home-screen icon)."""
    gym = GymSettings.get()
    data = {
        "name": f"{gym.name} — GymPro DZ", "short_name": gym.name[:18] or "GymPro DZ",
        "start_url": "/", "scope": "/", "display": "standalone", "orientation": "any",
        "background_color": "#0b1f1a", "theme_color": "#0e9f6e", "lang": "fr", "dir": "auto",
        "icons": [
            {"src": static("gym/img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("gym/img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("gym/img/icon-maskable.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Pointage / تسجيل الحضور", "url": "/checkin/"},
            {"name": "Nouvel adhérent / منخرط جديد", "url": "/members/new/"},
        ],
    }
    return HttpResponse(json.dumps(data, ensure_ascii=False), content_type="application/manifest+json")


SW = """// GymPro DZ service worker: makes the app installable. Always uses the network (data must be live).
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => new Response(
      '<meta charset=utf-8><meta name=viewport content="width=device-width"><body style="font-family:sans-serif;text-align:center;padding:60px">' +
      '<h2>Pas de connexion / لا يوجد اتصال</h2><p>Vérifiez Internet puis réessayez.<br>تحقق من الإنترنت ثم أعد المحاولة.</p>' +
      '<button onclick="location.reload()" style="padding:12px 24px;font-size:16px">↻</button></body>',
      {headers: {'Content-Type': 'text/html; charset=utf-8'}})));
  }
});
"""


def service_worker(request):
    resp = HttpResponse(SW, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp
