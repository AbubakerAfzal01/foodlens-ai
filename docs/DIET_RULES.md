# Food profile rules

FoodLens compares ingredient words with a small, editable rules file. These profiles are screening shortcuts; they do not certify a product or give religious rulings. `OK` means only that the ingredient name has no conflict in the rules we currently encode. It does not confirm the source, processing, kitchen, or certification of the product.

The imported ingredient dataset adds 500 common label terms and expands allergy matching from 8 to 14 categories. Its metadata records source links, but the project owner still needs to manually review the diet classifications before relying on them.

## What each profile means in this app

- **Halal:** named pork ingredients and named alcoholic drinks are marked `Not OK`. Beef, gelatin, rennet, and ingredients whose source or processing is unclear are marked `Check` where appropriate. A product still needs its own certification and review.
- **Vegetarian:** explicit meat, fish, and animal rennet are marked `Not OK`. Gelatin and source-dependent additives are flagged for checking.
- **Vegan:** explicit dairy, egg, honey, meat, and fish ingredients are marked `Not OK`. Source-dependent additives are flagged for checking.
- **Hindu-friendly (no beef):** this profile only checks for explicitly named beef ingredients, including beef fat, tallow, and beef extract. It does not represent every Hindu person's choices or check every tradition. Generic gelatin, rennet, and other animal-derived ingredients can have an unknown species, so they may be marked `Check`.
- **Kosher:** explicit pork and shellfish ingredients are marked `Not OK`. Beef, some fish, and source-dependent ingredients may need certification or more product information and are marked `Check`.

The rules also have ordinary food ingredient entries such as salt and chia seeds. An ingredient without a rule, or one marked `Check`, is sent to Gemini with Google Search grounding when Gemini is configured. Gemini is prompted to state a broadly reported majority view directly and explain recognized differences; its source links appear in the result. Product-specific source questions remain `Check` when the label does not identify the source. If Gemini is uncertain, unavailable, or returns low confidence, the item remains `Unknown` or `Check`. The overall result stays cautious whenever any ingredient remains unconfirmed, unless a known conflict already makes the result `Not OK`.

## Important limits

- Rules are based on ingredient names and listed E-numbers; they cannot infer an undisclosed source or factory process.
- Gemini's web-grounded estimates use search results, but they are not certification or religious rulings. Search cannot reveal a product-specific source missing from the label.
- A photo may miss or mistranscribe text. Compare the extracted list with the package.
- `May contain` statements are cross-contact warnings, separate from intentionally listed ingredients.
- The rules have not been reviewed by a religious certifier or qualified dietitian. For personal religious decisions, check the relevant certifier or trusted authority. For allergies, use the package and medical guidance.

Update `backend/data/ingredients.json` and add a regression check in `tests/test_engine.py` when adding a rule. Every entry should state a status for every profile so a missing status cannot silently become `OK`.
