# StyleMatch AI

StyleMatch AI is a Streamlit application for tone-aware outfit exploration. It combines image-based complexion estimation, structured local style rules, outfit scoring, generated looks, avatar previews, Supabase account support, and local SQLite fallback storage.

https://stylematch-ai-h9lu.onrender.com/

## What the App Does

- analyzes an uploaded portrait to estimate skin tone and undertone
- surfaces reliability warnings when lighting or sampling quality is weak
- recommends color palettes from local style knowledge files
- scores manual outfits against undertone, contrast, style, and occasion rules
- generates five distinct outfit directions with short explanations
- renders a layered avatar preview for manual looks and generated suggestions
- supports Supabase sign up and login
- keeps nicknames unique through a Supabase `user_profiles` table
- saves authenticated looks to Supabase when configured
- learns from Like / Not for me feedback with lightweight per-user style points
- falls back to local SQLite storage when Supabase storage is unavailable

## Architecture

```text
StyleMatch-AI/
|-- app.py                         # Streamlit page flow and active UI orchestration
|-- ui_components.py               # Theme, layout helpers, branded UI primitives
|-- image_analysis.py              # Portrait loading, skin sampling, quality checks
|-- recommendation_engine.py       # Color ranking, harmony logic, scoring, generated looks
|-- style_assistant.py             # Grounded assistant responses from project knowledge
|-- knowledge_base.py              # Loads local JSON rule files
|-- style_knowledge/               # Color, undertone, style, occasion, explanation data
|-- avatar_renderer.py             # Layered avatar rendering and garment placement
|-- database.py                    # Supabase saved-look and feedback sync with SQLite fallback
|-- supabase_client.py             # Supabase URL/key loading and client creation
|-- supabase_auth_service.py       # Supabase Auth sign up/login flow
|-- supabase_profile_repository.py # Nickname/profile storage in user_profiles
|-- session_manager.py             # Streamlit session state for guest/auth users
|-- models.py                      # Core validation dataclasses
|-- catalog.py                     # Shared color, tone, and option catalogs
|-- supabase_schema.sql            # Required Supabase tables
|-- assets/                        # Brand assets
|-- avatar_assets/                 # Base avatar and clothing overlays
|-- tests/                         # Focused regression tests
```

The active persistence model is Supabase plus local SQLite fallback. The app does not use MongoDB, standalone PostgreSQL, or a custom password database.

## Supabase Setup

Set these secrets in Streamlit locally or as Render environment variables:

```text
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-or-publishable-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

`SUPABASE_URL` must be the base project URL only, not a dashboard URL and not an `/auth/v1` or `/rest/v1` endpoint. `SUPABASE_KEY` is used for Supabase Auth. `SUPABASE_SERVICE_ROLE_KEY` is used server-side for profile and saved-look table access, so keep it out of Git.

Run the SQL in `supabase_schema.sql` in the Supabase SQL editor. The app expects:

- `public.user_profiles` for email and nickname uniqueness
- `public.saved_outfits` for cloud-saved looks
- `public.outfit_feedback` for per-user Like / Not for me learning points

If email confirmation is enabled in Supabase Auth, new users must confirm email before logging in. For local testing, you can disable email confirmation in Supabase Auth settings.

## Local Secrets

For local Streamlit development, copy `streamlit_secrets.example.toml` to `.streamlit/secrets.toml` and fill in real values. `.streamlit/secrets.toml` is ignored and must not be committed.

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

## Run the App

```bash
streamlit run app.py
```

On Linux, macOS, or Render-style shells, this is also valid after dependencies are installed:

```bash
./.venv/bin/python -m streamlit run app.py
```

## Run Tests

```bash
pytest -q
```

## Deployment Notes

- Keep `.streamlit/secrets.toml`, `.venv`, `node_modules`, cache folders, and local DB files out of Git.
- Configure Supabase secrets in Render environment variables.
- Use the base Supabase project URL and the anon/publishable key plus service-role key described above.
- The app still runs without Supabase secrets, but account login and cloud-saved looks are disabled and saved looks remain local.
- Feedback also falls back to local SQLite when Supabase is not configured or temporarily unavailable.

## Known Limitations

- skin tone and undertone estimation are heuristic and lighting-sensitive
- face detection uses a lightweight OpenCV detector rather than a dedicated face parsing model
- avatar realism depends on the supplied clothing overlay assets
- recommendation logic is rule-based and explainable; feedback points personalize color ranking, but the app is not trend-aware
