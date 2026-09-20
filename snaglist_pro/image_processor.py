"""
snaglist_pro.image_processor — Image Resizing
==============================================
Resize images to a standard 200×200 size for snaglist reports.
"""

import os
import logging
from typing import Optional

from PIL import Image, ImageOps, UnidentifiedImageError

from snaglist_pro.config import settings

logger = logging.getLogger(__name__)


def _apply_exif_transpose(img: Image.Image) -> Image.Image:
    try:
        return ImageOps.exif_transpose(img) or img
    except Exception as exc:
        logger.debug("EXIF transpose failed: %s", exc)
        return img


def resize_to_200(src_path: str, dst_path: Optional[str] = None) -> str:
    target = dst_path or src_path

    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"Source image not found: {src_path}")

    parent = os.path.dirname(os.path.abspath(target))
    os.makedirs(parent, exist_ok=True)

    size = getattr(settings, "images_resize_size", 200)
    quality = getattr(settings, "images_quality", 90)

    try:
        with Image.open(src_path) as img:
            img = _apply_exif_transpose(img)
            img = img.convert("RGB")
            img = img.resize((size, size), Image.LANCZOS)
            img.save(target, "JPEG", quality=quality)
    except UnidentifiedImageError:
        logger.error("Cannot identify image file: %s", src_path)
        raise
    except Exception as exc:
        logger.error("Failed to resize image %s: %s", src_path, exc)
        raise

    logger.debug("Resized %s → %s (%d×%d, q=%d)", src_path, target, size, size, quality)
    return target
