"""Tests for image magic-byte checks and JPEG compression."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.utils import compress_image, validate_image

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _png_bytes(width: int = 32, height: int = 32) -> bytes:
    image = Image.new("RGB", (width, height), color=(40, 120, 40))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes(width: int = 32, height: int = 32) -> bytes:
    image = Image.new("RGB", (width, height), color=(40, 120, 40))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def test_validate_accepts_jpeg_magic_bytes() -> None:
    data = _jpeg_bytes()
    assert data.startswith(b"\xff\xd8\xff")
    validate_image(data, "image/jpeg")


def test_validate_accepts_png_magic_bytes() -> None:
    data = _png_bytes()
    assert data.startswith(b"\x89PNG")
    validate_image(data, "image/png")


def test_validate_rejects_wrong_mime() -> None:
    with pytest.raises(ValueError, match="JPEG or PNG"):
        validate_image(_jpeg_bytes(), "image/gif")


def test_validate_rejects_jpeg_declared_as_png() -> None:
    with pytest.raises(ValueError, match="PNG"):
        validate_image(_jpeg_bytes(), "image/png")


def test_validate_rejects_random_bytes() -> None:
    with pytest.raises(ValueError, match="JPEG"):
        validate_image(b"not-an-image", "image/jpeg")


def test_validate_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_image(b"", "image/jpeg")


def test_compress_is_smaller_and_under_limit() -> None:
    original = _png_bytes(1800, 1600)
    compressed = compress_image(original)
    assert compressed.startswith(b"\xff\xd8\xff")
    assert len(compressed) < len(original)
    assert len(compressed) <= MAX_UPLOAD_BYTES
    with Image.open(BytesIO(compressed)) as image:
        assert image.format == "JPEG"
        assert max(image.size) <= 1024
        assert image.mode == "RGB"
