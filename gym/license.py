"""
Licensing — how you (the vendor) control every gym.

Two systems, use one or both:

1) ONLINE LICENSE SERVER  (recommended — you can extend or stop a gym remotely)
   * You create ONE Supabase project for yourself ("GymPro Licenses") and run tools/license_server.sql in it.
   * Put its URL and anon key below (LICENSE_SERVER_URL / LICENSE_SERVER_KEY) before you give the app to gyms.
   * The first time a gym opens the app, it registers itself automatically with a 14-day trial.
   * You see every gym in Supabase > Table Editor > licenses. To activate a paying gym:
     set status = 'active' and expires_at = the paid-until date. To stop a gym: status = 'suspended'.
   * The app re-checks every few hours; a gym that never connects for OFFLINE_GRACE_DAYS is locked too.

2) OFFLINE KEYS  (for a gym without reliable internet)
   * The gym sends you its Installation ID (Settings > License).
   * You run: python tools/make_license.py 3F2A-91BC-04DE 2027-12-31 "Salle Atlas"
   * They paste the key in Settings > License. A valid key always wins over the online status.

BEFORE SELLING: fill the constants below and change LICENSE_SECRET to your own long random text.
"""
import base64
import hashlib
import hmac
import json
import logging
import threading
import urllib.request
from datetime import date, timedelta

from django.conf import settings

log = logging.getLogger(__name__)

# ------------------------------------------------------------------ vendor constants (edit these)
LICENSE_SECRET = b"whoaremedzfuckingibrahimwhofuckingworkeveryday"
LICENSE_SERVER_URL = "https://pwhzpgltbidwmsfpwzts.supabase.co"   # your Supabase project URL, e.g. "https://abcdefgh.supabase.co"
LICENSE_SERVER_KEY = "sb_publishable_6FnkHCqvx6jNgYVHqrhNdA_ahpvu6O0"   # your Supabase "anon public" key (safe to ship: it can only call check_license)
VENDOR_NAME = "GymPro DZ"
VENDOR_PHONE = ""          # e.g. "0550 12 34 56"  — shown on the lock screen
VENDOR_WHATSAPP = ""       # e.g. "213550123456"   — international format, no + or spaces
CHECK_EVERY_HOURS = 6
OFFLINE_GRACE_DAYS = 10
APP_VERSION = "1.1"


# ------------------------------------------------------------------ offline keys
def _sign(payload: bytes) -> str:
    return hmac.new(LICENSE_SECRET, payload, hashlib.sha256).hexdigest()[:16].upper()


def make_key(install_id: str, expires: date, gym_name: str = "") -> str:
    payload = json.dumps({"i": install_id.upper(), "e": expires.isoformat(), "n": gym_name}, separators=(",", ":")).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"GP1.{body}.{_sign(payload)}"


def read_key(key: str):
    """Return dict(install_id, expires, name) or None if invalid."""
    try:
        prefix, body, sig = key.strip().split(".")
        if prefix != "GP1":
            return None
        payload = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        if not hmac.compare_digest(_sign(payload), sig.upper()):
            return None
        data = json.loads(payload)
        return {"install_id": data["i"], "expires": date.fromisoformat(data["e"]), "name": data.get("n", "")}
    except Exception:
        return None


# ------------------------------------------------------------------ online license server
def server_enabled():
    return bool(LICENSE_SERVER_URL and LICENSE_SERVER_KEY)


def _call_server(gym):
    body = json.dumps({"p_install_id": gym.install_id, "p_gym_name": gym.name, "p_phone": gym.phone,
                       "p_city": gym.city, "p_version": APP_VERSION}).encode()
    req = urllib.request.Request(
        LICENSE_SERVER_URL.rstrip("/") + "/rest/v1/rpc/check_license", data=body, method="POST",
        headers={"apikey": LICENSE_SERVER_KEY, "Authorization": f"Bearer {LICENSE_SERVER_KEY}",
                 "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=6) as r:
        data = json.loads(r.read().decode())
    if isinstance(data, list):
        data = data[0] if data else {}
    if not data.get("expires_at"):
        raise ValueError("bad answer")
    return {"status": data.get("status", "trial"), "expires": str(data["expires_at"])[:10],
            "message": data.get("message") or ""}


def refresh(gym, force=False):
    """Ask the license server (if configured). Saves the answer in GymSettings. Returns True on success."""
    from django.utils import timezone

    if not server_enabled():
        return False
    if not force and gym.license_checked_at and timezone.now() - gym.license_checked_at < timedelta(hours=CHECK_EVERY_HOURS):
        return True
    try:
        ans = _call_server(gym)
    except Exception as e:  # offline, DNS, server down… keep the last answer
        log.warning("license server unreachable: %s", e)
        return False
    type(gym).objects.filter(pk=gym.pk).update(license_cache=ans, license_checked_at=timezone.now())
    gym.license_cache, gym.license_checked_at = ans, timezone.now()
    type(gym)._cache = None
    return True


_bg_lock = threading.Lock()


def refresh_in_background(gym):
    """Non-blocking refresh, at most one at a time."""
    if not _bg_lock.acquire(blocking=False):
        return

    def run():
        from django.db import connection
        try:
            refresh(gym)
        finally:
            connection.close()
            _bg_lock.release()
    threading.Thread(target=run, daemon=True).start()


# ------------------------------------------------------------------ status used by the whole app
LOCKED_STATES = ("expired", "suspended", "offline")


def license_status(gym):
    """dict(state, expires, days_left, locked, source)
    state: licensed | trial | expired | suspended | offline"""
    from django.utils import timezone

    today = timezone.localdate()

    def result(state, expires, source, **extra):
        left = (expires - today).days if expires else 0
        if state in ("licensed", "trial") and left < 0:
            state = "expired"
        return {"state": state, "expires": expires, "days_left": left, "locked": state in LOCKED_STATES,
                "source": source, **extra}

    # 1) a valid offline key always wins
    if gym.license_key:
        info = read_key(gym.license_key)
        if info and info["install_id"] == (gym.install_id or "").upper():
            if info["expires"] >= today:
                return result("licensed", info["expires"], "key", name=info["name"])

    # 2) online license server
    if server_enabled():
        cache = gym.license_cache or {}
        if not cache:
            refresh(gym, force=True)  # first run: wait for the answer once
            cache = gym.license_cache or {}
        else:
            stale = not gym.license_checked_at or timezone.now() - gym.license_checked_at > timedelta(hours=CHECK_EVERY_HOURS)
            if stale:
                refresh_in_background(gym)
        if cache:
            expires = date.fromisoformat(cache["expires"])
            msg = cache.get("message", "")
            if cache.get("status") == "suspended":
                return result("suspended", expires, "server", message=msg)
            if gym.license_checked_at and timezone.now() - gym.license_checked_at > timedelta(days=OFFLINE_GRACE_DAYS):
                return result("offline", expires, "server", message=msg)
            return result("licensed" if cache.get("status") == "active" else "trial", expires, "server", message=msg)
        # server never reached yet: fall through to the local trial

    # 3) local trial
    return result("trial", gym.installed_at + timedelta(days=settings.TRIAL_DAYS), "local")


def vendor_contact():
    return {"name": VENDOR_NAME, "phone": VENDOR_PHONE, "whatsapp": VENDOR_WHATSAPP}
