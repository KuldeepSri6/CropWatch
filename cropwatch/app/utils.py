"""Image validation and compression helpers."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89\x50\x4e\x47"
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_SIDE_PX = 1024
JPEG_QUALITY = 85


def validate_image(file_bytes: bytes, content_type: str) -> None:
    """Check MIME type and magic bytes for JPEG or PNG.

    Raises:
        ValueError: If the file is empty, the type is unsupported, or magic
            bytes do not match the declared content type.
    """
    if not file_bytes:
        raise ValueError("The uploaded image is empty.")
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Image must be a JPEG or PNG file.")
    if mime in {"image/jpeg", "image/jpg"}:
        if not file_bytes.startswith(JPEG_MAGIC):
            raise ValueError("File content does not match a JPEG image.")
        return
    if not file_bytes.startswith(PNG_MAGIC):
        raise ValueError("File content does not match a PNG image.")


def compress_image(file_bytes: bytes) -> bytes:
    """Resize so the longest side is at most 1024 px and save as JPEG.

    Converts to RGB, uses quality 85, and returns JPEG bytes.
    """
    with Image.open(BytesIO(file_bytes)) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        longest = max(width, height)
        if longest > MAX_SIDE_PX:
            scale = MAX_SIDE_PX / float(longest)
            rgb = rgb.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )
        buffer = BytesIO()
        rgb.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue()
