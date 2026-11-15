import mimetypes

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.static import serve


def media(request, path):
    """Serve photos/logo from the disk (local install) or from the database (Vercel)."""
    if not settings.MEDIA_IN_DB:
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    from ..models import StoredFile
    obj = StoredFile.objects.filter(name=path).only("data", "content_type").first()
    if obj is None:
        raise Http404
    resp = HttpResponse(bytes(obj.data), content_type=obj.content_type or mimetypes.guess_type(path)[0])
    resp["Cache-Control"] = "public, max-age=31536000, immutable"  # file names change on every new photo
    return resp
