# AI use and checks

## AI inside FoodLens

- Google Gemini reads uploaded label photos and returns ingredients, precautionary statements, language, and nutrition when available.
- The rule engine handles known ingredients. Unknown or `Check` ingredients are sent together in a second Gemini request with Google Search grounding; the server validates the response, marks each applied estimate, and displays source links returned by Google.
- Typed lists use local rules first. Only items left `Unknown` or `Check` are sent to Gemini. When a broadly reported majority view exists, Gemini is prompted to state it directly and mention recognized differences. Product-specific unknown sources stay uncertain.
- Explicit local rule conflicts are never overridden. Low-confidence, missing, or failed AI assessments keep the original `Unknown`/`Check` result and show a warning. Web sources do not make an answer an official ruling, certification, or product-specific source check.
- Google Search grounding is enabled only for unresolved diet assessments. It uses the Gemini API's search quota and may have usage charges; check Google's current [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing).
- The prompt treats package text as data, not instructions. Unreadable or incomplete ingredient lists are rejected rather than silently treated as complete.

## AI-assisted development

An AI coding assistant helped review and refine the app. The project owner directs the work and should review the written dietary profile rules before presenting or relying on them.

Changes include unknown results for ingredients without a matching rule, separate handling for "may contain" statements, upload signature and size checks, request limits, safer provider errors, and a result view that renders label text as plain text.

## Checks completed so far

- `python -m pytest -q`: 43 passed after submission-hardening changes, including checks for AI assessment parsing/merging, hard-rule protection, fallback failures, unreadable photos, long combined entries, network-error mapping, and security headers. Python compilation and `node --check frontend/js/app.js` should be rerun in the final environment.
- Live Gemini scans succeeded on chia-seed and milk labels. The milk photo also worked from the desktop browser; it showed per-serving nutrition and left Vitamin D3 as `Unknown` because no source rule exists.
- Live text fallback was verified: Gemini returned a medium-confidence `Check` estimate for Vitamin D3 due to unknown source, and a high-confidence `Not OK` estimate for an unmapped `Dog` query. These are model outputs, not validated religious rulings.
- A live macaroni-label request returned two long combined ingredient entries. The old normalizer truncated them and produced an unsafe `OK`; it now rejects overlong combined entries. The photo flow still needs a successful live retest after this fix.
- Three unique product photos have been tried, but the ten-label evaluation remains incomplete. The images are not copied into `tests/labels`; mobile-browser testing is also still pending.

## Limits

Photo text can be missed or mistranscribed. The ingredient rules are limited and have not been reviewed by a religious certifier or qualified dietitian. Results are guidance, not certification or medical advice. Compare photo results with the package, and check with the manufacturer, certifier, or medical professional when needed.
