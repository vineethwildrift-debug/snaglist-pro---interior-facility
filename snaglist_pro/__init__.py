"""snaglist_pro package.

This package exposes the desktop and pipeline modules without eagerly importing
heavy runtime dependencies such as AI models, database layers, or dashboard code.
The Tk desktop app only needs the WhatsApp parser at startup, so keep the package
bootstrap intentionally lightweight.
"""

__version__ = "2.0.0"

__all__ = [
    "parse_whatsapp_text",
    "extract_media_refs",
]

from snaglist_pro.parse_export import parse_whatsapp_text, extract_media_refs
