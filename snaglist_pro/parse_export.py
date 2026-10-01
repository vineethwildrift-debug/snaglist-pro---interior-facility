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

# Matches standard and bracketed WhatsApp message starts.
_MSG_PATTERN = re.compile(
    r"^\[?(?P<date>\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})[ \t]*,[ \t]*(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:[ \t\u202f]*[APap][Mm])?)\]?[ \t]*(?:-[ \t]*)?(?P<sender>[^:\r\n]+):[ \t]*(?P<body>.*?)(?=^\[?\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}[ \t]*,|\Z)",
    re.MULTILINE | re.DOTALL,
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

_NUMBERED_OBSERVATION_RE = re.compile(r"^\s*\d+[.)]\s+(.+?)\s*$")


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
    """Parse WhatsApp messages, with grouping support for multi-image snags.
    
    When a sender sends multiple images with a single description, WhatsApp lists
    each image reference on separate lines or messages. This parser detects grouped
    images by checking if consecutive messages from the same sender have media but no
    text description—and applies the description from the first image to all subsequent
    images in the group.
    """
    if not text_content or not text_content.strip():
        logger.warning("Empty text content provided to parse_whatsapp_text")
        return []

    matches = list(_MSG_PATTERN.finditer(text_content))
    if not matches:
        logger.warning("No WhatsApp messages found in text")
        return []

    records: List[Dict] = []
    for match in matches:
        date_raw = match.group("date").strip()
        time_raw = match.group("time").strip()
        sender = match.group("sender").strip()
        body = match.group("body").strip()

        date_normalized = _normalize_date(date_raw)
        observation_lines = []
        current_observation = None
        for line in body.splitlines():
            numbered_match = _NUMBERED_OBSERVATION_RE.match(line)
            if numbered_match:
                if current_observation:
                    observation_lines.append(current_observation)
                current_observation = numbered_match.group(1)
            elif current_observation and line.strip():
                current_observation = f"{current_observation} {line.strip()}"
        if current_observation:
            observation_lines.append(current_observation)

        message_bodies = observation_lines if len(observation_lines) >= 2 else [body]
        for message_body in message_bodies:
            has_media = bool(_MEDIA_PATTERN.search(message_body))
            media_files = extract_media_refs(message_body)
            clean_body = _MEDIA_PATTERN.sub("", message_body).strip()
            records.append({
                "date": date_normalized,
                "time": time_raw,
                "sender": sender,
                "message": clean_body,
                "has_media": has_media,
                "media_files": media_files,
            })

    # Apply grouped image logic: if a message has media but no text, and the previous
    # message from the same sender had a description, apply that description to this group.
    _apply_grouped_image_descriptions(records)
    
    logger.info("Parsed %d messages from WhatsApp export", len(records))
    return records


def _apply_grouped_image_descriptions(records: List[Dict]) -> None:
    """Apply the first group member's description to all subsequent images from same sender."""
    for i in range(1, len(records)):
        curr = records[i]
        prev = records[i - 1]
        
        # If current message has media and same sender as previous, and previous had a description
        if (
            curr.get("has_media")
            and curr.get("sender") == prev.get("sender")
            and prev.get("message", "").strip()
            and not curr.get("message", "").strip()
        ):
            # Apply previous description to current message
            curr["message"] = prev.get("message", "")
            curr["is_grouped_image"] = True
            logger.debug(f"Applied grouped image description: '{curr['message'][:50]}...'")


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
