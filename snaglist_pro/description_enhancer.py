"""
snaglist_pro.description_enhancer — Description Cleaning & Classification
==========================================================================
Clean raw snag descriptions and guess category / area from keywords.
"""

import re
import logging
from typing import Set, Dict

logger = logging.getLogger(__name__)

ACRONYMS: Set[str] = {
    "AC", "AHU", "HVAC", "DB", "MCB", "RCCB", "ELCB", "UPS", "EPS",
    "LED", "LCD", "CCTV", "LAN", "WAN", "DHCP", "DNS", "NIC", "PoE",
    "RCP", "FFE", "MEP", "BMS", "FCU", "PAU", "VAV", "AHU", "DX",
    "GIS", "RCP", "PH", "WC", "VIP", "HOD", "CEO", "MD", "HR",
    "SOP", "MSDS", "PPE", "HSE", "QA", "QC", "RCA", "CAPA",
    "VRV", "VRF", "MCC", "LT", "HT", "CPVC", "UPVC", "PVC",
    "MCP", "FM200", "HDPE", "GI", "MS", "SS", "GRP", "FRP",
    "DG", "AHU", "FCU", "PAU", "VAV", "FCU",
}

PHRASE_FIXES: Dict[str, str] = {
    "to be install": "to be installed",
    "to be installe": "to be installed",
    "to be fix": "to be fixed",
    "to be repair": "to be repaired",
    "to be replace": "to be replaced",
    "to be paint": "to be painted",
    "to be clean": "to be cleaned",
    "to be remove": "to be removed",
    "to be provide": "to be provided",
    "need to be install": "needs to be installed",
    "need to be fix": "needs to be fixed",
    "need to be repair": "needs to be repaired",
    "need to be replace": "needs to be replaced",
    "should be install": "should be installed",
    "should be fix": "should be fixed",
    "should be repair": "should be repaired",
    "should be replace": "should be replaced",
    "not working condition": "not working",
    "in working condition": "working",
    "leakage": "leak",
    "watre": "water",
    "electrial": "electrical",
    "celing": "ceiling",
    "seeling": "ceiling",
    "flase": "false",
    "cellin": "ceiling",
    "fals ceiling": "false ceiling",
    "plywood": "plywood",
    "pliewood": "plywood",
    "handel": "handle",
    "holse": "hole",
    "rectify": "rectified",
    "dammage": "damage",
    "damage": "damaged",
    "dented": "dent",
    "scrach": "scratch",
    "scrath": "scratch",
    "broken down": "broken",
    "not function": "not working",
    "out of order": "not working",
    "not in use": "not working",
    "does not work": "not working",
    "dont work": "not working",
    "wont work": "not working",
    "not working properly": "not working",
    "not working condition": "not working",
    "not propely": "not working",
    "not proper": "not working",
    "not work": "not working",
    "needs to be": "to be",
    "need to be": "to be",
    "required to be": "to be",
    "provision for": "provide",
    "arrangement for": "provide",
    "making good": "make good",
    "makegood": "make good",
}

CATEGORY_KEYWORDS: Dict[str, list] = {
    "Electrical": [
        "earthing", "detector", "electrical", "wiring", "cable", "switch",
        "socket", "mcb", "db", "panel", "light", "lighting", "gland",
        "power", "rack", "commissioning", "fan", "exhaust", "conduit",
        "ups", "cctv", "camera", "emergency light", "exit sign",
        "indicator", "beacon", "hooter", "push button", "contactor",
        "relay", "timer", "dim", "regulator", "inverter", "battery",
        "charger", "stabilizer", "transformer", "busbar", "trunking",
        "heater", " immersion", "geyser", "motor", "starter",
    ],
    "HVAC": [
        "ac", "ahu", "hvac", "duct", "cooling", "outdoor unit", "indoor unit",
        "fcu", "chiller", "ventilation", "fresh air", "diffuser",
        "thermostat", "temperature", "compressor", "condenser", "gas charging",
        "refrigerant", "blower", "fan coil", "cassette", "split",
        "vrv", "vrf", "insulation", "grille", "damper", "actuator",
        "air handling", "precool", "heating", "coil", "cooling tower",
        "pump", "condensate", "drain pan", "filter",
    ],
    "Plumbing": [
        "plumb", "pipe", "drainage", "drain", "water", "tap", "faucet",
        "wc", "toilet", "bathroom", "sanitary", "leak", "valve",
        "sink", "basin", "cistern", "flush", "sewage", "sump",
        "grease trap", "septic", "water supply", "cpvc", "upvc",
        "pvc", "pipe clamp", "bibcock", "diverter", "shower",
        "urinal", "trap", " overflow", "soak pit",
    ],
    "Civil": [
        "civil", "crack", "plaster", "tile", "flooring", "wall", "ceiling",
        "masonry", "concrete", "paint", "putty", "grouting", "glass",
        "partition", "stain", "false ceiling", "gypsum",
        "waterproofing", "damp", "seepage", "brick", "block work",
        "screed", "leveling", "skirting", "cornice", "expansion joint",
        "sealant", "filler", "pop", "plaster of paris", "render",
        "patch", "repair work",
    ],
    "Fire Safety": [
        "fire", "sprinkler", "extinguisher", "smoke", "hose", "hydrant", "fls",
        "alarm", "detector", "heat detector", "manual call point", "mcp",
        "siren", "fire rated", "fire door", "fire damper", "fire seal",
        "firestop", "fire proof", "fire suppression", "gas suppression",
        "novec", "fm200", "co2 flooding", "emergency lighting",
        "fire exit", "evacuation", "signage",
    ],
    "Network/IT": [
        "network", "data", "lan", "cable tray", "patch", "wifi", "access point",
        "router", "switch", "server", "modem", "firewall", "cat6",
        "cat5", "rj45", "faceplate", "keystone", "patch panel",
        "structured cabling", "fiber", "optic", "poe", "rack",
        "ups", "crm", "door access", "access control", "biometric",
    ],
    "Furniture": [
        "furniture", "workstation", "chair", "table", "cubicle", "cabin",
        "pedestal", "keys", "drawer", "shelf", "cabinet", "locker",
        "sofa", "seating", "bench", "stool", "desk", "credenza",
        "bookcase", "partition", "counter", "modular furniture",
    ],
    "Interior": [
        "interior", "door", "window", "partition", "glass", "frame",
        "paint", "painting", "fascad", "writing board", "wallpaper",
        "cladding", "panel", "veneer", "laminate", "flooring",
        "carpet", "vinyl", "curtain", "blind", "screen",
        "signage", "name board", "display", "acoustic",
    ],
    "Cleaning": [
        "clean", "cleaning", "dust", "dirt", "rubbish", "waste",
        "garbage", "trash", "debris", "sweep", "mop", "scrub",
        "sanitize", "housekeeping", "janitor", "discard", "remove debris",
    ],
}

AREA_KEYWORDS: Dict[str, list] = {
    "Reception": ["reception", "lobby", "entrance", "front desk", "foyer", "waiting"],
    "Pantry": ["pantry", "kitchen", "cafeteria", "break room", "canteen", "tea point"],
    "Washroom": [
        "washroom", "toilet", "restroom", "bathroom", "wc", "urinal",
        "lavatory", "water closet",
    ],
    "Corridor": ["corridor", "hallway", "passage", "aisle", "walkway", "lobby"],
    "Conference Room": [
        "conference", "meeting room", "board room", "seminar",
        "training room", "discussion room", "boardroom",
    ],
    "Cabin": ["cabin", "office", "room", "chamber", "bay"],
    "Workstation Area": ["workstation", "work station", "cubicle area", "desk area"],
    "Staircase": ["stair", "staircase", "stairwell", "stairway", "fire escape"],
    "Parking": ["parking", "basement", "garage", "car park", "lot", "parking area"],
    "Lift Lobby": ["lift", "elevator", "lift lobby", "lift area", "elevator lobby"],
    "Server Room": ["server room", "server", "data center", "computer room", "server rack"],
    "Storage": ["storage", "store room", "store", "godown", "warehouse"],
    "Terrace": ["terrace", "roof", "rooftop", "deck", "balcony", "terrace garden"],
    "Facade": ["facade", "exterior", "outside", "outer", "building front", "elevation"],
    "Landscaping": [
        "landscape", "garden", "lawn", "plant", "tree", "green area",
        "planter", "shrub",
    ],
    "Electrical Room": [
        "electrical room", "panel room", "db room", "mcc room",
        "generator room", "transformer room", "lt panel", "ht panel",
    ],
    "AHU Room": [
        "ahu room", "ahu area", "mechanical room", "plant room",
        "chiller room", "ac plant",
    ],
}


def _fix_whitespace(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _capitalize_first(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _ensure_trailing_period(text: str) -> str:
    text = text.rstrip()
    if text and not text[-1] in (".", "!", "?"):
        text += "."
    return text


def _uppercase_acronyms(text: str) -> str:
    tokens = text.split()
    result: list = []
    for token in tokens:
        stripped = token.strip(".,!?;:")
        upper = stripped.upper()
        if upper in ACRONYMS:
            result.append(token.replace(stripped, upper))
        else:
            result.append(token)
    return " ".join(result)


def _apply_phrase_fixes(text: str) -> str:
    result = text
    for old, new in PHRASE_FIXES.items():
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        result = pattern.sub(new, result)
    return result


def enhance_description(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        return ""

    text = _fix_whitespace(raw_text)
    text = _apply_phrase_fixes(text)
    text = _uppercase_acronyms(text)
    text = _capitalize_first(text)
    text = _ensure_trailing_period(text)

    return text


def _check_keyword(text: str, keyword: str) -> bool:
    """Check if keyword appears in text. Uses word boundaries for single words."""
    if " " in keyword:
        return keyword in text
    return bool(re.search(r"\b" + re.escape(keyword) + r"\w*\b", text))


def _score_keywords(text: str, keywords: dict) -> tuple:
    """Score each category/area by matched keywords. Returns (best_label, best_score)."""
    low = text.lower()
    best_label = ""
    best_score = 0
    for label, kws in keywords.items():
        score = 0
        for kw in kws:
            if _check_keyword(low, kw):
                score += 1
        if score > best_score:
            best_score = score
            best_label = label
    return best_label, best_score


def guess_category(text: str) -> str:
    if not text:
        return "Unassigned"
    label, score = _score_keywords(text, CATEGORY_KEYWORDS)
    return label if score > 0 else "Unassigned"


def guess_area(text: str) -> str:
    if not text:
        return ""
    label, score = _score_keywords(text, AREA_KEYWORDS)
    return label if score > 0 else ""
