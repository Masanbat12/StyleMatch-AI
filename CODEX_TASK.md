# CODEX_TASK — Make style and occasion change the ranking

Read `AGENTS.md` first (collaboration protocol). Finish by overwriting `CODEX_REPORT.md`.

## Goal
Calibration works (golden set 35/35), but style and occasion barely affect results. For skin tone
`medium` and undertone `neutral`, `generate_outfit_suggestions(limit=3)` returns the **identical**
top 3 for `casual/daily` and `elegant/work` (gray-gray-beige 96, soft pink-gray-black 96,
icy blue-gray-brown 95). Style has no scoring component, and `dress_code` is only 10 of 100 points.
Make style and occasion matter, so a stylist would agree with each profile's top looks.

## Relevant files
- `style_knowledge/style_rules.json`, `style_knowledge/occasion_rules.json`,
  `style_knowledge/scoring_rules.json`: encode the rules as data first.
- `recommendation_engine.py`: add a style-fit component and strengthen occasion fit.
- `tests/golden_outfits.json`, `tests/test_scoring_calibration.py`, `scripts/score_check.py`.

## What to encode
- **Style fit (new component, `rule_id` in JSON):**
  - casual: relaxed, mid-value neutrals and soft colours; one colour accent welcome.
  - elegant: dark or deep bases (navy, charcoal, black, burgundy, camel), low chroma, refined contrast.
  - street: one bold saturated accent over black, white, gray or denim-blue; white or black shoes.
  - minimal: two or three neutrals, tonal or monochrome, no saturated accent.
- **Occasion fit (stronger):**
  - work: business-casual base of navy, charcoal, gray, white, beige or camel; at most one soft accent; leather-neutral shoes.
  - date: one flattering colour near the face; balanced contrast.
  - evening: dark base, deeper colours, black or brown shoes.
  - daily: anything wearable; light penalty for head-to-toe saturated colour.
- Keep the total spread healthy: the new component must not push scores back toward 100.

## Done when
- For skin tone `medium` and undertone `neutral`, the top-3 sets differ meaningfully between
  `casual/daily`, `elegant/work`, `street/date`, `minimal/work` and `elegant/evening`: at most one look
  shared between any two profiles. Assert this in a test.
- Every top-3 look for `elegant/work` has a bottom in {navy, charcoal, gray, black, beige, camel}
  and no saturated accent; every top-3 look for `street/*` has exactly one saturated colour.
- Golden set still at least 90% in band, and all 12 original anchors still in band. Add at least
  8 new style- or occasion-focused cases.
- Distribution for `medium/neutral/casual/daily`: at most 0.5% at 100 and at most 10% at or above 90.
  Top looks at or above 85 for the four profiles in `score_check.py`.
- `scripts/score_check.py` additionally prints the top-3 looks for the five profiles above, one
  line each, and stays ASCII-only (the Windows console is cp1255).
- All tests pass.

## Constraints
- Keep every public signature and return shape, including `score_report()` and total equality.
- Deterministic; no network; no new dependencies.
- Do NOT edit `app.py`, `ui_components.py`, `assets/`, `style_assistant.py`, `llm_client.py`,
  `AGENTS.md`, `CODEX_TASK.md`, `.gitignore`, or `.streamlit/`.
- Do not commit. Skip the `.pytest-stylematch-*` folders (they are git-ignored, and nobody has permission to delete them).

## Verification commands
```
.venv-run/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv-run/Scripts/python.exe scripts/score_check.py
```
