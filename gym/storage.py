"""Store uploaded files (member photos, logo) inside the database.
Used automatically on Vercel/serverless hosts, where files written to disk disappear."""
import mimetypes

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    def _model(self):
        from .models import StoredFile
        return StoredFile

    def _open(self, name, mode="rb"):
        obj = self._model().objects.get(name=name)
        return ContentFile(bytes(obj.data), name=name)

    def _save(self, name, content):
        content.seek(0) if hasattr(content, "seek") else None
        data = content.read()
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        self._model().objects.update_or_create(name=name, defaults={"data": data, "content_type": ctype, "size": len(data)})
        return name

    def exists(self, name):
        return self._model().objects.filter(name=name).exists()

    def delete(self, name):
        self._model().objects.filter(name=name).delete()

    def size(self, name):
        return self._model().objects.filter(name=name).values_list("size", flat=True).first() or 0

    def url(self, name):
        base = settings.MEDIA_URL if settings.MEDIA_URL.startswith("/") else "/" + settings.MEDIA_URL
        return base + name

    def listdir(self, path):
        return [], [n.rsplit("/", 1)[-1] for n in self._model().objects.filter(name__startswith=path).values_list("name", flat=True)]
