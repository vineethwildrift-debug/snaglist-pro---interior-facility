"""
snaglist_pro.ai_client — Local Ollama AI (text + optional vision)
=================================================================
Provides:
- Description enhancement/rewriting
- Smart categorization and area detection
- Executive summary generation
- Photo description for snags whose WhatsApp message carried no caption

All AI is local via Ollama. No cloud API keys are required. Vision is opt-in:
set OLLAMA_VISION_MODEL to the name of a vision-capable model (e.g.
"minicpm-v4.6:1b") to enable image description; otherwise describe_image()
returns the fallback text unchanged.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Docker-based Ollama connection
_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
# Fallback to localhost for local runs
if not os.environ.get("OLLAMA_URL"):
    try:
        requests.get(_OLLAMA_URL, timeout=2)
    except:
        _OLLAMA_URL = "http://localhost:11434"

_TEXT_MODEL = os.environ.get("OLLAMA_TEXT_MODEL", "llama2")
_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "")
_VISION_MAX_CALLS = int(os.environ.get("OLLAMA_VISION_MAX_CALLS", "200"))
_REQUEST_TIMEOUT = int(os.environ.get("AI_REQUEST_TIMEOUT", "120"))

# Module-level call counter for the vision fallback so a large chat cannot
# produce an unbounded number of model calls in one run.
_vision_calls = 0


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


def _call_ollama_chat(model: str, prompt: str, images: Optional[List[str]] = None,
                      max_tokens: int = 512, temperature: float = 0.1) -> Optional[str]:
    """Call Ollama via the /api/chat endpoint.

    Used for vision models that emit a thinking block by default; the
    ``think: false`` option is honoured here (it is ignored by /api/generate
    on some model versions), so the returned content is the final answer
    rather than the chain-of-thought.
    """
    if not _is_ollama_available():
        return None
    if not _check_model_available(model):
        return None

    content = prompt
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "think": False,
        },
    }
    if images:
        # Ollama accepts images as an "images" array of base64 strings on the
        # user message. Content parts with image_url objects are rejected
        # with status 400 on this model version.
        payload["messages"][0]["images"] = images

    try:
        resp = requests.post(
            f"{_OLLAMA_URL}/api/chat",
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            msg = data.get("message", {})
            text = (msg.get("content") or "").strip()
            # Some vision models (e.g. MiniCPM-V 4.6) ignore ``think: false``
            # and emit the answer into the thinking block while leaving content
            # empty. Fall back to the thinking block so the description is not
            # silently dropped.
            if not text:
                thinking = (msg.get("thinking") or "").strip()
                if thinking:
                    text = thinking
            if text:
                return text
        else:
            logger.warning("Ollama chat returned status %d for model %s", resp.status_code, model)
    except requests.exceptions.Timeout:
        logger.warning("Ollama chat timed out for model %s", model)
    except Exception as e:
        logger.warning("Ollama chat failed for model %s: %s", model, e)

    return None


def _encode_images(images: List[str]) -> List[str]:
    """Encode image paths as raw base64 strings for Ollama.

    The /api/chat endpoint accepts an "images" array of base64-encoded image
    bytes on the user message. Wrapping the bytes in a data: URI is rejected
    with status 400.
    """
    encoded = []
    for path in images:
        try:
            with open(path, "rb") as fh:
                encoded.append(base64.b64encode(fh.read()).decode("utf-8"))
        except Exception as e:
            logger.warning("Failed to encode image %s: %s", path, e)
    return encoded


def describe_image(image_path: str, fallback_text: str = "") -> str:
    """Describe a construction snag photo when the chat carried no caption.

    Uses a vision-capable local Ollama model to inspect the image and produce a
    concise snag description. Returns the fallback text (or "") when no model
    is available or the call fails, so callers can fall back to other logic.

    A module-level call counter bounds the number of vision calls per run so a
    large chat cannot produce an unbounded number of model invocations.
    """
    global _vision_calls
    if not image_path or not os.path.exists(image_path):
        return (fallback_text or "").strip()

    if _vision_calls >= _VISION_MAX_CALLS:
        logger.debug("Vision call budget exhausted (%d)", _VISION_MAX_CALLS)
        return (fallback_text or "").strip()

    prompt = (
        "You are a construction site inspector. Look at this photo of a building "
        "snag and write a concise, professional snag description (max 60 words). "
        "Describe what is wrong or needs attention. Output ONLY the description, "
        "nothing else.\n\n"
        + (f"Context from the chat: {fallback_text}\n\n" if fallback_text else "")
    )

    if not _VISION_MODEL or not _check_model_available(_VISION_MODEL):
        return (fallback_text or "").strip()

    encoded = _encode_images([image_path])
    if not encoded:
        return (fallback_text or "").strip()

    _vision_calls += 1
    response = _call_ollama_chat(
        model=_VISION_MODEL,
        prompt=prompt,
        images=encoded,
        max_tokens=200,
        temperature=0.1,
    )
    if response:
        return response.strip()

    return (fallback_text or "").strip()


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
