"""
VENDOR TOOL — keep it for yourself, do not give it to gyms.
Create a license key for a client installation.

    python tools/make_license.py <INSTALLATION-ID> <EXPIRY YYYY-MM-DD> ["Gym name"]
    python tools/make_license.py 3F2A-91BC-04DE 2027-12-31 "Salle Atlas Oran"

The client finds the Installation ID in Settings > License, sends it to you,
you send back the key, they paste it on the same page.
Before selling: change LICENSE_SECRET in gym/license.py (same value in your copy and in the client copies).
"""
import pathlib
import sys
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import os  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from gym.license import make_key, read_key  # noqa: E402

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)
key = make_key(sys.argv[1], date.fromisoformat(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "")
assert read_key(key)
print("\nLicense key:\n")
print(key)
print()
