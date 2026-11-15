"""Shrink photos before saving: phone pictures are 3-8 MB, a member photo needs ~40 KB."""
import io

from django.core.files.base import ContentFile


def shrink(uploaded, max_side=600, keep_png=False):
    from PIL import Image, ImageOps
    uploaded.seek(0)
    im = Image.open(uploaded)
    im = ImageOps.exif_transpose(im)  # phone photos taken sideways
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    if keep_png and im.mode in ("RGBA", "LA", "P"):
        im.save(buf, "PNG", optimize=True); ext = "png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=85, optimize=True); ext = "jpg"
    base = (getattr(uploaded, "name", "photo") or "photo").rsplit("/", 1)[-1].rsplit(".", 1)[0][:40] or "photo"
    return ContentFile(buf.getvalue(), name=f"{base}.{ext}")
