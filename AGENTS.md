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

## Claude ↔ Codex collaboration protocol (token-saving)
Claude plans, reviews and integrates; Codex does the heavy reading, implementation and test runs.
1. **Task in, report out.** The current task is always `CODEX_TASK.md`. When you finish, write
   `CODEX_REPORT.md` (max 40 lines, overwrite each time) with exactly these sections:
   `Status` (done / partial / blocked), `Files changed` (path + one line each),
   `Commands run` (command → one-line result, with the numbers), `Decisions` (any judgment
   call or deviation from the task, one line each), `Open issues`.
   Do not paste code or diffs into the report; Claude reads the diff itself.
2. **Stay in scope.** Edit only the files the task lists. If something outside scope is broken,
   record it under `Open issues` instead of fixing it.
3. **Do not commit, push, or change git config.** Claude reviews `git diff` and commits.
4. **Verify before reporting.** Run every command in the task's `Verification commands`;
   report failures honestly rather than weakening tests.
5. **Keep diffs small.** Prefer editing data (`style_knowledge/*.json`) over code; no
   reformatting of untouched lines; no new dependencies.
6. **Temporary files.** Use pytest's default temp location; delete any scratch folders you
   create (e.g. `.pytest-stylematch-*`) before reporting.
