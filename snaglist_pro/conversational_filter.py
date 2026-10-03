"""
snaglist_pro.conversational_filter — Distinguish real snag reports from chatter
==============================================================================
WhatsApp chats mix site observations with casual messages ("ok", "noted",
greetings). This classifier keeps only actionable snag text so the checklist
matcher and the summary Match Rate are not polluted by conversational noise.

Design (keeps all dependencies already used by the project):
- A fast keyword/keyword-length pass avoids loading any model for tiny or
  obvious conversational turns.
- For the rest, embeddings come from the existing lazy sentence-transformer
  model in ``semantic_matcher`` (no new dependency, model loads on demand only
  when scoring is actually needed).

Public API:
    is_snag(text) -> bool
    snag_score(text) -> float          # 0.0 .. 1.0
    classify(text) -> dict             # {"is_snag": bool, "score": float, "reason": str}
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict

from snaglist_pro.semantic_matcher import embed, cosine_similarity

logger = logging.getLogger(__name__)

# Sentences that are almost always chatter, not observations.
_CONVERSATION_KEYWORDS = {
    "ok", "okay", "okie", "thanks", "thank you", "thx", "noted", "noted thanks",
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "pls", "please", "plz", "got it", "roger", "copy that", "understood",
    "ack", "acknowledged", "will check", "on it", "on my way", "coming",
    "yes", "no", "yeah", "yep", "nope", "fine", "fine thanks", "thankyou",
}

# Word-boundary regex so "ack" is NOT matched inside "cr**ack**" or "hi" inside "**hi**nd".
_CONV_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _CONVERSATION_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Lower-case token set looked up by whole word; used only for very short turns.
_CONV_TOKENS = {
    "ok", "okay", "noted", "thanks", "thx", "thanks!", "thanks.",
    "hi", "hello", "hey", "roger", "copy", "yeah", "yep", "nope", "fine",
    "plz", "pls", "no", "yes",
}

_SHORT_MIN_TOKENS = 3

# Representative real snag observations. Scored against these via cosine sim.
_SNAG_SEED_PHRASES = [
    "crack in the wall near the window",
    "water leak under the sink in the pantry",
    "door handle broken on the fire escape stair",
    "electrical socket not working in the bedroom",
    "tile missing on the balcony floor",
    "paint peeling off the ceiling in the passage",
    "floor level difference between lobby and corridor",
    "light fitting loose in the hallway",
    "grout missing between ceramic tiles",
    "window glass cracked on the ground floor",
    "fire extinguisher signage not aligned",
    "ceiling tile sagging near the duct",
    "door not closing properly due to frame issue",
    "stair nosing chipped on tread 3",
    "plumbing pipe leak behind the wc pan",
]

# Confidence thresholds (cosine similarity against the seed phrases).
_THRESH_SURE_NOT_SNAG = 0.0
_THRESH_MAYBE = 0.30
_THRESH_SURE_SNAG = 0.45

# Lazily computed embeddings for the seed phrases.
_SEED_EMBS = None


def _seed_embeddings():
    global _SEED_EMBS
    if _SEED_EMBS is None:
        _SEED_EMBS = [embed(p) for p in _SNAG_SEED_PHRASES]
    return _SEED_EMBS


def _tokenize(text: str):
    return re.findall(r"[A-Za-z]+", text.lower())


def classify(text: str) -> Dict[str, object]:
    """Return {"is_snag": bool, "score": float, "reason": str} for ``text``."""
    if not text or not text.strip():
        return {"is_snag": False, "score": 0.0, "reason": "empty"}

    tokens = _tokenize(text)

    # Obvious conversational short turns.
    if len(tokens) < _SHORT_MIN_TOKENS:
        if any(t in _CONV_TOKENS for t in tokens) or not tokens:
            return {"is_snag": False, "score": 0.0, "reason": "short chatter"}
        # Very short but specific text (e.g. "Leak") -> still needs scoring below.

    joined = " ".join(tokens)
    if _CONV_RE.search(joined):
        return {"is_snag": False, "score": 0.0, "reason": "conversational"}

    # Semantic similarity to known snag phrasing.
    text_emb = embed(text.lower())
    seed_embs = _seed_embeddings()
    best = max(cosine_similarity(text_emb, s) for s in seed_embs)
    best = max(0.0, min(1.0, best))

    if best >= _THRESH_SURE_SNAG:
        return {"is_snag": True, "score": best, "reason": "strong snag match"}
    if best >= _THRESH_MAYBE:
        return {"is_snag": False, "score": best, "reason": "uncertain, not flagged"}
    return {"is_snag": False, "score": best, "reason": "no snag signal"}


def is_snag(text: str) -> bool:
    return classify(text)["is_snag"]


def snag_score(text: str) -> float:
    return float(classify(text)["score"])


def is_conversational(text: str) -> bool:
    """Fast, model-free check for obvious chatter (greetings/acknowledgements).

    Unlike :func:`classify`, this never loads the embedding model, so it is safe to
    run on every snag description without slowing the pipeline.
    """
    if not text or not text.strip():
        return True
    tokens = _tokenize(text)
    if len(tokens) < _SHORT_MIN_TOKENS:
        if not tokens or any(t in _CONV_TOKENS for t in tokens):
            return True
    joined = " ".join(tokens)
    if _CONV_RE.search(joined):
        return True
    return False
