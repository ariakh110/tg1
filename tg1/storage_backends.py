from urllib.parse import urljoin

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class CKEditor5Storage(FileSystemStorage):
    location = settings.MEDIA_ROOT / "uploads" / "ckeditor"
    base_url = urljoin(settings.MEDIA_URL, "uploads/ckeditor/")
