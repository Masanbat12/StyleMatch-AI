# CODEX_TASK — Professional style knowledge + more precise outfit scoring

Read `AGENTS.md` first.

## Goal
Make the outfit score more accurate and better justified by grounding it in professional
colour-analysis and dress-code knowledge. Today the score saturates: for the profile
`medium / neutral / casual / daily`, 302 of the 10,648 colour combinations score exactly 100 and the
reasons are generic. After this task the score should spread realistically, every point awarded or
deducted should come from a named rule in the knowledge base, and the result should be exposed in a
structured form that an LLM layer can explain.

## Relevant files
- `style_knowledge/*.json` — extend the existing rule files; you may add new JSON files
  (e.g. `seasonal_palettes.json`, `contrast_rules.json`, `dress_codes.json`).
- `knowledge_base.py` — load any new JSON files; add each new professional source to `SOURCES`
  (title, url, one-line summary). Only cite real, publicly reachable pages.
- `recommendation_engine.py` — scoring logic (`score_breakdown`, `score_dress`,
  `generate_outfit_suggestions`, `generate_dress_suggestions`).
- `catalog.py` — read-only unless a new colour is strictly needed (if so, also add it to
  `style_knowledge/color_metadata.json` and `ui_components`-independent maps only).
- `tests/test_recommendation_engine.py` — extend.

## Professional knowledge to encode (as data in JSON, not hard-coded in Python)
1. **Value contrast** — skin depth (fair → dark) vs garment lightness; high/medium/low contrast
   people and which garment contrast flatters each. Contrast between top and bottom.
2. **Chroma / saturation** — clear vs muted colouring; muted skin tones suit softened colours,
   high-contrast colouring tolerates saturated colours.
3. **Temperature / undertone** — warm, cool, neutral; how far each colour may stray.
4. **Seasonal colour analysis** — the 12-season model (e.g. True/Light/Deep Spring, Summer, Autumn,
   Winter) mapped from (skin tone, undertone) to a best-colours list and an avoid list.
5. **Colour harmony** — monochrome, analogous, complementary, neutral-anchored; the 60-30-10
   proportion idea (top ≈ dominant, bottom ≈ secondary, shoes ≈ accent).
6. **Occasion dress codes / formality** — daily, work (business casual), date, evening
   (smart / cocktail): allowed colour formality, how dark/neutral the base should be, shoe rules.
7. **Footwear rules** — shoes should match or anchor to the bottom or be a neutral; avoid shoes
   that are the loudest item unless the style is street.

## Constraints
- Keep the public signatures and return shapes of `score_breakdown(...) -> (int, list[str])`,
  `calculate_outfit_score`, `score_dress`, `generate_outfit_suggestions`,
  `generate_dress_suggestions`, `get_recommended_colors`, `get_avoid_colors` (callers: `app.py`,
  `style_assistant.py`).
- ADD a new function in `recommendation_engine.py`:
  `score_report(skin_tone, undertone, style, occasion, shirt_color, pants_color, shoes_color, dress=False) -> dict`
  returning
  `{"score": int, "label": str, "season": str, "components": [{"id": str, "name": str, "points": float, "max": float, "reason": str}], "strengths": [str], "risks": [str], "rule_ids": [str]}`.
  `score_breakdown` / `score_dress` must return the same total as `score_report`.
- Deterministic: no randomness, no network, no new dependencies.
- Do NOT edit `app.py`, `ui_components.py`, `style_assistant.py`, `llm_client.py`, or anything under
  `.streamlit/` — Claude is editing those in parallel.
- Reasons stay short, plain English, one fact each.
- Never print or read `.streamlit/secrets.toml`.

## Verification commands
```
.venv-run/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv-run/Scripts/python.exe -c "import itertools;from catalog import ALL_COLORS;from recommendation_engine import score_breakdown as s;v=[s('medium','neutral','casual','daily',*c)[0] for c in itertools.product(ALL_COLORS,repeat=3)];print(min(v),max(v),v.count(100),round(sum(x>=90 for x in v)/len(v)*100,1))"
```

## Done when
- All tests pass, including new tests for: `score_report` shape and total consistency; value-contrast
  rule (e.g. a fair/cool profile scores a black-white-black outfit differently from a deep/warm
  profile); dress-code rule (an evening look in loud brights scores below a dark neutral base);
  season mapping for at least 4 profiles.
- For `medium/neutral/casual/daily`: at most 0.5% of combinations score 100 and at most 10% score ≥ 90,
  while the best suggestions from `generate_outfit_suggestions` still score ≥ 85.
- Every component in `score_report` has a `rule_id` that exists in the JSON knowledge files.
- `SOURCES` lists each professional source used.
