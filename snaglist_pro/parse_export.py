"""
snaglist_pro.parse_export — WhatsApp Chat Export Parser
========================================================
Parses WhatsApp chat export text into structured snag records.
"""

import re
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

# Matches WhatsApp message start: date, time, sender, message body
_MSG_PATTERN = re.compile(
    r"^(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*-\s*([^:]+?):\s*(.*)",
    re.MULTILINE,
)

_MEDIA_PATTERN = re.compile(
    r"(?:<attached:\s*([^>]+)>|([\w\-]+\.(?:jpg|jpeg|png|gif|mp4|avi|mov|pdf))\s+\(file attached\)|<Media\s+omitted>)",
    re.IGNORECASE,
)

_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%Y/%m/%d",
]


def _normalize_date(raw_date: str) -> str:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    logger.warning("Could not parse date: %s, leaving as-is", raw_date)
    return raw_date


def extract_media_refs(text: str) -> List[str]:
    refs: List[str] = []
    for match in _MEDIA_PATTERN.finditer(text):
        groups = match.groups()
        if groups[0]:
            refs.append(groups[0].strip())
        elif groups[1]:
            refs.append(groups[1].strip())
        else:
            refs.append("<Media omitted>")
    return refs


def parse_whatsapp_text(text_content: str) -> List[Dict]:
    if not text_content or not text_content.strip():
        logger.warning("Empty text content provided to parse_whatsapp_text")
        return []

    matches = list(_MSG_PATTERN.finditer(text_content))
    if not matches:
        logger.warning("No WhatsApp messages found in text")
        return []

    records: List[Dict] = []
    for match in matches:
        date_raw = match.group(1).strip()
        time_raw = match.group(2).strip()
        sender = match.group(3).strip()
        body = match.group(4).strip()

        date_normalized = _normalize_date(date_raw)
        has_media = bool(_MEDIA_PATTERN.search(body))
        media_files = extract_media_refs(body)

        # Remove the media marker text from the message body for cleanliness
        clean_body = _MEDIA_PATTERN.sub("", body).strip()

        records.append({
            "date": date_normalized,
            "time": time_raw,
            "sender": sender,
            "message": clean_body,
            "has_media": has_media,
            "media_files": media_files,
        })

    logger.info("Parsed %d messages from WhatsApp export", len(records))
    return records


def extract_media_refs(text: str) -> list:
    refs = []
    attached = re.findall(r"<attached:\s*(.+?)>", text)
    refs.extend(attached)
    img_attached = re.findall(r"(IMG-\d{8}-WA\d+\.\w+)\s*\(file attached\)", text)
    refs.extend(img_attached)
    vid_attached = re.findall(r"(VID-\d{8}-WA\d+\.\w+)\s*\(file attached\)", text)
    refs.extend(vid_attached)
    if "<Media omitted>" in text:
        refs.append("__MEDIA_OMITTED__")
    return refs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    sample = (
        "20/07/2026, 10:30:45 - Alice: Found a crack in the wall near the window.\n"
        "This is a multi-line description that continues here.\n"
        "20/07/2026, 11:15:00 - Bob: Water leak under sink. <attached: IMG_001.jpg>\n"
        "21/07/2026, 09:00:30 - Alice: Electrical socket not working. IMG_002.jpg (file attached)\n"
        "1/2/26, 3:30 PM - Charlie: Door handle broken. <Media omitted>\n"
    )

    results = parse_whatsapp_text(sample)
    for r in results:
        print(f"[{r['date']} {r['time']}] {r['sender']}: {r['message'][:60]:<60} media={r['has_media']}")
    print(f"\nTotal messages parsed: {len(results)}")
