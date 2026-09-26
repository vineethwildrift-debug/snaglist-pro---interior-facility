"""
snaglist_pro.ai_client — Text AI only (Ollama local text model)
=================================================================
Provides:
- Description enhancement/rewriting
- Smart categorization and area detection
- Executive summary generation

Vision model removed — only text processing is supported.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
_TEXT_MODEL = os.environ.get("OLLAMA_TEXT_MODEL", "llama3.2")
_REQUEST_TIMEOUT = int(os.environ.get("AI_REQUEST_TIMEOUT", "120"))


def _is_ollama_available() -> bool:
    try:
        resp = requests.get(f"{_OLLAMA_URL}/", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def _check_model_available(model: str) -> bool:
    try:
        resp = requests.get(f"{_OLLAMA_URL}/api/tags", timeout=10)
        if resp.status_code != 200:
            return False
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        return any(model == m or m.startswith(model + ":") for m in models)
    except Exception:
        return False


def _call_ollama(model: str, prompt: str, images: Optional[List[str]] = None,
                 max_tokens: int = 512, temperature: float = 0.1) -> Optional[str]:
    if not _is_ollama_available():
        logger.debug("Ollama not available at %s", _OLLAMA_URL)
        return None

    if not _check_model_available(model):
        logger.debug("Model %s not available locally", model)
        return None

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    if images:
        payload["images"] = images

    try:
        resp = requests.post(
            f"{_OLLAMA_URL}/api/generate",
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("response", "").strip()
            if text:
                return text
        else:
            logger.warning("Ollama returned status %d for model %s", resp.status_code, model)
    except requests.exceptions.Timeout:
        logger.warning("Ollama request timed out for model %s", model)
    except Exception as e:
        logger.warning("Ollama call failed for model %s: %s", model, e)

    return None


def enhance_description(raw_text: str) -> str:
    if not raw_text or not raw_text.strip():
        return ""

    prompt = (
        "You are a construction snag description writer. Rewrite the following raw chat message "
        "into a clear, professional snag description. Fix grammar, spelling, and abbreviations. "
        "Keep it concise (max 100 words). Output ONLY the rewritten description, nothing else.\n\n"
        f"Raw: {raw_text}"
    )

    response = _call_ollama(
        model=_TEXT_MODEL,
        prompt=prompt,
        max_tokens=200,
        temperature=0.1,
    )

    if response:
        return response.strip()

    return raw_text.strip()


def guess_category_and_area(text: str) -> tuple[str, str]:
    prompt = (
        "You are a construction snag classifier. Given the following description, classify it into "
        "exactly one category and one area.\n\n"
        "Categories: Electrical, HVAC, Plumbing, Civil, Fire Safety, Network/IT, Furniture, "
        "Interior, Cleaning, Unassigned\n"
        "Areas: Reception, Pantry, Washroom, Corridor, Conference Room, Cabin, Workstation Area, "
        "Staircase, Parking, Lift Lobby, Server Room, Storage, Terrace, Facade, Landscaping, "
        "Electrical Room, AHU Room, or empty string if unknown\n\n"
        f"Description: {text}\n\n"
        "Respond in this exact format:\nCategory: <category>\nArea: <area>"
    )

    response = _call_ollama(
        model=_TEXT_MODEL,
        prompt=prompt,
        max_tokens=100,
        temperature=0.1,
    )

    if response:
        category = "Unassigned"
        area = ""
        for line in response.split("\n"):
            line_lower = line.lower()
            if line_lower.startswith("category:"):
                category = line.split(":", 1)[1].strip()
            elif line_lower.startswith("area:"):
                area = line.split(":", 1)[1].strip()
        valid_categories = {
            "Electrical", "HVAC", "Plumbing", "Civil", "Fire Safety",
            "Network/IT", "Furniture", "Interior", "Cleaning", "Unassigned",
        }
        if category not in valid_categories:
            category = "Unassigned"
        return category, area

    return "Unassigned", ""


def generate_summary(snags: List[Dict[str, Any]]) -> str:
    if not snags:
        return "No snags found."

    sample = "\n".join(
        f"- {s.get('description', '')[:100]} [{s.get('category', 'Unassigned')}]"
        for s in snags[:20]
    )

    prompt = (
        "You are a construction project manager. Write a brief executive summary (max 150 words) "
        "of the following snag list. Mention total count, main categories, and any high-priority items.\n\n"
        f"Total snags: {len(snags)}\n"
        f"Sample snags:\n{sample}"
    )

    response = _call_ollama(
        model=_TEXT_MODEL,
        prompt=prompt,
        max_tokens=300,
        temperature=0.2,
    )

    if response:
        return response.strip()

    return f"Total snags: {len(snags)}. AI summary unavailable."


def is_ai_available() -> bool:
    return _is_ollama_available() and _check_model_available(_TEXT_MODEL)


def get_status() -> Dict[str, Any]:
    return {
        "ollama_available": _is_ollama_available(),
        "text_model": _TEXT_MODEL,
        "text_model_available": _check_model_available(_TEXT_MODEL),
        "ai_enabled": is_ai_available(),
    }
