import io
import json
from types import SimpleNamespace

import pytest

from backend import create_app, ratelimit
from backend.services import vision

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


@pytest.fixture()
def client():
    ratelimit.reset()
    return create_app({"TESTING": True, "VISION_PROVIDER": "mock", "RATE_LIMIT_PER_MIN": 100}).test_client()


def img(data=JPEG, name="label.jpg", ctype="image/jpeg"):
    return (io.BytesIO(data), name, ctype)


def test_health_hides_internals(client):
    assert client.get("/api/health").json == {"status": "ok"}


def test_analyze_text(client):
    r = client.post("/api/analyze", json={"ingredients": "lard, salt", "diet": "halal"})
    assert r.status_code == 200 and r.json["verdict"] == "not_ok" and r.json["request_id"]


def test_analyze_image_mock(client):
    r = client.post("/api/analyze", data={"image": img(), "diet": "vegan", "allergies": ["milk"]},
                    content_type="multipart/form-data")
    assert r.status_code == 200 and r.json["nutrition"] and "milk" in r.json["allergy_alerts"]
    assert r.json["demo_mode"] is True and r.json["source"] == "image"
    assert r.json["precautionary"][0]["allergens"] == ["peanuts"]


@pytest.mark.parametrize("extracted", [
    {"legible": False, "ingredients": [], "precautionary": []},
    {"legible": True, "ingredients": [], "precautionary": []},
])
def test_photo_without_ingredient_list_is_rejected(client, monkeypatch, extracted):
    class Provider:
        def extract(self, *_):
            return extracted

    monkeypatch.setattr(vision, "get_provider", lambda _config: Provider())
    r = client.post("/api/analyze", data={"image": img(), "diet": "halal"},
                    content_type="multipart/form-data")
    assert r.status_code == 422
    assert r.json["code"] == "UNREADABLE_LABEL"
    assert "verdict" not in r.json


def test_rejects_bad_input(client):
    assert client.post("/api/analyze", json={}).status_code == 400
    assert client.post("/api/analyze", json={"ingredients": "x", "diet": "nope"}).status_code == 400
    assert client.post("/api/analyze", json={"ingredients": "x", "diet": "christian"}).status_code == 400
    assert client.post("/api/analyze", json={"ingredients": "x", "allergies": ["cheese"]}).status_code == 400
    assert client.post("/api/analyze", json={"ingredients": "x", "allergies": "milk"}).status_code == 400


def test_diet_list_matches_supported_profiles(client):
    diets = client.get("/api/diets").json["diets"]
    assert diets == ["halal", "vegetarian", "vegan", "hindu", "kosher"]


def test_fake_image_is_rejected_by_signature(client):
    r = client.post("/api/analyze", data={"image": img(b"<script>alert(1)</script>"), "diet": "halal"},
                    content_type="multipart/form-data")
    assert r.status_code == 415 and r.json["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_empty_and_oversized_image(client):
    r = client.post("/api/analyze", data={"image": img(b""), "diet": "halal"}, content_type="multipart/form-data")
    assert r.status_code == 400
    app = create_app({"TESTING": True, "VISION_PROVIDER": "mock", "MAX_IMAGE_BYTES": 100,
                      "MAX_CONTENT_LENGTH": 10_000, "RATE_LIMIT_PER_MIN": 100})
    r = app.test_client().post("/api/analyze", data={"image": img(JPEG + b"0" * 200), "diet": "halal"},
                               content_type="multipart/form-data")
    assert r.status_code == 413 and r.json["code"] == "FILE_TOO_LARGE"


def test_text_too_long(client):
    r = client.post("/api/analyze", json={"ingredients": "a, " * 6000})
    assert r.status_code == 400 and r.json["code"] == "TEXT_TOO_LONG"


def test_rate_limit():
    ratelimit.reset()
    c = create_app({"TESTING": True, "RATE_LIMIT_PER_MIN": 2}).test_client()
    codes = [c.post("/api/analyze", json={"ingredients": "salt"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_missing_gemini_key_is_safe_error():
    ratelimit.reset()
    c = create_app({"TESTING": True, "VISION_PROVIDER": "gemini", "GEMINI_API_KEY": ""}).test_client()
    r = c.post("/api/analyze", data={"image": img(), "diet": "halal"}, content_type="multipart/form-data")
    assert r.status_code == 503 and "key" not in r.json["error"].lower()


def test_unknown_route_is_json(client):
    assert client.get("/api/nope").json["code"] == "NOT_FOUND"


# ---- Gemini provider with a fake SDK client (no network) ----
def gemini_with(fake_generate):
    p = vision.GeminiProvider.__new__(vision.GeminiProvider)
    from google.genai import types
    p._types, p.model = types, "test-model"
    p.client = SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate))
    return p


def test_gemini_parses_and_cleans_output():
    payload = {"legible": True, "ingredients": [" Sugar ", "", "E471"], "precautionary": ["May contain milk"],
               "language": "English", "nutrition": {"basis": "per 12 g serving", "serving_size_g": 12,
                                                       "calories": 60, "fat_g": -5, "carbs_g": 5,
                                                       "fiber_g": 4, "sodium_mg": 0}}
    p = gemini_with(lambda **k: SimpleNamespace(text=json.dumps(payload)))
    out = p.extract(JPEG, "image/jpeg")
    assert out["ingredients"] == ["Sugar", "E471"] and out["nutrition"]["fat_g"] is None
    assert out["nutrition"]["basis"] == "per serving" and out["nutrition"]["serving_size_g"] == 12
    assert out["nutrition"]["carbs_g"] == 5 and out["nutrition"]["fiber_g"] == 4
    assert out["nutrition"]["sodium_mg"] == 0 and out["nutrition"]["salt_g"] is None


def test_gemini_rejects_a_combined_overlong_ingredient_entry():
    payload = {"legible": True, "ingredients": ["Ingredients: " + ("wheat flour, cheese, milk, " * 12)]}
    out = gemini_with(lambda **k: SimpleNamespace(text=json.dumps(payload))).extract(JPEG, "image/jpeg")
    assert out["legible"] is False


def test_gemini_structures_diet_estimates_for_unknown_items():
    payload = {"items": [{"ingredient": "dog", "status": "not_ok", "confidence": "high",
                           "reason": "The profile flags this animal source."}]}
    p = gemini_with(lambda **k: SimpleNamespace(text=json.dumps(payload)))
    out = p.assess_diet(["dog"], "halal")
    assert out == [{"ingredient": "dog", "status": "not_ok", "confidence": "high",
                    "reason": "The profile flags this animal source."}]


def test_text_unknown_uses_gemini_and_keeps_estimate_label(monkeypatch):
    ratelimit.reset()

    class Provider:
        def assess_diet(self, ingredients, diet):
            assert ingredients == ["Vitamin D3"] and diet == "halal"
            return [{"ingredient": "Vitamin D3", "status": "doubtful", "confidence": "medium",
                     "reason": "The source is not stated on the label."}]

    monkeypatch.setattr(vision, "get_provider", lambda _config: Provider())
    client = create_app({"TESTING": True, "VISION_PROVIDER": "gemini", "GEMINI_API_KEY": "configured",
                         "RATE_LIMIT_PER_MIN": 100}).test_client()
    response = client.post("/api/analyze", json={"ingredients": "Vitamin D3", "diet": "halal"})
    assert response.status_code == 200
    assert response.json["verdict"] == "doubtful"
    assert response.json["ai_assisted"] is True
    assert response.json["items"][0]["ai_estimated"] is True
    assert "Gemini estimate" in response.json["items"][0]["note"]


def test_gemini_fallback_failure_keeps_rule_result(monkeypatch):
    ratelimit.reset()

    class Provider:
        def assess_diet(self, *_):
            raise vision.VisionError("The AI service is busy right now. Please try again in a minute.",
                                     429, "PROVIDER_QUOTA")

    monkeypatch.setattr(vision, "get_provider", lambda _config: Provider())
    client = create_app({"TESTING": True, "VISION_PROVIDER": "gemini", "GEMINI_API_KEY": "configured",
                         "RATE_LIMIT_PER_MIN": 100}).test_client()
    response = client.post("/api/analyze", json={"ingredients": "Vitamin D3", "diet": "halal"})
    assert response.status_code == 200
    assert response.json["verdict"] == "unknown"
    assert response.json["ai_assisted"] is False
    assert response.json["ai_check_warning"] is True


def test_gemini_invalid_json_blocked():
    p = gemini_with(lambda **k: SimpleNamespace(text="not json {"))
    with pytest.raises(vision.VisionError) as e:
        p.extract(JPEG, "image/jpeg")
    assert e.value.code == "INVALID_MODEL_OUTPUT" and e.value.status == 422


@pytest.mark.parametrize("exc,status,code", [
    (TimeoutError("request timed out"), 504, "AI_TIMEOUT"),
    (type("ConnectError", (Exception,), {})("socket failed because of access permissions"),
     503, "AI_CONNECTION_ERROR"),
    (type("APIError", (Exception,), {"code": 403})("PERMISSION_DENIED"), 503, "AI_UNAVAILABLE"),
    (type("APIError", (Exception,), {"code": 429})("RESOURCE_EXHAUSTED secret-detail"), 429, "PROVIDER_QUOTA"),
    (RuntimeError("boom with secret-detail"), 502, "AI_PROVIDER_ERROR"),
])
def test_gemini_errors_are_mapped_and_not_leaked(exc, status, code):
    def boom(**k):
        raise exc
    with pytest.raises(vision.VisionError) as e:
        gemini_with(boom).extract(JPEG, "image/jpeg")
    assert (e.value.status, e.value.code) == (status, code) and "secret-detail" not in str(e.value)
