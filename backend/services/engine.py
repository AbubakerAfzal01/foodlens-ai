"""Rule engine and conservative merger for AI estimates on unresolved items."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "ingredients.json").read_text())
DIETS = ("halal", "vegetarian", "vegan", "hindu", "kosher")
ECODE = re.compile(r"\be\s?-?(\d{3,4}[a-i]?)\b", re.I)


def allergen_names():
    return sorted(DATA["allergens"])


PRECAUTION = re.compile(
    r"\b(may contain|might contain|can contain|traces? of"
    r"|(?:produced|processed|manufactured|made|packed) (?:in|on) (?:a |an |the )?(?:shared )?"
    r"(?:facility|factory|plant|equipment|line)|shared (?:facility|equipment|line))\b", re.I)


def split_ingredients(text):
    parts = re.split(r"[,;\n]", re.sub(r"^\s*ingredients\s*:?", "", text, flags=re.I))
    return [p.strip(" .") for p in parts if p.strip(" .")]


def split_label(text):
    """Typed label text -> (ingredients, precautionary statements).

    'May contain ...' sentences are kept apart so they are never mistaken for
    ingredients that are intentionally in the product.
    """
    text = re.sub(r"^\s*ingredients\s*:?", "", text, flags=re.I)
    precautions = []
    while True:
        m = PRECAUTION.search(text)
        if not m:
            break
        start = max(text.rfind(c, 0, m.start()) for c in ".,;\n") + 1
        tail = re.search(r"[.\n]", text[m.end():])
        stop = m.end() + tail.start() if tail else len(text)
        precautions.append(text[start:stop].strip(" .,;"))
        text = text[:start] + " " + text[stop + 1:]
    return split_ingredients(text), precautions


def _clean(name):
    name = re.sub(r"\(\s*\d+(\.\d+)?\s*%\s*\)|\d+(\.\d+)?\s*%", "", name.lower())
    return re.sub(r"\s+", " ", name).strip()


def _match(name):
    cleaned = _clean(name)
    codes = {f"e{c.lower()}" for c in ECODE.findall(cleaned)}
    matches = []
    for entry in DATA["ingredients"]:
        if codes & {c.lower() for c in entry.get("ecodes", [])}:
            return entry
        for alias in entry["names"]:
            if re.search(rf"\b{re.escape(alias)}\b", cleaned):
                matches.append((len(alias), entry))
    return max(matches, key=lambda match: match[0])[1] if matches else None


def _allergens_in(name):
    cleaned = _clean(name)
    return [a for a, words in DATA["allergens"].items()
            if any(re.search(rf"\b{re.escape(w)}\b", cleaned) for w in words)]


def _verdict(items):
    statuses = {item["status"] for item in items}
    if "not_ok" in statuses:
        return "not_ok"
    if "unknown" in statuses or not items:
        return "unknown"
    if "doubtful" in statuses:
        return "doubtful"
    return "ok"


def apply_ai_assessments(result, assessments):
    """Apply medium/high-confidence Gemini estimates to unresolved rule items.

    Explicit rule conflicts remain untouched. AI-estimated items are marked so
    the frontend can distinguish estimates from database rules.
    """
    by_name = {
        re.sub(r"\s+", " ", item.get("ingredient", "")).strip().casefold(): item
        for item in assessments
    }
    applied = 0
    for item in result["items"]:
        if item["status"] not in {"unknown", "doubtful"}:
            continue
        estimate = by_name.get(re.sub(r"\s+", " ", item["ingredient"]).strip().casefold())
        if not estimate or estimate.get("confidence") not in {"medium", "high"}:
            continue
        status = estimate.get("status")
        if status not in {"ok", "doubtful", "not_ok"}:
            continue
        reason = str(estimate.get("reason", "")).strip()[:400]
        if not reason:
            continue
        confidence = estimate["confidence"]
        item["status"] = status
        item["note"] = f"Gemini estimate ({confidence} confidence): {reason}"
        item["ai_estimated"] = True
        applied += 1

    if applied:
        result["verdict"] = _verdict(result["items"])
        result["unrecognized"] = [item["ingredient"] for item in result["items"]
                                  if item["status"] == "unknown"]
    return applied


def analyze(ingredients, diet, user_allergies=(), precautionary=()):
    items, unknown, found = [], [], set()
    for raw in ingredients:
        entry = _match(raw)
        status, note = "ok", ""
        if entry:
            status = entry.get("status", {}).get(diet, "unknown")
            if status not in {"ok", "doubtful", "not_ok", "unknown"}:
                status = "unknown"
            note = entry.get("note", "") if status != "ok" else ""
            if status == "unknown":
                note = note or (
                    "FoodLens has no rule for this ingredient under the selected profile, "
                    "so its status is unconfirmed. Check product details or certification."
                )
                unknown.append(raw)
        else:
            status = "unknown"
            note = (
                "FoodLens has no rule for this ingredient under the selected profile, "
                "so its status is unconfirmed. Check product details or certification."
            )
            unknown.append(raw)
        found.update(_allergens_in(raw))
        items.append({"ingredient": raw, "status": status, "note": note})

    verdict = _verdict(items)

    mine = {a.lower() for a in user_allergies}
    precaution_items = [{"text": t, "allergens": _allergens_in(t)} for t in precautionary]
    precaution_found = {a for p in precaution_items for a in p["allergens"]}

    return {
        "diet": diet,
        "verdict": verdict,
        "items": items,
        "unrecognized": unknown,
        "allergens": sorted(found),
        "allergy_alerts": sorted(found & mine),
        "precautionary": precaution_items,
        "precautionary_alerts": sorted(precaution_found & mine),
    }
