# StyleMatch AI

StyleMatch AI is a Streamlit application for tone-aware outfit exploration. It combines image-based complexion estimation, a structured local style knowledge base, rule-driven outfit recommendations, and an avatar preview workflow in one polished interface.

<img width="350" height="150" alt="logo" src="https://github.com/user-attachments/assets/53defc2c-f900-45da-80f9-531bf7ebd2a6" />
<img width="1762" height="509" alt="image" src="https://github.com/user-attachments/assets/279cde1c-a6d2-40bc-bbf6-861f864c63c4" />

## What the app does

- analyzes an uploaded portrait to estimate skin tone and undertone
- surfaces reliability warnings when lighting or sampling quality is weak
- recommends color palettes grounded in local style knowledge files
- scores manual outfits against undertone, contrast, style, and occasion rules
- generates five distinct outfit directions with short explanations
- renders a layered avatar preview for manual looks and generated suggestions
- saves selected looks locally in SQLite

## Product principles

- Honest UX: low-confidence image reads are shown as best estimates, not facts
- Structured reasoning: recommendations use explicit local rules instead of vague text
- Maintainable code: domain rules, image analysis, rendering, and UI helpers are separated
- Portfolio realism: the README and code make realistic claims and document limitations

## Architecture

```text
stylematch_ai_v2/
├── app.py                   # Streamlit orchestration and page flow
├── ui_components.py         # Theme, layout helpers, branded UI primitives
├── image_analysis.py        # Portrait loading, skin sampling, quality checks, confidence scoring
├── recommendation_engine.py # Color ranking, harmony logic, scoring, generated looks
├── style_assistant.py       # Grounded assistant responses built from project knowledge
├── knowledge_base.py        # Loads local JSON rule files
├── style_knowledge/         # Color theory, undertone, style, occasion, explanation data
├── avatar_renderer.py       # Layered avatar rendering and garment placement
├── database.py              # Local SQLite persistence
├── models.py                # Core validation dataclasses
├── catalog.py               # Shared color, tone, and option catalogs
├── assets/                  # Brand assets
├── avatar_assets/           # Base avatar and clothing overlays
└── tests/                   # Focused regression tests
```

## Key modules

### `image_analysis.py`

Implements a multi-stage heuristic pipeline:

1. load and validate the upload
2. attempt a face-focused crop using OpenCV Haar cascades
3. build a combined skin mask in YCrCb and HSV space
4. sample stable zones such as forehead and cheeks when possible
5. reject highlight-heavy and shadow-heavy pixels
6. estimate dominant skin color, skin tone, and undertone
7. compute reliability signals for flash, low light, contrast, color cast, and unstable sampling

This is still heuristic image analysis, not a clinical or biometric system. The app exposes warnings and confidence instead of pretending otherwise.

### `recommendation_engine.py`

Uses a structured local knowledge base to score outfits against:

- undertone compatibility
- style and occasion preferences
- contrast against the estimated skin tone
- color harmony patterns such as analogous, complementary, and monochromatic relationships
- shoe neutrality and versatility

Generated looks are filtered to stay meaningfully distinct from one another.

### `avatar_renderer.py`

Builds a dressed avatar from a base body plus transparent clothing overlays. Each overlay is cropped to visible alpha content before placement so asset tuning remains maintainable.

## Setup

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux / macOS / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

## Run tests

```bash
pytest -q
```

## Local knowledge base

The recommendation system is grounded in local JSON files under `style_knowledge/`.

- `color_theory_rules.json`
- `undertone_rules.json`
- `style_rules.json`
- `occasion_rules.json`
- `color_metadata.json`
- `explanation_templates.json`

This makes the behavior transparent, editable, and safe to extend without retraining or hidden dependencies.

## Repository strengths

- recruiter-friendly separation between UI, domain rules, rendering, and persistence
- explicit quality/confidence signals in the image-analysis flow
- local rule files that make recommendation behavior inspectable
- focused tests for recommendations, persistence, rendering, and image-analysis outputs
- premium but restrained Streamlit UI with custom styling

## Known limitations

- skin tone and undertone estimation remain heuristic and lighting-sensitive
- face detection uses a lightweight classical OpenCV detector rather than a dedicated face parsing model
- avatar realism depends on the quality of the supplied clothing overlay assets
- recommendation logic is rule-based, so it is explainable but not trend-aware or personalized over time
