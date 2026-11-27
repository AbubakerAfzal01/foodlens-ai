# FoodLens AI

Scan a food label (any language), then check it against your diet, beliefs and allergies.
Built for the **Global AI Builder's Challenge** (Devpost).

> Scan • Analyze • Stay Informed

## How it works
1. The user uploads a label photo or types ingredients, and picks a profile (Halal, Vegetarian, Vegan, Hindu-friendly (no beef), or Kosher) and allergies.
2. Google Gemini **reads** the label and returns structured ingredients (plus nutrition if printed and any "may contain" warnings).
3. A transparent **rule engine** (`backend/data/ingredients.json`) handles known ingredients. Gemini uses Google Search grounding to give a clearly labelled screening estimate for unresolved `Unknown`/`Check` items and returns source links; explicit rule conflicts remain authoritative. These estimates are not product certification or religious rulings.

## Quick start
```bash
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python run.py               # open http://localhost:5000
```
For actual photo scans, add your `GEMINI_API_KEY` to `.env`. The template defaults to Gemini. To run an offline demo without a key, set `VISION_PROVIDER=mock`; mock mode returns a fixed sample result and does not read the photo. Typed ingredients use the rules first and call Gemini only when an item is unknown or marked `Check`.

The `Hindu-friendly (no beef)` option only checks for explicitly named beef ingredients. It is a narrow screening preference, not a statement about Hindu practice generally. All profiles are ingredient checks, not religious certifications or rulings; see [the rule notes](docs/DIET_RULES.md).

## Project structure
```
backend/
  __init__.py        app factory
  config.py          settings from .env
  routes.py          /api/health, /api/diets, /api/analyze
  services/
    vision.py        label photo -> ingredients (mock + Gemini providers)
    ratelimit.py      per-IP request limit
    engine.py        ingredients + diet -> verdict
  data/ingredients.json   ingredient screening rules and allergen keywords
  data/products.json      200 product identity entries (reference only; most package details are unverified)
frontend/            index.html, css/styles.css, js/app.js (no build step)
tests/               pytest (run: python -m pytest)
docs/                architecture and roadmap
```

## API
`GET /api/mode` reports whether photo scanning is configured or the app is in demo mode. `POST /api/analyze` (multipart or JSON): `image` or `ingredients`, `diet`, `allergies[]`
Returns: `verdict` (ok | doubtful | not_ok | unknown), `items[]` (status, note, optional `ai_estimated`), `allergens`, `allergy_alerts`, `precautionary[]`, `precautionary_alerts`, `nutrition`, `unrecognized`, `ai_assisted`, `ai_check_warning`, `ai_grounded`, `ai_sources[]`, `request_id`.
Errors: `{error, code, request_id}` with 400/413/415/422/429/502/503/504.
Limits: JPG/PNG/WebP up to 4 MB (checked by file signature), 10,000 characters of text, 10 requests/min/IP. The browser shrinks photos to 1600 px before upload.

## Testing
```bash
python -m pytest
```
More: `docs/AI_USAGE.md` (what has actually been checked), `docs/ARCHITECTURE.md`, and [diet rule notes](docs/DIET_RULES.md). The optional label evaluation script needs actual image files in `tests/labels`.

Current check status: 43 automated tests pass after final submission-hardening changes. Live Gemini fallback estimates were verified for Vitamin D3 and an unmapped `Dog` query. A macaroni photo returned long combined ingredient entries; the app now rejects those instead of returning an unsafe `OK`. The post-fix photo flow still needs a successful live recheck; see [the scan log](docs/TEST_TABLE.md).

## Limitations and failure handling
- Photo reading can miss or misread text; the result card shows what was read so you can compare with the package.
- Ingredients not in `ingredients.json` are shown as "Unknown", never "OK". "No match" never means allergen-free or certified.
- Bad file, oversize photo, rate limit, AI timeout, quota, or malformed AI output each return a clear message with a request ID, never a stack trace or key.
- Free-tier Gemini has low rate limits; the app shows "AI service is busy" if hit.
- Grounded diet checks use Google Search through the Gemini API and are subject to its current quota and pricing.

## Disclaimer
FoodLens AI gives guidance, not religious or medical rulings. Always check official certification and consult a qualified person for allergies.
