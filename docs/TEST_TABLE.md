# Label scan check

Manual checks using the chia-seed package photo supplied by the project owner. The photo itself is not copied into the repository.

| Run | What was checked | Observed result | Status |
|---|---|---|---|
| Initial live scan | Photo reading before adding chia aliases | Gemini read `ORGANIC CHIA SEEDS`; the rule engine returned `Unknown` because chia was not yet in the ingredient rules. | Led to adding chia aliases. |
| Live scan after rule and serving-basis changes | Ingredient result and nutrition printed per serving | Gemini read `ORGANIC CHIA SEEDS`; Vegan result was `OK`; nutrition basis was per serving, size 12 g, with 60 calories, 4 g fat, 0 g sugar, and 2 g protein. | Matched the visible ingredient and serving information. |
| Latest live attempt after adding carbs, fiber, and separate sodium fields | Current expanded nutrition schema | Gemini returned HTTP 504 (`AI_TIMEOUT`). | No live result; retry later. |
| Macaroni-and-cheese label live scan | Small print; Gemini returned two long grouped ingredient entries and nutrition | The earlier code truncated those entries and incorrectly returned `OK`. The normalizer now marks long combined entries unreadable instead. | Unsafe result caught; post-fix live scan still needed. |
| Typed AI fallback: Vitamin D3 (Halal) | Unknown ingredient sent to Gemini | Medium-confidence `Check` estimate; source could not be identified. | Live fallback worked and kept uncertainty visible. |
| Typed AI fallback: Dog (Halal) | Unknown term sent to Gemini | High-confidence `Not OK` AI estimate. | Model output only; not a validated religious ruling. |
| Google Search grounding for diet estimates | Code now requests Search grounding and returns provider source links | Implemented, but the live grounded request has not yet been run. | Needs a live Gemini check. |
| Automated suite | API, rules, parsing, upload checks, mocked Gemini responses, AI fallback merging, non-label rejection, network error mapping, and long-entry rejection | 42 tests passed. | Passed. |

The successful milk-label live scan confirmed the serving basis and nutrition fields. The macaroni scan caught a separate extraction issue, now covered by a rejection rule and test. That post-fix image flow needs another live run. The supplied photos are still far short of the planned ten-label evaluation. No desktop/mobile browser test has been recorded.
