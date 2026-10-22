"""Bounded document allowlist. Signatures are format checks, not malware scanning."""
from pathlib import Path
import re

from rest_framework import serializers

MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def validate_product_document(value):
    if not 0 < value.size <= MAX_DOCUMENT_SIZE:
        raise serializers.ValidationError("حجم سند باید بین صفر و ۱۰ مگابایت باشد.")
    extension = Path(value.name).suffix.lower()
    position = value.tell()
    try:
        header = value.read(1024)
    finally:
        value.seek(position)
    valid = {
        ".pdf": header.startswith(b"%PDF-"),
        ".dwg": re.match(rb"AC10[0-9]{2}", header) is not None,
        ".dxf": header.startswith(b"AutoCAD Binary DXF\r\n\x1a\x00")
        or re.match(rb"\s*0\s+SECTION\s", header) is not None,
    }
    if not valid.get(extension, False):
        raise serializers.ValidationError("فقط سند معتبر PDF، DWG یا DXF مجاز است.")
    return value
