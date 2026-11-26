# AGENTS.md — StyleMatch AI

## Purpose
Streamlit app for tone-aware outfit exploration: skin-tone/undertone estimation from an uploaded photo,
rule-based outfit scoring from local JSON knowledge, layered PNG avatar previews, saved looks
(local SQLite, optional Supabase sync + auth).

## Stack
Python 3.13, Streamlit (1.5x — uses `width="stretch"`), Pillow, OpenCV (headless), NumPy, supabase-py, pytest.

## Layout
- `app.py` — page flow: sidebar (access, avatar, complexion, wardrobe direction) + 6 tabs
  (Image Analyzer, Outfit Builder, Generate 5 Looks, AI Style Assistant, Saved Looks, Sources).
- `ui_components.py` — theme (`inject_theme`, one big injected `<style>` block with `--sm-*` tokens),
  branded HTML blocks (header, profile band, chips, score badge, colour legends, pickers).
- `recommendation_engine.py`, `image_analysis.py`, `avatar_renderer.py`, `avatar_materials.py`,
  `style_assistant.py`, `database.py`, `session_manager.py`, `supabase_*.py`, `catalog.py`,
  `knowledge_base.py`, `models.py`.
- `style_knowledge/*.json` — rules. `avatar_assets/`, `assets/` — images. `tests/` — pytest.

## Commands
- Run: `.venv-run/Scripts/python.exe -m streamlit run app.py`
- Test: `.venv-run/Scripts/python.exe -m pytest -q -p no:cacheprovider`

## Conventions / constraints
- Visual identity: warm ivory background, dark espresso sidebar, gold accent (`--sm-gold`). No violet.
- Widget state that must change from a button goes through `on_click` callbacks (never assign a
  widget's session_state key after the widget is created in the same run).
- Never commit or print `.streamlit/secrets.toml`.
- Motion: subtle and purposeful; respect `prefers-reduced-motion`.
