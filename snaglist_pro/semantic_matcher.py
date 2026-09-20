"""
snaglist_pro.semantic_matcher — Semantic matching via sentence-transformers
===========================================================================
Lazy-loads a lightweight embedding model to enable semantic matching:
  "paint peeling off" ↔ "check paint condition"  (no token overlap)
"""

import os
import logging
import numpy as np
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        logger.info("Loading semantic model: %s", _MODEL_NAME)
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(_MODEL_NAME)
        logger.info("Model loaded (dim=%d)", _MODEL.get_embedding_dimension())
    return _MODEL


@lru_cache(maxsize=2048)
def _encode(text: str):
    return _get_model().encode(text, normalize_embeddings=True)


def embed(text: str) -> np.ndarray:
    return _encode(text)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def guess_category_semantic(text: str, categories: list) -> tuple:
    if not text:
        return "", 0.0
    if not categories:
        return "", 0.0

    text_emb = embed(text)
    best_label = ""
    best_score = 0.0

    for cat in categories:
        cat_emb = embed(cat)
        score = cosine_similarity(text_emb, cat_emb)
        if score > best_score:
            best_score = score
            best_label = cat

    return best_label, best_score


def semantic_match(description: str, checklist_items: list, top_n: int = 3) -> list:
    if not description or not checklist_items:
        return []

    desc_emb = embed(description.lower())

    results = []
    for item in checklist_items:
        check_text = item["check_points"].lower()
        check_emb = _encode(check_text)
        sim = cosine_similarity(desc_emb, check_emb)
        results.append((sim, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_n]
