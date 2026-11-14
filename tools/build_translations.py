"""
Compile tools/translations.py into locale/<lang>/LC_MESSAGES/django.po + .mo
Needs:  pip install polib     (only on the developer machine, not for the gyms)
Usage:  python tools/build_translations.py
"""
import pathlib
import sys

import polib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from translations import T  # noqa: E402
import translations as _tr  # noqa: E402
PLURALS = getattr(_tr, 'PLURALS', {})

PLURAL = {"fr": "nplurals=2; plural=(n > 1);", "ar": "nplurals=6; plural=n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5;"}

for idx, lang in enumerate(("fr", "ar")):
    po = polib.POFile()
    po.metadata = {"Content-Type": "text/plain; charset=UTF-8", "Language": lang, "Plural-Forms": PLURAL[lang]}
    n_plurals = 2 if lang == "fr" else 6
    for msgid, tr in T.items():
        value = tr[idx]
        if isinstance(value, tuple):  # plural entry
            singular, plural = value
            msgid_plural = PLURALS.get(msgid, msgid.replace("day left", "days left"))
            forms = {0: singular, 1: plural} if lang == "fr" else {i: (singular if i == 1 else plural) for i in range(n_plurals)}
            po.append(polib.POEntry(msgid=msgid, msgid_plural=msgid_plural, msgstr_plural=forms))
        else:
            po.append(polib.POEntry(msgid=msgid, msgstr=value))
    out = ROOT / "locale" / lang / "LC_MESSAGES"
    out.mkdir(parents=True, exist_ok=True)
    po.save(str(out / "django.po"))
    po.save_as_mofile(str(out / "django.mo"))
    print(f"{lang}: {len(po)} strings")
