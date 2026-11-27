import logging
import time
import uuid

from flask import Blueprint, current_app, jsonify, request

from . import ratelimit
from .services import engine, vision

api = Blueprint("api", __name__)
log = logging.getLogger("foodlens.api")
MAX_AI_DIET_ITEMS = 40

# File signatures: never trust the browser-supplied MIME type or filename.
def _sniff(data):
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _client_ip():
    return request.remote_addr or "unknown"


def _error(message, status, code, rid):
    return jsonify({"error": message, "code": code, "request_id": rid}), status


@api.get("/health")
def health():
    return jsonify({"status": "ok"})  # no provider/model details on purpose


@api.get("/mode")
def mode():
    cfg = current_app.config
    provider = str(cfg.get("VISION_PROVIDER", "") or "").strip().lower()
    return jsonify({
        "demo_mode": provider == "mock",
        "photo_scan_available": provider == "gemini" and bool(cfg.get("GEMINI_API_KEY")),
    })


@api.get("/diets")
def diets():
    return jsonify({"diets": list(engine.DIETS), "allergens": engine.allergen_names()})


@api.post("/analyze")
def analyze():
    rid, started = uuid.uuid4().hex[:8], time.monotonic()
    cfg = current_app.config

    if not ratelimit.allow(_client_ip(), cfg["RATE_LIMIT_PER_MIN"]):
        return _error("Too many checks. Please wait a minute and try again.", 429, "RATE_LIMITED", rid)

    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    form = request.form

    diet = str(form.get("diet") or data.get("diet") or "halal").lower()
    if diet not in engine.DIETS:
        return _error("Choose one of the listed diets.", 400, "INVALID_DIET", rid)

    raw_allergies = form.getlist("allergies") or data.get("allergies") or []
    if not isinstance(raw_allergies, list) or not all(isinstance(a, str) for a in raw_allergies):
        return _error("Allergies must be a list.", 400, "INVALID_ALLERGIES", rid)
    allergies = [a.lower() for a in raw_allergies]
    if any(a not in engine.allergen_names() for a in allergies):
        return _error("Choose allergies from the list.", 400, "INVALID_ALLERGIES", rid)

    image = request.files.get("image")
    text = form.get("ingredients") or data.get("ingredients")
    precautionary = []
    provider = None

    if image:
        blob = image.read(cfg["MAX_IMAGE_BYTES"] + 1)
        if not blob:
            return _error("That file is empty.", 400, "INVALID_IMAGE", rid)
        if len(blob) > cfg["MAX_IMAGE_BYTES"]:
            return _error("That photo is too large. Try a smaller one.", 413, "FILE_TOO_LARGE", rid)
        mime = _sniff(blob)
        if not mime:
            return _error("Upload a JPG, PNG or WebP image.", 415, "UNSUPPORTED_MEDIA_TYPE", rid)
        try:
            provider = vision.get_provider(cfg)
            extracted = provider.extract(blob, mime)
        except vision.VisionError as exc:
            return _error(str(exc), exc.status, exc.code, rid)
        if not extracted.get("legible", False):
            return _error("We couldn't read the complete ingredients list. Try a closer, brighter photo or type it in.",
                          422, "UNREADABLE_LABEL", rid)
        ingredients, precautionary = extracted["ingredients"], extracted.get("precautionary", [])
        source = "image"
    elif isinstance(text, str) and text.strip():
        if len(text) > cfg["MAX_TEXT_CHARS"]:
            return _error("That list is too long. Keep it under 10,000 characters.", 400, "TEXT_TOO_LONG", rid)
        ingredients, precautionary = engine.split_label(text)
        ingredients = ingredients[:150]
        extracted = {"language": None, "nutrition": None}
        source = "text"
    else:
        return _error("Send a label photo or an ingredients list.", 400, "EMPTY_INPUT", rid)

    if not ingredients:
        return _error("No ingredients found. Try a sharper photo or type them in.", 422, "UNREADABLE_LABEL", rid)

    result = engine.analyze(ingredients, diet, allergies, precautionary)
    provider_name = str(cfg.get("VISION_PROVIDER", "mock") or "").strip().lower()
    unresolved = [item["ingredient"] for item in result["items"]
                  if item["status"] in {"unknown", "doubtful"}]
    if provider_name == "gemini" and unresolved:
        try:
            checker = provider or vision.get_provider(cfg)
            estimates = checker.assess_diet(unresolved[:MAX_AI_DIET_ITEMS], diet)
            applied = engine.apply_ai_assessments(result, estimates)
            result["ai_sources"] = getattr(estimates, "sources", [])
            result["ai_grounded"] = bool(result["ai_sources"])
            still_unresolved = any(item["status"] in {"unknown", "doubtful"} for item in result["items"])
            result["ai_assisted"] = applied > 0
            result["ai_check_warning"] = still_unresolved
            log.info("diet_assessment rid=%s requested=%d applied=%d unresolved=%s",
                     rid, len(unresolved), applied, still_unresolved)
        except vision.VisionError as exc:
            # Preserve the transparent rule result if Gemini is unavailable.
            result["ai_assisted"] = False
            result["ai_check_warning"] = True
            result["ai_sources"] = []
            result["ai_grounded"] = False
            log.info("diet_assessment_unavailable rid=%s code=%s", rid, exc.code)
    result["nutrition"] = extracted.get("nutrition")
    result["language"] = extracted.get("language")
    result["source"] = source
    result["demo_mode"] = source == "image" and provider_name == "mock"
    result["request_id"] = rid
    log.info("analyze ok rid=%s source=%s verdict=%s ms=%d", rid, source, result["verdict"],
             (time.monotonic() - started) * 1000)
    return jsonify(result)
