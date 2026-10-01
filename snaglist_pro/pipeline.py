"""
WhatsApp Snaglist Pipeline — Enhanced
Process WhatsApp chat ZIP export → formatted snaglist Excel with database persistence.
"""

import os
import sys
import re
import json
import shutil
import zipfile
import argparse
import logging
import time
import os
import concurrent.futures
from rapidfuzz import fuzz
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Optional

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage

from snaglist_pro.config import settings
from snaglist_pro.parse_export import parse_whatsapp_text
from snaglist_pro.image_processor import resize_to_200
from snaglist_pro.description_enhancer import ACRONYMS, enhance_description, guess_category, guess_area
from snaglist_pro.ai_client import (
    enhance_description as ai_enhance_description,
    guess_category_and_area,
    generate_summary,
    is_ai_available,
    describe_image as ai_describe_image,
)


class LicenseError(RuntimeError):
    """Raised when a paid feature is gated by the license entitlement."""


def _check_license(feature: Optional[str] = None) -> None:
    """Gate paid report generation on the current entitlement.

    Opt-in: only called when the caller passes ``license_check=True``. When no
    license is configured the app degrades to the unlicensed state rather than
    crashing, so existing tests and the free tier keep working.
    """
    try:
        from snaglist_pro import licensing
    except Exception:
        return  # licensing module not available; do not block
    entitlement = licensing.evaluate_entitlement()
    if entitlement.get("gated"):
        raise LicenseError(
            f"License check failed: {entitlement.get('reason', 'not licensed')}. "
            "Install a valid license token to generate reports."
        )
    if feature and not licensing.is_feature_allowed(feature):
        raise LicenseError(
            f"Feature '{feature}' is not included in the current license."
        )

PHRASE_BOOST = [
    "light", "switch", "socket", "panel", "cable",
    "fire alarm", "smoke detector", "sprinkler", "door",
    "paint", "tile", "carpet", "ac", "duct", "damper",
    "network", "data", "chair", "table", "workstation",
    "clean", "floor", "partition", "glass", "ceiling",
]

_REPORT_SPELLING = {
    "Emeregency": "Emergency",
    "allignment": "alignment",
    "temparary": "temporary",
    "Lighining": "Lighting",
    "achiving": "achieving",
    "Draiwings": "Drawings",
    "installedded": "installed",
    "installedd": "installed",
    "installededd": "installed",
    "rectifiy": "rectify",
    "workinging": "working",
    "fixeded": "fixed",
    "obstuction": "obstruction",
    "scoket": "socket",
    "awarness": "awareness",
    "signgages": "signages",
    "engish": "English",
    "stips": "strips",
    "Exhuast": "Exhaust",
    "Diffueser": "Diffuser",
    "Landscapping": "Landscaping",
    # Typos seen in snag captions lifted from the site chats.
    "teil": "tile",
    "jip": "zip",
    "maut": "mat",
    "partion": "partition",
    "vissible": "visible",
    "standerd": "standard",
    "lavel": "level",
    "issuess": "issues",
    "namingg": "naming",
    "groutingg": "grouting",
    "leakagee": "leakage",
    "instalation": "installation",
    "comissioning": "commissioning",
    "accoustic": "acoustic",
    "aslo": "also",
    "wich": "which",
    "tehy": "they",
    "thier": "their",
    "recieve": "receive",
    "seperate": "separate",
    "occured": "occurred",
    "neccessary": "necessary",
    "existance": "existence",
    "responce": "response",
    "responsibile": "responsible",
    # Doubled trailing consonants in site snag captions.
    "replacedd": "replaced",
    "removedd": "removed",
    "providedd": "provided",
    "controll": "control",
    "damagedd": "damaged",
}


def correct_report_text_with_changes(value):
    original = str(value or "")
    text = original
    changes = []
    for incorrect, correct in _REPORT_SPELLING.items():
        updated = re.sub(rf"\b{re.escape(incorrect)}\b", correct, text, flags=re.IGNORECASE)
        if updated != text:
            changes.append((incorrect, correct))
            text = updated
    return text, changes


def correct_report_text(value):
    return correct_report_text_with_changes(value)[0]


def _correct_report_text(value):
    return correct_report_text(value)


SHEET_COLUMNS = [
    "Slno", "Facility Name", "Client Name", "Date Given", "Floor",
    "Area/Location", "Category", "Check Points", "Status (Open/Close)",
    "Snag Points", "Priority", "Ref. Images", "Ref. Images", "Date Closed",
    "Closed Images", "Vendor Name", "Project SPOC", "Transition SPOC",
]

COL_WIDTHS = {
    "A": 9.88, "B": 18.13, "C": 19.75, "D": 22.38, "E": 15.63,
    "F": 24.75, "G": 15.38, "H": 55.0, "I": 21.25, "J": 52.38,
    "K": 16.38, "L": 26.0, "M": 26.0, "N": 26.0, "O": 26.0,
    "P": 14, "Q": 18, "R": 18, "S": 18,
}

# Cell sizing for images
IMAGE_CELL_HEIGHT = 200    # Row height in points

FILL_GREEN = PatternFill("solid", fgColor="FFA9D18E")
FILL_YELLOW = PatternFill("solid", fgColor="FFFCE5CD")
FILL_ORANGE = PatternFill("solid", fgColor="FFFF9900")
FILL_HEADER = PatternFill("solid", fgColor="FF4472C4")
STYLE_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"))
HEADER_FONT = Font(bold=True)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
DATA_ALIGN = Alignment(wrap_text=True, vertical="top")

KNOWN_AREAS = [
    "Director cabin", "Workstation area", "Post review room", "Cafeteria area",
    "Cafeteria", "10pax meeting room", "2pax cabin", "Mr cabin", "Mr cabins",
    "Boardroom", "Finance cabin", "IT cabin", "HOD", "All area",
    "All cabins", "Acting and store rooms", "Store rooms", "Reception",
    "Conference room", "Server room", "Pantry", "Storage", "Locker room",
    "Acting room", "Right wing ups room", "Director cabin and workstation area",
    "Washroom", "Bathroom", "Restroom", "Corridor", "Hallway", "Passage",
    "Staircase", "Stairwell", "Lift lobby", "Elevator lobby", "Parking",
    "Basement", "Garage", "Terrace", "Balcony", "Rooftop", "Facade",
    "Exterior", "Landscaping", "Garden", "Electrical room", "AHU room",
    "Mechanical room", "Chiller room", "Data center", "Locker",
    "Foyer", "Entrance lobby", "Front desk", "Lounge", "Training room",
    "Seminar room", "Discussion room", "VIP room", "Waiting area",
    "Cubicle area", "Desk area", "Godown", "Warehouse",
    "Terrace garden", "Deck", "Parking area", "Car park",
    "Entry lobby", "Main lobby", "Reception desk",
]

def _vendor_override(category: str) -> str:
    ov = settings.vendor_overrides or {}
    return ov.get(category, "")


# Captions that assert no defect and no outstanding work. These are progress
# notes or bare location labels on photos, and turning them into report rows
# would claim defects nobody reported.
_FILLER_CAPTIONS = {
    "present project status",
    "project status",
    "present status",
    "cafetaria status",
    "cafeteria status",
    "site status",
    "progress photo",
    "garbage yard",
    "garbage area",
}

# Words that indicate the caption is actually saying something is wrong or
# outstanding. A short caption containing none of these is a label, not a snag.
_DEFECT_WORDS = {
    "damaged", "damage", "broken", "break", "crack", "cracked", "leak", "leaking",
    "leakage", "seepage", "seep", "missing", "not", "pending", "required", "need",
    "needs", "needed", "required", "install", "installed", "installation", "fix",
    "fixing", "fixed", "repair", "replace", "replaced", "replacement", "remove",
    "removed", "clean", "cleaning", "clear", "cleared", "provide", "provided",
    "pending", "to", "be", "should", "must", "issue", "issues", "wrong", "loose",
    "loosed", "uneven", "unfinished", "incomplete", "pending", "blocked", "stopped",
    "non", "functioning", "working", "finish", "finishing", "open", "exposed",
    "expose", "uncovered", "untidy", "dust", "dusty", "water", "paint", "painting",
    "tiling", "tile", "grout", "gap", "hole", "rust", "stain", "stained", "mark",
    "marks", "align", "alignment", "level", "loose", "gap", "gap", "gap",
    "mismatch", "wrong", "incorrect", "error", "fault", "faulty", "defect",
    "reject", "rejected", "hold", "pending", "awaiting", "delay", "delayed",
    # Nouns that name a defect type on their own. Without these a caption such
    # as "Rodent points" or "Rodent entry point" reads as a bare location
    # label and would be dropped, even though rodent-proofing is a real snag
    # category.
    "rodent", "rodents", "termite", "termites", "waterproofing", "waterproof",
    "sealing", "sealant", "leakproofing", "insulation", "cladding", "grouting",
}


def _normalize_caption(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def is_filler_caption(text: str) -> bool:
    """True when a photo caption reports no defect and no outstanding work.

    Two tests, both deliberately conservative so a real snag is never lost:

    1. The caption is in the explicit blocklist above (a progress note such as
       "Present project status").
    2. The caption is three words or fewer and contains no defect vocabulary -
       a bare label like "Fire pump room" or "Transformer yard".

    Longer captions always pass. This exists because fixing the dropped-snags
    bug also let through captions that only became visible once nothing was
    being thrown away.
    """
    norm = _normalize_caption(text)
    if not norm:
        return False
    if norm in _FILLER_CAPTIONS:
        return True
    words = norm.split()
    if len(words) > 3:
        return False
    return not any(w in _DEFECT_WORDS for w in words)


def _resolve_vendor(category: str) -> str:
    """Vendor for a category, with the precedence between the two tables explicit.

    config.yaml carries both a general "vendors" map and a "vendor_overrides"
    table. The values currently sitting in vendor_overrides belong to a
    different site ("MD Electrical", "IND Aircon") and include placeholder
    labels ("Interior: Interior", "Service: Service team"), so letting them win
    by name alone renamed vendors that were already correct.

    The order is therefore driven by config, not hardcoded, so a project that
    really does use vendor_overrides per-site can set:

        vendor_overrides_win: true      # overrides beat the general map

    and get the original behaviour back without a code change. The default
    matches what the packaged build did anyway, where config.yaml is absent and
    the override table is empty.
    """
    if settings.vendor_overrides_win:
        return _vendor_override(category) or get_vendor(category)
    return get_vendor(category) or _vendor_override(category)

CLOSED_KEYWORDS = [
    "done", "completed", "aligned", "fixed", "confirmed",
    "pass", "no issue", "no defect", "connected",
    "closed", "finished",
]

STRONG_CLOSED_SIGNALS = [
    "client scope", "out of scope", "not required", "not needed",
    "not available", "declined", "not applicable",
]

PENDING_KEYWORDS = [
    "need to", "to be ", "needs to", "should be", "required",
    "not working", "broken", "damaged", "leaking", "missing",
    "improper", "wrong",
]

_NEGATION_WORDS = {"not", "don't", "dont", "no", "never", "isnt", "isn't", "wasnt", "wasn't", "arent", "aren't"}


def extract_area_from_text(text: str) -> str:
    if not text:
        return "All area"
    t = text.lower()
    for area in sorted(KNOWN_AREAS, key=len, reverse=True):
        if area.lower() in t:
            return area
    return "All area"


def determine_status(description: str) -> str:
    if not description:
        return "Open"
    d = description.lower()
    if d.strip() in ("na", "n/a", "none"):
        return "Open"
    # Check pending keywords FIRST: "to be closed" should be Open, not Closed
    has_pending = any(pk in d for pk in PENDING_KEYWORDS)
    if has_pending:
        return "Open"
    for sig in STRONG_CLOSED_SIGNALS:
        if sig in d:
            return "Closed"
    for ck in CLOSED_KEYWORDS:
        if ck in d:
            idx = d.find(ck)
            before = d[:idx].strip().split()
            if any(w in _NEGATION_WORDS for w in before[-3:]):
                return "Open"
            return "Closed"
    return "Open"


_SYSTEM_TEXTS = {
    "ok", "ok,", "ok.", "okay", "yes", "no", "sure", "noted",
    "thank you", "thanks", "👍", "🙏", "hello", "hi",
}

_SYSTEM_PATTERNS = [
    "created group", "messages and calls are end-to-end encrypted",
    "you were added", "left", "added you", "deleted this message",
    "changed the subject", "changed this group",
    "this message was edited",
]

MESSAGE_HEADER_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s*"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)"
    r"\s*-\s*"
    r"(.+?):\s*"
    r"(.*)"
)

BRACKETED_MESSAGE_HEADER_RE = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s*"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s*"
    r"(?:-\s*)?(.*)"
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


class AICallTracker:
    def __init__(self, max_calls: int = 200, enabled: Optional[bool] = None):
        self.max_calls = max_calls
        self.calls = 0
        self.enabled = settings.ai_enabled if enabled is None else enabled
        self.enabled = self.enabled and is_ai_available()

    def call(self, func, *args, **kwargs):
        if not self.enabled:
            return None
        if self.calls >= self.max_calls:
            return None
        self.calls += 1
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning("AI call failed: %s", e)
            return None

    def status(self) -> str:
        if not self.enabled:
            return "disabled"
        return f"{self.calls}/{self.max_calls} calls used"


def detect_project_name(text_content: Optional[str], zip_path: Optional[str]) -> str:
    if text_content:
        m = re.search(r'created group "([^"]+)"', text_content)
        if m:
            return m.group(1).strip()

        candidate = _extract_client_from_chat(text_content)
        if candidate:
            return candidate

    if zip_path:
        base = os.path.basename(zip_path)
        name = re.sub(r"^WhatsApp Chat with\s+", "", base, flags=re.IGNORECASE)
        name = name.rsplit(".", 1)[0].strip()
        if name:
            return name
    return "Unknown Project"


def _extract_client_from_chat(text: str) -> Optional[str]:
    if not text:
        return None

    lines = text.split("\n")
    candidates = []

    business_suffixes = [
        "pvt", "ltd", "llp", "inc", "corp", "private", "limited",
        "solutions", "technologies", "services", "consulting",
        "group", "holdings", "enterprises", "global", "international",
        "bank", "financial", "healthcare", "pharma", "software",
        "digital", "labs", "media", "properties", "realty",
    ]

    skip_words = {
        "you", "were", "added", "left", "changed", "this", "group",
        "subject", "messages", "calls", "end", "to", "end", "encrypted",
        "security", "code", "now", "on", "off", "created", "new",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "am", "pm", "good", "morning", "evening", "night", "hello", "hi",
        "thanks", "thank", "ok", "okay", "yes", "no", "sure", "noted",
        "sent", "delivered", "read", "image", "video", "document", "audio",
        "sticker", "gif", "location", "contact", "poll", "event",
        "team", "please", "confirm", "status", "for", "the", "is", "are",
        "was", "has", "have", "that", "this", "its", "or", "but", "by",
        "on", "at", "i", "we", "you", "it", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
    }

    def score_candidate(tokens: list) -> float:
        if not tokens:
            return 0.0
        score = 0.0
        has_business = any(t.lower().rstrip(".") in business_suffixes for t in tokens)
        if has_business:
            score += 2.0
        if 1 <= len(tokens) <= 5:
            score += 1.5
        for t in tokens:
            t_lower = t.lower().rstrip(".")
            if t_lower in skip_words or len(t) <= 2:
                score -= 0.5
            if t[0].isupper() and len(t) > 3 and t_lower not in skip_words:
                score += 0.4
        return score

    for line in lines[:300]:
        line = line.strip()
        if not line:
            continue

        if "created group" in line:
            m = re.search(r'created group "([^"]+)"', line)
            if m:
                name = m.group(1).strip()
                name = re.sub(r"\s*[-–—]\s*WhatsApp.*$", "", name, flags=re.IGNORECASE).strip()
                if name:
                    return name

        m = re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", line)
        if not m:
            continue

        msg_part = line[m.end():]
        msg_part = re.sub(r"^[,\s]*[-\s]*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?\s*[-–—]\s*", "", msg_part).strip()
        msg_part = re.sub(r"^[,\s]*([A-Za-z][A-Za-z\s]{2,30}?):\s*", "", msg_part).strip()

        if not msg_part or len(msg_part) < 4:
            continue

        tokens = msg_part.split()
        scored = score_candidate(tokens)
        if scored > 1.0:
            name = " ".join(t for t in tokens if t.lower().rstrip(".") not in skip_words and len(t) > 2)
            name = re.sub(r"\s*[-–—:]\s*.*$", "", name).strip()
            if name and len(name) >= 4:
                candidates.append((scored, name))

        words = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", msg_part)
        for phrase in words:
            phrase_tokens = phrase.split()
            if 1 <= len(phrase_tokens) <= 5:
                scored = score_candidate(phrase_tokens)
                if scored > 1.5:
                    candidates.append((scored, phrase))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    best = []
    for score, name in candidates:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            best.append(name)
        if len(best) >= 3:
            break

    return best[0] if best else None


def slugify_project(name: str) -> str:
    slug = name.lower().replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    return slug.strip("_") or "project"


def detect_project_floor(project_name: str) -> str:
    match = re.search(r"\b(?:GF|B\d+|\d+(?:ST|ND|RD|TH)?F)\b", project_name or "", re.IGNORECASE)
    return match.group(0).upper() if match else ""


def extract_zip(zip_path: str, extract_dir: str) -> tuple:
    logging.info("Extracting ZIP: %s", zip_path)
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir, exist_ok=True)
    extract_root = Path(extract_dir).resolve()

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target = (extract_root / member.filename).resolve()
            if target != extract_root and extract_root not in target.parents:
                raise ValueError(f"Unsafe ZIP path: {member.filename}")
        zf.extractall(extract_dir)

    text_content = None
    image_map = {}
    attachment_map = {}

    for root, _dirs, files in os.walk(extract_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            if fname.lower().endswith(".txt"):
                try:
                    with open(fpath, encoding="utf-8-sig") as fh:
                        text_content = fh.read()
                    logging.info("  Found chat text: %s (%d bytes)", fname, len(text_content))
                except Exception as e:
                    logging.warning("  Failed to read %s: %s", fname, e)
            elif fname.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                image_map[fname] = fpath
            else:
                attachment_map[fname] = fpath

    logging.info("  Extracted %d image files and %d attachments", len(image_map), len(attachment_map))
    return text_content, image_map, attachment_map


def _is_system_message(text: str) -> bool:
    t = text.strip().lower()
    if t in _SYSTEM_TEXTS or len(t) < 4:
        return True
    for pat in _SYSTEM_PATTERNS:
        if pat in t:
            return True
    if re.match(r"^[A-Za-z\s]+[-–—]\s*[A-Za-z\s]+$", t) and "-" in t:
        if any(v.lower() in t for v in ["ever green", "carrier", "nikhita", "eaton", "amlite"]):
            return True
    if re.search(r"\.(pdf|xlsx?|docx?|pptx?)", t):
        return True
    if re.match(r"^\d+(?:st|nd|rd|th)?\s*f$", t):
        return True
    if re.match(r"^[\w\-\.]+$", t) and " " not in t and len(t) <= 12:
        return True
    return False


def _extract_image_filename(message_text: str) -> Optional[str]:
    m = re.search(r"(IMG-\d{8}-WA\d+\.\w+)", message_text)
    return m.group(1) if m else None


def _extract_attachment_filenames(message_text: str) -> list:
    candidates = []
    for m in re.finditer(r"([\w\- ]+\.(?:pdf|dwg|dxf|zip|rar|docx?|xlsx?|pptx?|txt|csv|rvt|rfa|ifc))", message_text, re.IGNORECASE):
        candidates.append(m.group(1).strip())
    attached = re.search(r"<attached:\s*([^>]+)>", message_text, re.IGNORECASE)
    if attached:
        candidates.append(attached.group(1).strip())
    return [name.strip("\"'") for name in candidates]


def _detect_date_order(raw_dates: list) -> list:
    """Pick the strptime format order that matches the export's date convention.

    WhatsApp writes dates as either D/M/Y (India) or M/D/Y (US). Trying
    "%d/%m/%Y" first silently swaps every ambiguous stamp such as "9/4/26", so
    the convention is detected from the whole chat first: a first component
    above 12 can only be a day (D/M/Y), a second component above 12 can only be
    a day (M/D/Y). When every stamp is ambiguous the two readings are
    indistinguishable from the numbers alone, so the format is picked once for
    the whole chat (D/M/Y, the convention this tool has always produced) instead
    of guessing per stamp and getting a different answer for each one.
    """
    day_first = month_first = False
    for raw in raw_dates:
        m = re.match(r"^\s*(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\s*$", str(raw))
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            day_first = True
        if b > 12:
            month_first = True

    if month_first and not day_first:
        logging.info("  Date format detected: M/D/Y (US export)")
        return ["%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y"]
    if day_first:
        logging.info("  Date format detected: D/M/Y")
    else:
        logging.info("  All dates ambiguous; assuming D/M/Y")
    return ["%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"]


def parse_chat_messages(text: str) -> list:
    if not text:
        return []
    messages = []
    current_date = None
    current_sender = None
    current_message = []

    for line in text.split("\n"):
        stripped = line.strip()
        match = MESSAGE_HEADER_RE.match(stripped) if stripped else None
        bracketed_match = BRACKETED_MESSAGE_HEADER_RE.match(stripped) if stripped else None
        if match:
            if current_sender and current_message:
                msg_text = "\n".join(current_message).strip()
                if msg_text:
                    messages.append({"date": current_date, "sender": current_sender, "message": msg_text})
            current_date = match.group(1)
            current_sender = match.group(3).strip()
            current_message = [match.group(4)]
        elif bracketed_match:
            if current_sender and current_message:
                msg_text = "\n".join(current_message).strip()
                if msg_text:
                    messages.append({"date": current_date, "sender": current_sender, "message": msg_text})
            current_date = bracketed_match.group(1)
            body = bracketed_match.group(3).strip()
            sender_match = re.match(r"([^:]+):\s*(.*)", body)
            if sender_match:
                current_sender = sender_match.group(1).strip()
                current_message = [sender_match.group(2)]
            else:
                current_sender = ""
                current_message = [body]
        else:
            if current_sender and stripped:
                current_message.append(stripped)

    if current_sender and current_message:
        msg_text = "\n".join(current_message).strip()
        if msg_text:
            messages.append({"date": current_date, "sender": current_sender, "message": msg_text})

    date_order = _detect_date_order(
        [msg.get("date") for msg in messages if msg.get("date")]
    )
    for msg in messages:
        d = msg.get("date")
        if d:
            for fmt in date_order:
                try:
                    msg["date"] = datetime.strptime(d, fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
    return messages


def pair_images_with_descriptions(messages: list, image_map: dict, ai_tracker: Optional[AICallTracker] = None) -> list:
    sorted_images = sorted(image_map.keys())
    if not sorted_images:
        logging.warning("  No images found in ZIP - media files may be missing from export")
    consumed = set()

    def _peek_unconsumed():
        for name in sorted_images:
            if name not in consumed:
                return name
        return None

    def _consume(name):
        consumed.add(name)

    def _next_unconsumed():
        for name in sorted_images:
            if name not in consumed:
                consumed.add(name)
                return name
        return None

    def _clean_text(text):
        t = text or ""
        t = re.sub(r"IMG-\d{8}-WA\d+\.\w+\s*\(file attached\)\s*", "", t)
        t = re.sub(r"(?:<Media omitted>|<image omitted>|\[Image\])\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"<attached:\s*[^>]+>\s*", "", t)
        # A caption can be followed by a chat header the parser folded into the
        # body ("Dbs area towers bolts 9/29/26, 6:41 PM - Abhilash added ...").
        # Drop the header and everything after it so the snag point stays clean.
        t = re.sub(
            r"\s*\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*[APap][Mm]\s*-\s*.*$",
            "",
            t,
        )
        t = re.sub(r"[\u202f\u00a0]+", " ", t)
        t = re.sub(r"\s{2,}", " ", t)
        t = t.strip()
        if t and _is_system_message(t):
            t = ""
        return t

    entries_by_index = {}
    omits_indices = []
    missing_media_index = 0

    for i, msg in enumerate(messages):
        text = msg.get("message", "")
        sender = msg.get("sender", "")
        date = msg.get("date", "")
        clean = _clean_text(text)

        if date == "2026-07-18" and not clean:
            continue

        has_img = bool(re.search(r"IMG-\d{8}-WA\d+\.\w+", text))
        if has_img:
            filename = re.search(r"(IMG-\d{8}-WA\d+\.\w+)", text).group(1)
            if filename in image_map and filename not in consumed:
                _consume(filename)
                entries_by_index[i] = {
                    "image_filename": filename,
                    "image_path": image_map[filename],
                    "sender": sender,
                    "date": date,
                    "description": clean,
                }
        elif re.search(r"(?:<Media omitted>|<image omitted>|\[Image\])", text, re.IGNORECASE):
            omits_indices.append((i, msg, clean))

    for i, msg, clean in omits_indices:
        sender = msg.get("sender", "")
        date = msg.get("date", "")
        if date == "2026-07-18" and not clean:
            continue
        filename = _next_unconsumed()
        if filename:
            entries_by_index[i] = {
                "image_filename": filename,
                "image_path": image_map[filename],
                "sender": sender,
                "date": date,
                "description": clean,
            }
        else:
            missing_media_index += 1
            entries_by_index[i] = {
                "image_filename": f"missing_media_{missing_media_index:04d}",
                "image_path": "",
                "sender": sender,
                "date": date,
                "description": clean,
                "media_missing": True,
            }

    entries = [entries_by_index[i] for i in sorted(entries_by_index.keys())]
    entries = _merge_image_only_snags(entries)
    return entries


def _merge_image_only_snags(entries: list) -> list:
    """Attach photos sent without a description to the nearest text snag.

    WhatsApp chats commonly send a batch of photos with no caption, followed
    (or preceded) by a text message describing them. When a snag entry carries
    an image but no description, it is merged into the nearest entry that has a
    description on the same date, so the row keeps its description and the image
    is not lost.

    The sender is intentionally NOT required to match: on a live site the
    supervisor (e.g. "Manu Indiqube Gowda") files the text snag while a
    contractor or client (e.g. "+91 89715 11617") sends the photos of the same
    area on the same day. Requiring the same sender left every such batch as an
    orphan image with a blank description.

    Both directions are searched (nearest preceding first, then nearest
    following) because a photo batch may arrive before the describing text.
    Entries that cannot be merged (no text snag on the same date at all) are
    kept as-is.
    """
    merged = []
    consumed = set()
    for i, entry in enumerate(entries):
        if i in consumed:
            continue
        desc = (entry.get("description") or "").strip()
        if desc or not entry.get("image_filename"):
            merged.append(entry)
            continue
        # Image-only snag: look for a text snag on the same date, nearest
        # preceding first, then nearest following. Sender is not required to
        # match (see module docstring rationale above).
        host = None
        for j in range(i - 1, -1, -1):
            if j in consumed:
                continue
            other = entries[j]
            other_desc = (other.get("description") or "").strip()
            if other_desc and other.get("date") == entry.get("date"):
                host = other
                break
        if host is None:
            for j in range(i + 1, len(entries)):
                if j in consumed:
                    continue
                other = entries[j]
                other_desc = (other.get("description") or "").strip()
                if other_desc and other.get("date") == entry.get("date"):
                    host = other
                    break
        if host is None:
            merged.append(entry)
            continue
        consumed.add(i)
        fn = entry.get("image_filename", "")
        existing = list(host.get("image_filenames") or [])
        if fn and fn not in existing:
            existing.append(fn)
        host["image_filenames"] = existing
        # Promote the first image to the primary slot if the host had none.
        if not host.get("image_filename") and existing:
            host["image_filename"] = existing[0]
        extra = [f for f in existing if f != host.get("image_filename")]
        host["extra_image_filenames"] = extra
    return merged


def deduplicate_snags(snags: list) -> list:
    seen = set()
    deduped = []
    dup_count = 0
    for s in snags:
        key = (s["image_filename"], s["description"][:60])
        if key not in seen:
            seen.add(key)
            deduped.append(s)
        else:
            dup_count += 1
    if dup_count:
        logging.info("  Removed %d duplicate snags", dup_count)
    return deduped


def _compute_phash(entry: dict) -> tuple:
    img_path = entry.get("image_path", "")
    if not img_path or not os.path.exists(img_path):
        return (None, None, entry)
    try:
        import imagehash
        with PILImage.open(img_path) as img:
            h = imagehash.phash(img)
        return (h, entry.get("description", ""), entry)
    except Exception:
        return (None, None, entry)


def deduplicate_by_phash(entries: list) -> list:
    try:
        import imagehash
    except ImportError:
        logging.info("  imagehash not available, skipping phash dedup")
        return entries

    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        results = list(pool.map(_compute_phash, entries))

    keep = []
    removed = 0
    hashes = {}

    for h, desc, entry in results:
        if h is None:
            keep.append(entry)
            continue

        duplicate = False
        for existing_h, existing_entry in hashes.items():
            if h - existing_h <= 6:
                if desc == existing_entry.get("description", ""):
                    duplicate = True
                    removed += 1
                    break

        if not duplicate:
            hashes[h] = entry
            keep.append(entry)

    if removed:
        logging.info("  Removed %d visually duplicate images (phash dedup)", removed)
    return keep


def load_checklist(checklist_path: str) -> list:
    if not checklist_path or not os.path.exists(checklist_path):
        logging.warning("  Checklist NOT FOUND: %s", checklist_path)
        return []

    wb = openpyxl.load_workbook(checklist_path)
    ws = wb.active

    header_row = None
    for row in ws.iter_rows(min_row=1, max_row=10, max_col=20):
        for cell in row:
            if cell.value and "Check points" in str(cell.value):
                header_row = cell.row
                break
        if header_row:
            break
    if not header_row:
        header_row = 5

    headers = {}
    for cell in ws[header_row]:
        if cell.value:
            headers[str(cell.value).strip()] = cell.column

    slno_col = headers.get("Slno", 1)
    cat_col = headers.get("Catagory", 7)
    check_col = headers.get("Check points", 8)
    pri_col = headers.get("Priority", 11)
    snag_col = headers.get("Snag Points", 10)
    area_col = headers.get("Area/Location", 6)

    items = []
    for row in ws.iter_rows(min_row=header_row + 1, max_row=1500, max_col=20):
        slno_v = row[slno_col - 1].value
        cat_v = str(row[cat_col - 1].value or "").strip() if row[cat_col - 1].value else ""
        check_v = str(row[check_col - 1].value or "").strip() if row[check_col - 1].value else ""
        pri_v = str(row[pri_col - 1].value or "").strip() if row[pri_col - 1].value else "Medium"
        snag_v = str(row[snag_col - 1].value or "").strip() if row[snag_col - 1].value else ""
        area_v = str(row[area_col - 1].value or "").strip() if row[area_col - 1].value else ""

        if slno_v is not None and check_v:
            try:
                slno = int(float(slno_v))
            except (ValueError, TypeError):
                continue  # Skip header/sub-header rows with non-numeric Slno
            items.append({
                "slno": slno,
                "category": cat_v if cat_v else "Unassigned",
                "check_points": check_v,
                "priority": pri_v if pri_v else "Medium",
                "snag_points": snag_v,
                "area_location": area_v,
            })

    wb.close()
    logging.info("  Loaded %d checklist items", len(items))
    return items


_STOP_WORDS = {
    "the", "a", "an", "is", "in", "of", "to", "for", "and",
    "with", "as", "per", "be", "all", "not", "any", "from",
    "are", "was", "has", "have", "that", "this", "its", "or",
    "but", "by", "on", "at", "no", "am", "pm", "i", "we", "you",
    "it", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "shall", "been", "being", "were", "had",
    "having", "done", "need", "needs", "needed", "provides",
}


def _tokenize(text: str) -> list:
    tokens = [t for t in re.findall(r"\w+", text.lower()) if t not in _STOP_WORDS]
    return [t for t in tokens if len(t) > 2 or t.upper() in ACRONYMS]


def _bigrams(tokens: list) -> set:
    return set(zip(tokens, tokens[1:]))


def _token_score(match_text: str, desc_lower: str, match_tokens: list, match_set: set, match_bigrams: set, check: str) -> float:
    check_tokens = _tokenize(check)
    check_set = set(check_tokens)
    check_bigrams = _bigrams(check_tokens)

    intersection = match_set & check_set
    union = match_set | check_set
    jaccard = len(intersection) / len(union) if union else 0.0

    fuzzy_bonus = 0.0
    unmatched_desc = match_set - check_set
    unmatched_check = check_set - match_set
    for dt in unmatched_desc:
        for ct in unmatched_check:
            if len(dt) > 3 and len(ct) > 3:
                if dt in ct or ct in dt:
                    fuzzy_bonus += 0.03
                else:
                    ratio = fuzz.ratio(dt, ct) / 100.0
                    if ratio > 0.65:
                        fuzzy_bonus += 0.04

    bigram_overlap = match_bigrams & check_bigrams
    bigram_bonus = len(bigram_overlap) * 0.08

    phrase_bonus = 0.0
    for phrase in PHRASE_BOOST:
        if phrase in desc_lower and phrase in check:
            phrase_bonus += 0.05

    partial = fuzz.partial_ratio(match_text, check) / 100.0
    direct_ratio = fuzz.ratio(match_text, check) / 100.0
    fuzzy_text_bonus = (partial * 0.12) + (direct_ratio * 0.06)

    min_len = min(len(match_set), len(check_set))
    coverage_bonus = (len(intersection) / min_len * 0.10) if min_len > 0 else 0.0

    return jaccard + fuzzy_bonus + bigram_bonus + phrase_bonus + fuzzy_text_bonus + coverage_bonus


def match_to_checklist(description: str, guessed_category: str, checklist_items: list, enhanced_desc: str = "",
                       checklist_embs: Optional[list] = None) -> tuple:
    if not description or not checklist_items:
        return None, 0.0

    match_text = (enhanced_desc or description).lower()
    desc_lower = description.lower()
    match_tokens = _tokenize(match_text)
    match_set = set(match_tokens)
    match_bigrams = _bigrams(match_tokens)

    candidates = [it for it in checklist_items if it["category"].lower() == guessed_category.lower()]
    if not candidates:
        candidates = checklist_items

    best_item = None
    best_score = 0.0

    for idx, item in enumerate(candidates):
        check = item["check_points"].lower()
        token_s = _token_score(match_text, desc_lower, match_tokens, match_set, match_bigrams, check)

        cat_bonus = 0.08 if item["category"].lower() == guessed_category.lower() else 0.0

        # Area/location proximity bonus
        item_area = str(item.get("area_location", "") or "")
        if item_area:
            item_area_tokens = set(re.findall(r"\w+", item_area.lower()))
            desc_tokens = set(re.findall(r"\w+", desc_lower))
            if item_area_tokens & desc_tokens:
                token_s += 0.10
        score = token_s + cat_bonus

        # Blend with semantic score if embeddings available
        if checklist_embs is not None:
            orig_idx = checklist_items.index(item)
            if orig_idx < len(checklist_embs) and checklist_embs[orig_idx] is not None:
                from snaglist_pro.semantic_matcher import embed, cosine_similarity
                desc_emb = embed(match_text)
                sem_score = cosine_similarity(desc_emb, checklist_embs[orig_idx])
                score = score * 0.55 + sem_score * 0.45

        if score > 0.10 and score > best_score:
            best_score = score
            best_item = item

    return best_item, best_score


def infer_description_from_image(image_path: str, fallback_text: str = "") -> str:
    text = (fallback_text or "").strip()
    if not image_path or not os.path.exists(image_path):
        return text or ""

    name = os.path.basename(image_path).lower()
    if any(token in name for token in ["grr", "lrr", "hrr", "restroom", "rest room", "washroom"]):
        if "grr" in name or "grr" in text.lower():
            return text or "GRR - general rectification required"
        if "lrr" in name or "lrr" in text.lower():
            return text or "LRR - ladies restroom rectification required"
        if "hrr" in name or "hrr" in text.lower():
            return text or "HRR - handicap restroom rectification required"
        return text or "Restroom defect - rectification required"

    return text or ""


def determine_priority(description: str, matched_item: Optional[dict]) -> str:
    desc_lower = description.lower()
    for kw in settings.priority_high_keywords:
        if kw in desc_lower:
            return "High"
    if matched_item and matched_item.get("priority"):
        return matched_item["priority"]
    return settings.project_default_priority


def get_vendor(category: str) -> str:
    return settings.get_vendor(category)


def _resize_one(args: tuple) -> tuple:
    idx, snag, img_dir = args
    src = snag.get("image_path", "")
    if not src or not os.path.exists(src):
        return None
    ext = os.path.splitext(src)[1].lower()
    dst_name = f"snag_{idx:03d}{ext}"
    dst = os.path.join(img_dir, dst_name)
    try:
        resize_to_200(src, dst)
        return (snag["image_filename"], dst)
    except Exception:
        try:
            shutil.copy2(src, dst)
            return (snag["image_filename"], dst)
        except Exception:
            return None


def resize_snag_images(snags: list, output_dir: str) -> dict:
    img_dir = os.path.join(output_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    items = [(idx, snag, img_dir) for idx, snag in enumerate(snags)]
    resized_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        for result in pool.map(_resize_one, items):
            if result is not None:
                key, val = result
                resized_map[key] = val
    return resized_map


def _extract_attachment_metadata(path: str) -> dict:
    info = {
        "file_size": None, "extension": None,
        "page_count": None, "layer_count": None, "entity_count": None,
        "layer_names": "", "text_snippet": "", "keyword_summary": "", "notes": "",
    }
    if not path or not os.path.exists(path):
        return info

    info["file_size"] = os.path.getsize(path)
    ext = os.path.splitext(path)[1].lower()
    info["extension"] = ext.lstrip(".") if ext else ""

    try:
        if ext == ".pdf":
            try:
                from PyPDF2 import PdfReader
                with open(path, "rb") as fh:
                    reader = PdfReader(fh)
                    info["page_count"] = len(reader.pages)
                    extracted = []
                    for page in reader.pages[:5]:
                        extracted.append(page.extract_text() or "")
                    full_text = "\n".join(extracted).strip()
                    info["text_snippet"] = full_text[:1500].replace("\n", " ").strip()
                    tokens = re.findall(r"\w+", full_text.lower())
                    tokens = [t for t in tokens if len(t) > 2 and t not in _STOP_WORDS]
                    info["keyword_summary"] = ", ".join([w for w, _ in Counter(tokens).most_common(10)])
            except ImportError:
                info["notes"] = "Install PyPDF2 for PDF metadata"

        elif ext in (".dxf", ".dwg"):
            try:
                import ezdxf
                doc = ezdxf.readfile(path)
                info["layer_count"] = len(doc.layers)
                info["entity_count"] = sum(1 for _ in doc.entities)
                layer_names = [layer.dxf.name for layer in doc.layers if layer.dxf.name.lower() != "0"]
                info["layer_names"] = ", ".join(sorted(set(layer_names))[:10])
                if layer_names:
                    info["keyword_summary"] = ", ".join(sorted(set(layer_names))[:8])
                info["notes"] = f"DXF/DWG structure extracted; use CAD for deeper analysis"
            except ImportError:
                info["notes"] = "Install ezdxf for DXF/DWG metadata"
    except Exception:
        pass

    return info


def gather_attachment_entries(messages: list, attachment_map: dict) -> list:
    norm_map = {}
    for name in attachment_map:
        key = name.lower().strip()
        key = re.sub(r"[^a-z0-9._-]", "", key)
        norm_map[key] = name

    references = {}
    for msg in messages:
        filenames = _extract_attachment_filenames(msg.get("message", ""))
        for raw_name in filenames:
            key = raw_name.lower().strip()
            key = re.sub(r"[^a-z0-9._-]", "", key)
            if key in norm_map:
                actual = norm_map[key]
                references.setdefault(actual, []).append(msg)
                continue
            for nk, na in norm_map.items():
                if nk.endswith(key) or key.endswith(nk):
                    references.setdefault(na, []).append(msg)
                    break

    entries = []
    for attached_name, attached_path in sorted(attachment_map.items()):
        refs = references.get(attached_name, [])
        metadata = _extract_attachment_metadata(attached_path)
        chat_notes = " | ".join(r.get("message", "") for r in refs)
        suggested_action = _suggest_attachment_action(metadata, chat_notes)
        entries.append({
            "attachment_name": attached_name,
            "attachment_type": metadata["extension"] or "unknown",
            "file_size": metadata["file_size"],
            "page_count": metadata["page_count"],
            "layer_count": metadata["layer_count"],
            "entity_count": metadata["entity_count"],
            "layer_names": metadata.get("layer_names", ""),
            "text_snippet": metadata.get("text_snippet", ""),
            "keyword_summary": metadata.get("keyword_summary", ""),
            "suggested_action": suggested_action,
            "analysis_notes": metadata["notes"],
            "referenced": bool(refs),
            "reference_count": len(refs),
            "first_referenced_by": refs[0]["sender"] if refs else "",
            "first_reference_date": refs[0]["date"] if refs else "",
            "chat_notes": chat_notes[:1000],
            "attachment_path": attached_path,
        })

    return entries


def _suggest_attachment_action(metadata: dict, chat_notes: str) -> str:
    ext = (metadata.get("extension") or "").lower()
    keywords = (metadata.get("keyword_summary") or "").lower()
    actions = []

    if ext in {"dwg", "dxf"}:
        actions.append("Open in CAD software and validate layers/geometry")
    elif ext == "pdf":
        actions.append("Review PDF drawing/specification content")
        if "plan" in keywords or "layout" in keywords:
            actions.append("Verify plan dimensions and floor references")
    elif ext in {"rvt", "rfa", "ifc"}:
        actions.append("Review BIM model/drawing in Revit or IFC tool")
    elif ext in {"zip", "rar"}:
        actions.append("Inspect archive contents for CAD/drawing files")

    if "as-built" in chat_notes.lower() or "as built" in chat_notes.lower():
        actions.append("Compare with as-built documentation")
    if not actions:
        actions.append("Review attachment and classify its drawing/spec content")

    return "; ".join(actions)


def build_excel(
    snags: list,
    checklist_items: list,
    resized_map: dict,
    output_path: str,
    sheet_name: Optional[str] = None,
    ai_tracker: Optional[AICallTracker] = None,
    project_client: Optional[str] = None,
    project_facility: Optional[str] = None,
    project_floor: Optional[str] = None,
) -> str:
    logging.info("Building Excel: %s", output_path)
    project_client_name = project_client or settings.project_default_client
    project_facility_name = project_facility or settings.project_default_facility
    project_floor_name = project_floor or settings.project_default_floor
    if not sheet_name:
        sheet_name = project_facility_name or "Snaglist"

    wb = openpyxl.Workbook()
    safe_name = sheet_name.replace("/", "-").replace("\\", "-").replace("?", "").replace("*", "").replace("[", "").replace("]", "").replace(":", "-")
    safe_name = safe_name.strip()
    if not safe_name:
        safe_name = "Snaglist"
    ws = wb.active
    ws.title = safe_name[:31]

    ws["A2"] = "Index"
    ws["I2"] = "Date"
    ws["J2"] = datetime.now()
    for cell in [ws["I2"], ws["J2"]]:
        cell.font = Font(bold=True)
        cell.fill = FILL_GREEN

    checklist_embs = None
    try:
        from snaglist_pro.semantic_matcher import embed
        checklist_embs = [embed(it["check_points"].lower()) for it in checklist_items]
    except Exception:
        pass

    snag_with_match = []
    matched_slnos = set()
    for snag in snags:
        desc_raw = snag.get("description", "")
        desc_enhanced = enhance_description(desc_raw)
        if not desc_enhanced and snag.get("image_path"):
            heuristic_desc = infer_description_from_image(snag["image_path"], desc_raw)
            if heuristic_desc:
                desc_enhanced = heuristic_desc
        if not desc_enhanced and snag.get("image_path"):
            # WhatsApp chats frequently send photos with no caption. Use a
            # vision model to describe the image so the row is not blank.
            # This is a data-filling fallback, so it runs independently of the
            # text-AI tracker (which may be disabled when no text model is
            # installed but a vision model is available).
            vision_desc = ai_describe_image(snag["image_path"], desc_raw)
            if vision_desc:
                desc_enhanced = vision_desc
        if not desc_enhanced and ai_tracker and ai_tracker.enabled:
            ai_desc = ai_tracker.call(enhance_description, desc_raw or "Construction defect in image")
            if ai_desc:
                desc_enhanced = ai_desc
        guessed_cat = guess_category(desc_enhanced or desc_raw)
        if guessed_cat == "Unassigned" and ai_tracker and ai_tracker.enabled:
            ai_cat, ai_area = ai_tracker.call(guess_category_and_area, desc_enhanced or desc_raw)
            if ai_cat and ai_cat != "Unassigned":
                guessed_cat = ai_cat
            if ai_area:
                snag["ai_area"] = ai_area
        matched_item, match_score = match_to_checklist(desc_raw, guessed_cat, checklist_items, desc_enhanced, checklist_embs)
        snag_with_match.append((snag, matched_item, desc_enhanced, guessed_cat))
        if matched_item:
            matched_slnos.add(matched_item["slno"])

    for col_idx, col_name in enumerate(SHEET_COLUMNS, start=1):
        cell = ws.cell(row=7, column=col_idx, value=col_name)
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN
        cell.border = STYLE_BORDER
        if col_name == "Ref.images":
            cell.fill = FILL_YELLOW
        elif col_name == "Vendor name":
            cell.fill = FILL_ORANGE
        else:
            cell.fill = FILL_GREEN

    matched_count = 0
    unmatched_checklist = 0
    unmatched_snag_count = 0
    correction_log = []
    stats = Counter()
    row_num = 8

    def _get_checklist_snag_points(snag, checklist):
        """Find the most contextually relevant Snag Points from checklist for a snag."""
        snag_desc = (snag.get("description") or "").lower()
        best_snag = ""
        best_score = 0
        for item in checklist:
            item_snag = str(item.get("snag_points", "") or "")
            if not item_snag:
                continue
            item_tokens = set(re.findall(r"\w+", item_snag.lower()))
            desc_tokens = set(re.findall(r"\w+", snag_desc)) if snag_desc else set()
            overlap = len(item_tokens & desc_tokens)
            item_area = str(item.get("area_location", "") or "").lower()
            if item_area:
                area_tokens = set(re.findall(r"\w+", item_area))
                if area_tokens & desc_tokens:
                    overlap += 2
            if overlap > best_score:
                best_score = overlap
                best_snag = item_snag
        return best_snag

    def _consolidate_by_area(snag_with_match):
        """Group snags that map to the same checklist item + area into one row.

        Multiple chat messages for the same checklist item and area are merged
        rather than dropped: their descriptions are joined (so no row is left
        blank) and every image filename is collected so it can be embedded.
        """
        grouped = {}
        for snag, matched_item, desc_enhanced, guessed_cat in snag_with_match:
            if not matched_item:
                continue
            area = extract_area_from_text(desc_enhanced or snag.get("description", ""))
            key = (matched_item["slno"], area)
            if key not in grouped:
                grouped[key] = {
                    "snag": dict(snag),
                    "matched_item": matched_item,
                    "guessed_cat": guessed_cat,
                    "descriptions": [],
                    "image_filenames": [],
                }
            g = grouped[key]
            desc = (snag.get("description") or "").strip()
            if desc and desc not in g["descriptions"]:
                g["descriptions"].append(desc)
            fn = snag.get("image_filename", "")
            if fn and fn not in g["image_filenames"]:
                g["image_filenames"].append(fn)

        consolidated = []
        for g in grouped.values():
            primary = g["snag"]
            merged_desc = " | ".join(g["descriptions"])
            primary["description"] = merged_desc
            # Deduplicate image filenames across the merged group and split
            # into a primary image and extras (up to the template's two image
            # columns, L and M).
            seen = []
            for fn in g["image_filenames"]:
                if fn and fn not in seen:
                    seen.append(fn)
            primary["image_filenames"] = seen
            primary["image_filename"] = seen[0] if seen else ""
            primary["extra_image_filenames"] = seen[1:]
            consolidated.append((
                primary,
                g["matched_item"],
                enhance_description(merged_desc),
                g["guessed_cat"],
            ))
        return consolidated

    # DISABLED: Don't consolidate snags - each should be separate row
    # Each unique checklist item + description = separate row (no merging)
    consolidated = [(s, m, d, c) for s, m, d, c in snag_with_match if m]
    logging.info("  Using %d snags after filtering (no consolidation)", len(consolidated))

    # Group matched snags by checklist slno. Several chat snags can legitimately
    # answer the same checklist question (e.g. "Ahu room door handle need to be
    # install" and "Ahu room unwanted material need to be clear" both hit the AHU
    # door item), so every one of them is kept and gets its own row below.
    snags_by_slno = {}
    for snag, matched_item, desc_enhanced, guessed_cat in consolidated:
        snags_by_slno.setdefault(matched_item["slno"], []).append(
            (snag, matched_item, desc_enhanced, guessed_cat)
        )

    # Expand the checklist into one entry per matched snag. A checklist question
    # with N matching snags yields N rows; a question with no match still yields
    # its single unmatched row. Keeping only the first snag per slno silently
    # discarded the rest, which lost most of the captured snag points.
    expanded_items = []
    for item in checklist_items:
        hits = snags_by_slno.get(item["slno"], [])
        if not hits:
            expanded_items.append((item, None))
        else:
            for hit in hits:
                expanded_items.append((item, hit))

    for item, hit in expanded_items:
        slno = item["slno"]
        cat = _correct_report_text(settings.normalize_category(item["category"]))
        check_point, check_changes = correct_report_text_with_changes(item["check_points"])
        correction_log.extend(("Check Points", original, corrected) for original, corrected in check_changes)
        pri = item["priority"]
        vendor = _resolve_vendor(cat)
        stats[cat] += 1

        if hit:
            matched_count += 1
            snag, matched_item, desc_enhanced, guessed_cat = hit
            desc_raw = snag.get("description", "")
            # Use checklist item's area_location first, fallback to text extraction
            checklist_area = matched_item.get("area_location", "")
            guessed_area = extract_area_from_text(checklist_area) if checklist_area else extract_area_from_text(desc_enhanced or desc_raw)
            priority = determine_priority(desc_raw, matched_item)

            corrected_description, description_changes = correct_report_text_with_changes(desc_enhanced)
            correction_log.extend(("Snag Points", original, corrected) for original, corrected in description_changes)
            # Fallback: when the chat message carried no description (a common
            # WhatsApp pattern where photos are sent on their own), use the
            # matched checklist item's Snag Points so the row is not blank.
            if not corrected_description:
                checklist_snag = str(matched_item.get("snag_points", "") or "").strip()
                if checklist_snag:
                    corrected_description = checklist_snag
                    correction_log.append(("Snag Points", "", checklist_snag))
            # Use snag's actual date instead of current date
            snag_date = snag.get("date", "")
            if snag_date:
                try:
                    date_given = datetime.strptime(snag_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                except ValueError:
                    date_given = datetime.now().strftime("%d/%m/%Y")
            else:
                date_given = datetime.now().strftime("%d/%m/%Y")
            row_vals = [
                matched_count,
                project_facility_name,
                project_client_name,
                date_given,
                project_floor_name,
                guessed_area,
                cat,
                check_point,
                determine_status(desc_raw),
                corrected_description,
                priority,
            ]

            for col_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=row_num, column=col_idx, value=val)
                cell.alignment = DATA_ALIGN
                cell.border = STYLE_BORDER

            img_path = resized_map.get(snag["image_filename"])
            extra_paths = [resized_map.get(fn) for fn in snag.get("extra_image_filenames", [])]
            extra_paths = [p for p in extra_paths if p and os.path.exists(p)]
            # Grouped images: embed multiple images in columns L, M, N, O (up to 4 per row)
            # Each image is 200x200 pixels and fixed inside its cell
            image_columns = ["L", "M", "N", "O"]  # Support up to 4 grouped images
            all_img_paths = [img_path] + extra_paths if img_path else extra_paths
            
            for idx, path in enumerate(all_img_paths[:len(image_columns)]):
                if not path or not os.path.exists(path):
                    continue
                col_letter = image_columns[idx]
                try:
                    img = XLImage(path)
                    img.width = 200      # 200 pixels width
                    img.height = 200     # 200 pixels height
                    # Add image anchored to cell (fixed inside, not floating)
                    ws.add_image(img, f"{col_letter}{row_num}")
                    # Set column width to fit 200px image
                    ws.column_dimensions[col_letter].width = 26.0
                except Exception as e:
                    logging.warning("  Image embed failed row %d col %s: %s", row_num, col_letter, e)

            # Set row height to 200 points to fit 200x200 images
            ws.row_dimensions[row_num].height = 200
            for col_idx in range(12, 19):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.alignment = DATA_ALIGN
                cell.border = STYLE_BORDER
            if snag.get("media_missing"):
                ws.cell(row=row_num, column=12, value="Media file not included in ZIP export")
            ws.cell(row=row_num, column=16, value=vendor).border = STYLE_BORDER
            # Set Date Closed for closed snags
            status_val = determine_status(desc_raw)
            if status_val == "Closed":
                snag_date = snag.get("date", "")
                if snag_date:
                    try:
                        ws.cell(row=row_num, column=14, value=datetime.strptime(snag_date, "%Y-%m-%d").strftime("%d/%m/%Y")).border = STYLE_BORDER
                    except ValueError:
                        ws.cell(row=row_num, column=14, value=datetime.now().strftime("%d/%m/%Y")).border = STYLE_BORDER
                else:
                    ws.cell(row=row_num, column=14, value=datetime.now().strftime("%d/%m/%Y")).border = STYLE_BORDER
            # Set default SPOC values
            ws.cell(row=row_num, column=17, value="Project SPOC").border = STYLE_BORDER
            ws.cell(row=row_num, column=18, value="Transition SPOC").border = STYLE_BORDER
        else:
            unmatched_checklist += 1
            # Use checklist item's area_location instead of "All area"
            checklist_area = item.get("area_location", "")
            guessed_area = extract_area_from_text(checklist_area) if checklist_area else "All area"
            row_vals = [
                matched_count + unmatched_checklist,
                project_facility_name,
                project_client_name,
                "",
                project_floor_name,
                guessed_area,
                cat,
                check_point,
                "Open",
                "",
                pri,
            ]
            for col_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=row_num, column=col_idx, value=val)
                cell.alignment = DATA_ALIGN
                cell.border = STYLE_BORDER
            ws.cell(row=row_num, column=16, value=vendor).border = STYLE_BORDER
            ws.cell(row=row_num, column=17, value="Project SPOC").border = STYLE_BORDER
            ws.cell(row=row_num, column=18, value="Transition SPOC").border = STYLE_BORDER

        row_num += 1

    def _fallback_category_from_checklist(desc_raw: str) -> str:
        if not desc_raw:
            return "Unassigned"
        desc_words = set(w.lower() for w in re.findall(r"[a-zA-Z]+", desc_raw) if len(w) > 2)
        best_cat = "Unassigned"
        best_score = 0
        for item in checklist_items:
            item_cat = item.get("category", "")
            if not item_cat or item_cat.lower() in ("unassigned", "general"):
                continue
            item_text = f"{item.get('check_points', '')} {item.get('description', '')} {item.get('item', '')} {item.get('title', '')}"
            item_words = set(w.lower() for w in re.findall(r"[a-zA-Z]+", item_text) if len(w) > 2)
            overlap = len(desc_words & item_words)
            if overlap > best_score:
                best_score = overlap
                best_cat = item_cat
        return best_cat

    for snag, matched_item, desc_enhanced, guessed_cat in snag_with_match:
        if matched_item:
            continue
        unmatched_snag_count += 1
        desc_raw = snag.get("description", "")
        guessed_area = extract_area_from_text(desc_enhanced or desc_raw)
        if guessed_cat == "Unassigned":
            guessed_cat = _fallback_category_from_checklist(desc_raw)
        category = _correct_report_text(settings.normalize_category(guessed_cat))
        priority = determine_priority(desc_raw, None)
        vendor = _resolve_vendor(category)
        stats[category] += 1

        corrected_description, description_changes = correct_report_text_with_changes(desc_enhanced)
        # Use checklist Snag Points as fallback when description is empty
        if not corrected_description:
            checklist_snag = _get_checklist_snag_points(snag, checklist_items)
            if checklist_snag:
                corrected_description = checklist_snag
        correction_log.extend(("Snag Points", original, corrected) for original, corrected in description_changes)
        # Use snag's actual date instead of current date
        snag_date = snag.get("date", "")
        if snag_date:
            try:
                date_given = datetime.strptime(snag_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                date_given = datetime.now().strftime("%d/%m/%Y")
        else:
            date_given = datetime.now().strftime("%d/%m/%Y")
        row_vals = [
            matched_count + unmatched_checklist + unmatched_snag_count,
            project_facility_name,
            project_client_name,
            date_given,
            project_floor_name,
            guessed_area,
            category,
            "",
            determine_status(desc_raw),
            corrected_description,
            priority,
        ]

        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=row_num, column=col_idx, value=val)
            cell.alignment = DATA_ALIGN
            cell.border = STYLE_BORDER

            img_path = resized_map.get(snag["image_filename"])
            extra_paths = [resized_map.get(fn) for fn in snag.get("extra_image_filenames", [])]
            extra_paths = [p for p in extra_paths if p and os.path.exists(p)]
            primary_col = "L"
            for idx, path in enumerate([img_path] + extra_paths):
                if not path or not os.path.exists(path):
                    continue
                try:
                    img = XLImage(path)
                    img.width = 200
                    img.height = 200
                    ws.add_image(img, f"{primary_col if idx == 0 else 'M'}{row_num}")
                except Exception as e:
                    logging.warning("  Image embed failed row %d: %s", row_num, e)

            ws.row_dimensions[row_num].height = 200
            for col_idx in range(12, 19):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.alignment = DATA_ALIGN
                cell.border = STYLE_BORDER
            if snag.get("media_missing"):
                ws.cell(row=row_num, column=12, value="Media file not included in ZIP export")
        ws.cell(row=row_num, column=16, value=vendor).border = STYLE_BORDER
        # Set Date Closed for closed snags
        status_val = determine_status(desc_raw)
        if status_val == "Closed":
            snag_date = snag.get("date", "")
            if snag_date:
                try:
                    ws.cell(row=row_num, column=14, value=datetime.strptime(snag_date, "%Y-%m-%d").strftime("%d/%m/%Y")).border = STYLE_BORDER
                except ValueError:
                    ws.cell(row=row_num, column=14, value=datetime.now().strftime("%d/%m/%Y")).border = STYLE_BORDER
            else:
                ws.cell(row=row_num, column=14, value=datetime.now().strftime("%d/%m/%Y")).border = STYLE_BORDER
        # Set default SPOC values
        ws.cell(row=row_num, column=17, value="Project SPOC").border = STYLE_BORDER
        ws.cell(row=row_num, column=18, value="Transition SPOC").border = STYLE_BORDER
        row_num += 1

    for col_letter, width in COL_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width
    ws.freeze_panes = "A8"

    try:
        from snaglist_pro.summary_dashboard import add_summary_sheet
        # Dashboard metrics describe the snags that were actually found, not the
        # checklist questions that were printed with nothing against them. Every
        # checklist row with no snag is still emitted (that is what shows the
        # client what was looked for and not found), so counting rows reported
        # Open Snags = Total Snags = 409 on a 288-snag export. Column 10 holds
        # the Snag Points text, so it identifies the snag rows exactly.
        vendor_counts = Counter()
        priority_counts = Counter()
        category_counts = Counter()
        open_count = 0
        closed_count = 0
        snag_row_count = 0
        for r in range(8, row_num):
            if not str(ws.cell(row=r, column=10).value or "").strip():
                continue
            snag_row_count += 1
            v = ws.cell(row=r, column=16).value
            if v:
                vendor_counts[v] += 1
            p = ws.cell(row=r, column=11).value
            if p:
                priority_counts[p] += 1
            c = ws.cell(row=r, column=7).value
            if c:
                category_counts[c] += 1
            status = ws.cell(row=r, column=9).value
            if status == "Open":
                open_count += 1
            elif status == "Closed":
                closed_count += 1
        summary_stats = {
            "total": snag_row_count,
            "total_rows": row_num - 8,
            "matched": matched_count,
            "unmatched": unmatched_checklist + unmatched_snag_count,
            "unmatched_checklist": unmatched_checklist,
            "unmatched_snags": unmatched_snag_count,
            "checklist_items": len(checklist_items),
            "open": open_count,
            "closed": closed_count,
            "categories": dict(category_counts),
            "priorities": dict(priority_counts),
            "vendors": dict(vendor_counts),
        }
        add_summary_sheet(wb, summary_stats, data_sheet=ws.title)
    except ImportError:
        pass

    if correction_log:
        notes = wb.create_sheet("Correction Notes")
        notes.append(["Field", "Original", "Corrected"])
        seen = set()
        for field, original, corrected in correction_log:
            key = (field, original, corrected)
            if key not in seen:
                notes.append([field, original, corrected])
                seen.add(key)
        for cell in notes[1]:
            cell.font = HEADER_FONT
        notes.freeze_panes = "A2"
        notes.column_dimensions["A"].width = 18
        notes.column_dimensions["B"].width = 45
        notes.column_dimensions["C"].width = 45

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)

    logging.info("  Rows: %d | Checkpoint matched: %d | Unmatched checklist: %d | Unmatched snags: %d | Images: %d",
                 row_num - 8, matched_count, unmatched_checklist, unmatched_snag_count, len(resized_map))
    return output_path


def build_excel_google_sheets(
    snags: list,
    checklist_items: list,
    resized_map: dict,
    output_path: str,
    sheet_name: Optional[str] = None,
    snag_with_match: Optional[list] = None,
    project_client: Optional[str] = None,
    project_facility: Optional[str] = None,
    project_floor: Optional[str] = None,
) -> str:
    logging.info("Building Google Sheets Excel: %s", output_path)
    project_client_name = project_client or settings.project_default_client
    project_facility_name = project_facility or settings.project_default_facility
    project_floor_name = project_floor or settings.project_default_floor
    if not sheet_name:
        sheet_name = project_facility_name or "Snaglist"

    wb = openpyxl.Workbook()
    safe_name = sheet_name.replace("/", "-").replace("\\", "-").replace("?", "").replace("*", "").replace("[", "").replace("]", "").replace(":", "-").strip()[:31]
    if not safe_name:
        safe_name = "Snaglist"
    ws = wb.active
    ws.title = safe_name

    ws["A2"] = "Index"
    ws["I2"] = "Date"
    ws["J2"] = datetime.now()
    for cell in [ws["I2"], ws["J2"]]:
        cell.font = Font(bold=True)
        cell.fill = FILL_GREEN

    for col_idx, col_name in enumerate(SHEET_COLUMNS, start=1):
        cell = ws.cell(row=7, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = STYLE_BORDER
        if col_name == "Ref.images":
            cell.fill = FILL_YELLOW
        elif col_name == "Vendor name":
            cell.fill = FILL_ORANGE
        else:
            cell.fill = FILL_GREEN

    matched_count = 0
    unmatched_checklist = 0
    unmatched_snag_count = 0
    stats = Counter()
    row_num = 8

    if not snag_with_match:
        snag_with_match = []
        for snag in snags:
            desc_raw = snag.get("description", "")
            desc_enhanced = enhance_description(desc_raw)
            guessed_cat = guess_category(desc_enhanced or desc_raw)
            matched_item, _ = match_to_checklist(desc_raw, guessed_cat, checklist_items, desc_enhanced, None)
            snag_with_match.append((snag, matched_item, desc_enhanced, guessed_cat))

    for snag, matched_item, desc_enhanced, guessed_cat in snag_with_match:
        if matched_item:
            matched_count += 1
            desc_raw = snag.get("description", "")
            guessed_area = extract_area_from_text(desc_enhanced or desc_raw)
            category = settings.normalize_category(guessed_cat)
            priority = determine_priority(desc_raw, matched_item)
            vendor = _resolve_vendor(category)
            stats[category] += 1

            # Use snag's actual date instead of current date
            snag_date = snag.get("date", "")
            if snag_date:
                try:
                    date_given = datetime.strptime(snag_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                except ValueError:
                    date_given = datetime.now().strftime("%d/%m/%Y")
            else:
                date_given = datetime.now().strftime("%d/%m/%Y")

            row_vals = [
                matched_count,
                project_facility_name,
                project_client_name,
                date_given,
                project_floor_name,
                guessed_area,
                category,
                matched_item["check_points"],
                determine_status(desc_raw),
                _correct_report_text(desc_enhanced),
                priority,
                snag.get("image_filename", ""),
                "",
                "",
                "",
                vendor,
                "",
                "",
            ]
            for col_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=row_num, column=col_idx, value=val)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.border = STYLE_BORDER
            ws.row_dimensions[row_num].height = 30
        else:
            unmatched_checklist += 1
            # Use checklist item's area_location instead of empty
            checklist_area = matched_item.get("area_location", "") if matched_item else ""
            guessed_area = extract_area_from_text(checklist_area) if checklist_area else ""
            row_vals = [
                matched_count + unmatched_checklist,
                project_facility_name,
                project_client_name,
                "",
                project_floor_name,
                guessed_area,
                settings.normalize_category(guessed_cat),
                "",
                "Open",
                "",
                determine_priority(snag.get("description", ""), None),
            ]
            for col_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=row_num, column=col_idx, value=val)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.border = STYLE_BORDER
            ws.cell(row=row_num, column=16, value=get_vendor(settings.normalize_category(guessed_cat))).border = STYLE_BORDER
        row_num += 1

    for snag, matched_item, desc_enhanced, guessed_cat in snag_with_match:
        if matched_item:
            continue
        unmatched_snag_count += 1
        desc_raw = snag.get("description", "")
        guessed_area = guess_area(desc_enhanced or desc_raw)
        category = settings.normalize_category(guessed_cat)
        priority = determine_priority(desc_raw, None)
        vendor = get_vendor(category)
        stats[category] += 1

        # Use snag's actual date instead of current date
        snag_date = snag.get("date", "")
        if snag_date:
            try:
                date_given = datetime.strptime(snag_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                date_given = datetime.now().strftime("%d/%m/%Y")
        else:
            date_given = datetime.now().strftime("%d/%m/%Y")

        row_vals = [
            matched_count + unmatched_checklist + unmatched_snag_count,
            project_facility_name,
            project_client_name,
            date_given,
            project_floor_name,
            guessed_area,
            category,
            "",
            settings.project_default_status,
            desc_enhanced,
            priority,
            snag.get("image_filename", ""),
            "",
            "",
            "",
            vendor,
            "",
            "",
        ]
        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws.cell(row=row_num, column=col_idx, value=val)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = STYLE_BORDER
        # Set Date Closed for closed snags
        status_val = determine_status(desc_raw)
        if status_val == "Closed":
            snag_date = snag.get("date", "")
            if snag_date:
                try:
                    ws.cell(row=row_num, column=14, value=datetime.strptime(snag_date, "%Y-%m-%d").strftime("%d/%m/%Y")).border = STYLE_BORDER
                except ValueError:
                    ws.cell(row=row_num, column=14, value=datetime.now().strftime("%d/%m/%Y")).border = STYLE_BORDER
            else:
                ws.cell(row=row_num, column=14, value=datetime.now().strftime("%d/%m/%Y")).border = STYLE_BORDER
        # Set default SPOC values
        ws.cell(row=row_num, column=17, value="Project SPOC").border = STYLE_BORDER
        ws.cell(row=row_num, column=18, value="Transition SPOC").border = STYLE_BORDER
        ws.row_dimensions[row_num].height = 30
        row_num += 1

    for col_letter, width in COL_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width
    ws.freeze_panes = "A8"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)

    logging.info("  GS Rows: %d | Checkpoint matched: %d | Unmatched checklist: %d | Unmatched snags: %d | Images: %d",
                 row_num - 8, matched_count, unmatched_checklist, unmatched_snag_count, len(resized_map))
    return output_path


class SnaglistPipeline:
    def __init__(self):
        self.stats = {}

    def run(
        self,
        zip_path: str,
        checklist_path: str,
        output_dir: str,
        project_name: Optional[str] = None,
        db_session=None,
        progress_callback=None,
        fast_mode: bool = False,
        ai_enabled: Optional[bool] = None,
        license_check: bool = False,
    ) -> dict:
        if license_check:
            _check_license("report_generation")

        def _progress(step, message, percent):
            if progress_callback:
                progress_callback(step, message, percent)
        
        t0 = datetime.now()
        os.makedirs(output_dir, exist_ok=True)
        extract_dir = os.path.join(output_dir, "extracted")

        logging.info("=" * 50)
        logging.info("STEP 1: EXTRACT ZIP")
        text_content, image_map, attachment_map = extract_zip(zip_path, extract_dir)
        if not text_content:
            raise ValueError("No chat text found in ZIP!")
        _progress("extract", "Extracted ZIP", 10)

        if project_name is None:
            project_name = detect_project_name(text_content, zip_path)
        project_client = project_name if project_name and project_name != "Unknown Project" else ""
        project_facility = project_name if project_name and project_name != "Unknown Project" else "Unknown Project"
        project_floor = detect_project_floor(project_name)
        logging.info("  Project: %s", project_name)

        logging.info("=" * 50)
        logging.info("STEP 2: PARSE CHAT & PAIR IMAGES")
        messages = parse_chat_messages(text_content)
        logging.info("  Parsed %d raw messages", len(messages))
        _progress("parse", f"Parsed {len(messages)} messages", 20)

        ai_tracker = AICallTracker(
            max_calls=settings.max_ai_calls_per_run,
            enabled=ai_enabled,
        )
        logging.info("AI status: %s", ai_tracker.status())

        snags = pair_images_with_descriptions(messages, image_map, ai_tracker=ai_tracker)
        logging.info("  Paired %d snag items", len(snags))
        _progress("pair", f"Paired {len(snags)} snags", 35)

        logging.info("=" * 50)
        logging.info("STEP 3: DEDUPLICATE")
        snags = deduplicate_snags(snags)
        logging.info("  %d unique snags after dedup", len(snags))
        _progress("dedup", f"{len(snags)} unique snags", 45)

        # Drop photos captioned only with a progress note or a bare location
        # label. Done here rather than inside build_excel so that len(snags) -
        # the count the UI, the progress bar, snag_data.json and the saved
        # report all use - agrees with the rows actually written.
        before_filler = len(snags)
        snags = [s for s in snags if not is_filler_caption(s.get("description", ""))]
        filler_dropped = before_filler - len(snags)
        if filler_dropped:
            logging.info("  %d photo(s) captioned only with a progress note or "
                         "location label, not snag points", filler_dropped)
            _progress("filler", f"{len(snags)} snags after removing filler captions", 50)

        logging.info("=" * 50)
        logging.info("STEP 4: DEDUPLICATE BY PHASH")
        if not fast_mode:
            snags = deduplicate_by_phash(snags)
            logging.info("  %d snags after phash dedup", len(snags))
            _progress("phash", f"{len(snags)} after visual dedup", 55)
        else:
            _progress("phash", f"{len(snags)} snags (fast mode)", 55)

        logging.info("=" * 50)
        logging.info("STEP 5: LOAD CHECKLIST")
        checklist_items = load_checklist(checklist_path)
        _progress("checklist", f"Loaded {len(checklist_items)} checklist items", 60)

        logging.info("=" * 50)
        logging.info("STEP 6: RESIZE IMAGES")
        resized_map = resize_snag_images(snags, output_dir)
        logging.info("  Resized %d images", len(resized_map))
        _progress("resize", f"Resized {len(resized_map)} images", 70)

        logging.info("=" * 50)
        logging.info("STEP 7: COLLECT ATTACHMENT METADATA")
        attachment_entries = gather_attachment_entries(messages, attachment_map)
        logging.info("  Collected %d attachment entries", len(attachment_entries))
        _progress("attachments", "Collected attachments", 75)

        logging.info("=" * 50)
        logging.info("STEP 8: BUILD EXCEL")
        _progress("excel", "Building Excel...", 80)
        excel_name = f"{slugify_project(project_name)}.xlsx"
        excel_path = os.path.join(output_dir, excel_name)
        build_excel(
            snags, checklist_items, resized_map, excel_path,
            sheet_name=project_name[:31],
            ai_tracker=ai_tracker,
            project_client=project_client,
            project_facility=project_facility,
            project_floor=project_floor,
        )
        _progress("excel", "Excel built", 90)

        gs_excel_path = ""
        if not fast_mode:
            gs_excel_name = f"{slugify_project(project_name)}_gs.xlsx"
            gs_excel_path = os.path.join(output_dir, gs_excel_name)
            build_excel_google_sheets(
                snags, checklist_items, resized_map, gs_excel_path,
                sheet_name=project_name[:31],
                project_client=project_client,
                project_facility=project_facility,
                project_floor=project_floor,
            )

        logging.info("=" * 50)
        logging.info("STEP 9: SAVE REPORT")
        _progress("report", "Saving report...", 95)
        data_path = os.path.join(output_dir, "snag_data.json")
        report = {
            "project": project_name,
            "floor": project_floor,
            "generated_at": datetime.now().isoformat(),
            "total_snags": len(snags),
            "total_images": len(resized_map),
            "checklist_items": len(checklist_items),
            "duration_seconds": (datetime.now() - t0).total_seconds(),
            "output_excel": excel_path,
            "snags": [{
                "index": i + 1,
                "description": s.get("description", ""),
                "image": s.get("image_filename", ""),
                "sender": s.get("sender", ""),
                "timestamp": s.get("date", ""),
            } for i, s in enumerate(snags)],
        }
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        if ai_tracker and ai_tracker.enabled and not fast_mode:
            try:
                summary = generate_summary(snags)
                report["ai_summary"] = summary
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                logging.info("  AI summary generated (%d chars)", len(summary))
            except Exception as e:
                logging.warning("  AI summary failed: %s", e)

        if db_session:
            try:
                self._persist_to_db(db_session, project_name, snags, attachment_entries, project_facility, project_client, project_floor)
            except Exception as e:
                logging.warning("  DB persistence failed: %s", e)

        _progress("complete", "Pipeline complete", 100)

        elapsed = (datetime.now() - t0).total_seconds()
        logging.info("=" * 50)
        logging.info("PIPELINE COMPLETE")
        logging.info("  Duration: %.1f seconds", elapsed)
        logging.info("  Snags:    %d", len(snags))
        logging.info("  Images:   %d", len(resized_map))
        logging.info("  Output:   %s", excel_path)
        if ai_tracker:
            logging.info("  AI:       %s", ai_tracker.status())

        return {
            "project": project_name,
            "total_snags": len(snags),
            "total_images": len(resized_map),
            "excel_path": excel_path,
            "excel_gs_path": gs_excel_path,
            "data_path": data_path,
            "snags": snags,
        }

    def _persist_to_db(self, db_session, project_name: str, snags: list, attachment_entries: list, project_facility: str, project_client: str, project_floor: str):
        from snaglist_pro.models import Project, Snag as SnagModel, AttachmentRecord

        slug = slugify_project(project_name)
        project = db_session.query(Project).filter_by(slug=slug).first()
        if not project:
            project = Project(
                name=project_name,
                slug=slug,
                facility=project_facility,
                client=project_client,
                floor=project_floor,
            )
            db_session.add(project)
            db_session.flush()

        existing_count = db_session.query(SnagModel).filter_by(project_id=project.id).count()
        for i, s in enumerate(snags):
            snag_record = SnagModel(
                project_id=project.id,
                index=existing_count + i + 1,
                image_filename=s.get("image_filename", ""),
                image_path=s.get("image_path", ""),
                description=s.get("description", ""),
                sender=s.get("sender", ""),
                date_reported=s.get("date", ""),
            )
            db_session.add(snag_record)

        for att in attachment_entries:
            att_record = AttachmentRecord(
                project_id=project.id,
                attachment_name=att.get("attachment_name", ""),
                attachment_type=att.get("attachment_type", ""),
                file_size=att.get("file_size") or 0,
                file_path=att.get("attachment_path", ""),
                page_count=att.get("page_count"),
                layer_count=att.get("layer_count"),
                entity_count=att.get("entity_count"),
                layer_names=att.get("layer_names", ""),
                text_snippet=att.get("text_snippet", ""),
                keyword_summary=att.get("keyword_summary", ""),
                suggested_action=att.get("suggested_action", ""),
                referenced=att.get("referenced", False),
                reference_count=att.get("reference_count", 0),
                first_referenced_by=att.get("first_referenced_by", ""),
                first_reference_date=att.get("first_reference_date", ""),
                chat_notes=att.get("chat_notes", ""),
            )
            db_session.add(att_record)

        db_session.commit()
        logging.info("  Persisted %d snags and %d attachments to DB", len(snags), len(attachment_entries))


def main():
    parser = argparse.ArgumentParser(description="Snaglist Pipeline — Enhanced")
    parser.add_argument("--zip", "-z", required=True, help="Path to WhatsApp ZIP export")
    parser.add_argument("--checklist", "-c", default="C:\\Users\\vinee\\Downloads\\Untitled spreadsheet (2).xlsx", help="Path to checklist XLSX")
    parser.add_argument("--output", "-o", default="./output", help="Output directory")
    parser.add_argument("--project-name", "-n", help="Project name override")
    parser.add_argument("--db", action="store_true", help="Persist to database")

    args = parser.parse_args()

    pipeline = SnaglistPipeline()
    db_session = None
    if args.db:
        from snaglist_pro.database import init_db, get_session
        init_db()
        db_session = next(get_session())

    try:
        result = pipeline.run(
            zip_path=args.zip,
            checklist_path=args.checklist or "",
            output_dir=args.output,
            project_name=args.project_name,
            db_session=db_session,
        )
        print(f"\nDone. Excel: {result['excel_path']}")
        print(f"Snags: {result['total_snags']}")
    finally:
        if db_session:
            db_session.close()


if __name__ == "__main__":
    main()
