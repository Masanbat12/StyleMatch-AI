# CODEX_TASK — Calibrate scoring v2 against expert-labelled outfits

Read `AGENTS.md` first (especially the collaboration protocol). Finish by writing `CODEX_REPORT.md`.

## Goal
Scoring v2 is formally correct but miscalibrated against real styling. Example: for
`medium / neutral / casual / daily`, white shirt + navy pants + brown shoes, a textbook classic,
scores 68 ("Needs refining") because the footwear and emphasis rules call brown shoes
"dominant" and the top/bottom value-contrast rule calls white/navy "too high". Calibrate the
rules so the score agrees with professional judgment, and make every reason concrete.

## Relevant files
- `tests/golden_outfits.json` — NEW: expert-labelled calibration set (see below).
- `tests/test_scoring_calibration.py` — NEW: asserts the golden set.
- `scripts/score_check.py` — NEW: prints a compact calibration summary (see Verification).
- `style_knowledge/scoring_rules.json`, `style_knowledge/seasonal_palettes.json`,
  `style_knowledge/color_metadata.json` — tune here first (prefer data over code).
- `recommendation_engine.py` — only where a rule cannot be expressed as data.
- `tests/test_recommendation_engine.py` — update only if an existing assertion encodes the
  miscalibration; say which in `Decisions`.

## Golden set
`tests/golden_outfits.json` = list of
`{"profile": [skin_tone, undertone, style, occasion], "outfit": [top, bottom, shoes], "dress": false, "band": [min, max], "why": "one line"}`.
Include these anchors exactly, then add at least 22 more of your own (at least 30 total),
covering every skin tone group (fair, medium, dark), all 3 undertones, all 4 occasions, and
3 or more dress cases. Every `why` must name the professional principle.

| profile | outfit (top, bottom, shoes) | band | why |
|---|---|---|---|
| medium, neutral, casual, daily | white, navy, brown | 80–92 | classic neutral base; brown leather is a neutral shoe |
| medium, neutral, elegant, work | white, charcoal, black | 82–95 | business-casual staple |
| tan, warm, casual, daily | cream, olive, camel | 82–95 | warm analogous neutrals for warm undertone |
| fair, cool, elegant, evening | navy, charcoal, black | 80–93 | dark, low-chroma evening base for cool colouring |
| dark, warm, elegant, date | rust, cream, brown | 82–95 | warm earth palette with good contrast for deep skin |
| fair, cool, casual, daily | icy blue, gray, white | 78–92 | soft cool palette suits light cool colouring |
| medium, warm, elegant, evening | mustard, red, cobalt | 35–60 | three loud brights, wrong formality for evening |
| fair, cool, elegant, work | mustard, rust, red | 30–55 | warm saturated colours against cool fair colouring; too loud for work |
| dark, cool, minimal, work | soft pink, mustard, green | 35–60 | clashing hues, no neutral anchor, off-code for minimal work |
| medium, neutral, casual, daily | red, red, red | 30–55 | head-to-toe saturated red reads costume-like for daily |
| light, warm, elegant, evening | black, black, black (dress) | 72–88 | all-black evening dress is formal and safe |
| tan, warm, casual, date | olive, cream, white (dress) | 74–90 | warm muted dress with clean neutral shoes |

## Calibration principles (encode as data where possible)
- Neutral leather shoe colours (black, brown, camel, taupe, white, beige, gray, navy, charcoal)
  are neutrals for footwear and emphasis. They must never count as "dominant" or "most saturated".
- Value contrast is judged against a band chosen by occasion and style (evening/elegant/work
  tolerate higher top/bottom contrast; casual/daily tolerates high contrast with a neutral base).
  White over navy or charcoal is in band for every occasion.
- Monochrome neutrals are fine; monochrome saturated colours are penalised.
- More than one saturated hue without a neutral anchor is penalised; evening and work penalise it more.
- Reasons are concrete and name the garment and colour, e.g. "White top is much lighter than
  medium skin: crisp, high-contrast focus", not "above the estimated range". One fact each,
  at most 110 characters.

## Constraints
- Keep all public signatures and return shapes, including `score_report()`, and keep
  `score_breakdown` / `score_dress` totals equal to `score_report()["score"]`.
- Deterministic; no network; no new dependencies.
- Do NOT edit `app.py`, `ui_components.py`, `style_assistant.py`, `llm_client.py`, `AGENTS.md`,
  `CODEX_TASK.md`, `.gitignore`, or anything under `.streamlit/`.
- Do not commit. Delete the scratch folders `.pytest-stylematch-*` that your last run left in the
  project root (they have sandbox-only permissions).

## Verification commands
```
.venv-run/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv-run/Scripts/python.exe scripts/score_check.py
```
`scripts/score_check.py` prints at most 12 lines:
- golden set: `passed X/N`, followed by one line per failure (`profile | outfit | got S, band [a,b]`);
- distribution for `medium/neutral/casual/daily` over all colour triples: min, max, % at 100, % ≥ 90;
- top-5 generated scores for the four profiles used in the tests.

## Done when
- Golden set: at least 90% of cases in band, and every one of the 12 anchors above in band.
- Distribution for `medium/neutral/casual/daily`: at most 0.5% at 100 and at most 10% ≥ 90.
- Top generated looks still score ≥ 85 for those four profiles.
- No reason string contains "estimated range"; all reasons are ≤ 110 characters.
- All tests pass and `CODEX_REPORT.md` follows the protocol.
