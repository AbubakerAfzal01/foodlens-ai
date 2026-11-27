# Architecture

Browser (frontend/) -> Flask API (backend/routes.py) -> Gemini vision (reads photo) -> rule engine (known items) -> Gemini with Google Search grounding (only unresolved items, with source links).

- **Why separate vision and rules?** Gemini reads labels and can estimate statuses for items the rules leave `Unknown` or `Check`. The rule engine handles known items and keeps explicit conflicts; AI estimates are marked in results.
- **Providers:** `vision.py` has a `MockProvider` (offline demo) and `GeminiProvider`. The Gemini provider supports photo extraction and batched, search-grounded diet estimates for unresolved items.
- **Statuses:** `ok`, `doubtful` (source or processing details are unclear), `not_ok`, and `unknown` when any ingredient is unrecognised or has no rule for the selected profile.
- **Limits:** 4 MB uploads (Vercel's request limit is about 4.5 MB), JPG/PNG/WebP only. No data is stored.
- **Extending the rules:** add an entry to `backend/data/ingredients.json` (names, optional ecodes, status per diet, note) and a test in `tests/test_engine.py`.

- **Safety rules:** an ingredient missing from the rules is sent to Gemini when configured; low-confidence or unavailable assessments remain `unknown`. Explicit rule conflicts are not overridden. "May contain" statements are kept apart from ingredients. No match never means allergen-free.
- **Deploy:** `api/index.py` and `vercel.json` are an untested starting point for Vercel. The in-memory rate limiter is per instance there, so also set a spending cap on the Gemini key.
