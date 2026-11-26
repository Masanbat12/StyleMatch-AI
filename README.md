# StyleMatch AI

StyleMatch AI is a Streamlit app that suggests outfit colours for your complexion. Upload a portrait or pick your skin tone, and the app estimates your undertone, places you in one of 12 colour seasons, scores outfits out of 100, and shows each look on a layered avatar.

Live app: https://stylematch-ai-h9lu.onrender.com/

Promo video (30 s, 1080p):


https://github.com/user-attachments/assets/c893ae7d-c3fb-47a1-8d92-d8373932cfc0



## What you can do in the app

The sidebar holds your profile: skin tone, undertone, style (casual, elegant, street, minimal) and occasion (daily, date, work, evening). It also picks the avatar (man or woman) and the garments: shirt, hoodie, jacket or dress on top, pants or skirt below, sneakers or heels. Six tabs sit on the main page:

- Image Analyzer reads a portrait, estimates skin tone and undertone, and warns you when the lighting or the skin sample is too poor to trust.
- Outfit Builder lets you choose colours for each garment. The score and its reasons update as you change them, and the avatar preview follows.
- Generate 5 Looks ranks five distinct outfits for your profile. You can open any of them in the Builder to adjust it.
- AI Style Assistant answers questions in English or Hebrew. It only uses facts the engine produced, so it never makes up a score.
- Saved Looks keeps the outfits you saved, with the avatar and profile they were made for.
- Sources lists the colour-theory references behind the rules.

Each look has Like and Not for me buttons. Reactions move the colours you like up the recommendation list and push the ones you reject down. They change the order of suggestions, and the score itself stays the same.

## How the score works

The engine in `recommendation_engine.py` reads its rules from `style_knowledge/scoring_rules.json` and splits 100 points across ten checks:

| Check | Points (dress) |
| --- | --- |
| Value contrast between face and garment | 14 (17) |
| Value contrast between top and bottom | 7 |
| Chroma against your season | 12 (14) |
| Undertone temperature | 12 |
| Seasonal palette | 13 (15) |
| Colour harmony | 8 |
| Colour emphasis (60/30/10 split) | 5 |
| Style fit | 12 |
| Occasion fit | 12 |
| Footwear | 5 |

`score_report()` returns the total together with every component, its reason, and the rule IDs it used. The Builder, the generated looks and the assistant all read from that one report.

A golden set of 44 hand-scored outfits in `tests/golden_outfits.json` keeps the scores honest. To check calibration:

```bash
python scripts/score_check.py
```

It prints how many golden cases fall in their expected band, the score spread across all colour combinations, and the top three looks for five sample profiles. At the moment all 44 cases pass, no outfit scores 100, and about 7% score 90 or more.

## AI stylist

`llm_client.py` speaks the OpenAI-compatible chat API, so one setting switches the provider. The default is a local Ollama model, which is free and needs no account:

```bash
ollama pull qwen2.5:3b
```

Groq, Gemini and OpenRouter work too, each with a free tier and an API key. Set the provider in `.streamlit/secrets.toml` (see `streamlit_secrets.example.toml`) or with `LLM_*` environment variables. When no model answers, the tab falls back to a rule-based answer built from the same facts.

## Project layout

```text
StyleMatch-AI/
|-- app.py                         # Page flow: sidebar, six tabs, callbacks
|-- ui_components.py               # Theme loader and branded HTML blocks
|-- assets/theme.css               # Colour tokens, type, motion
|-- image_analysis.py              # Portrait loading, skin sampling, quality checks
|-- recommendation_engine.py       # score_report(), suggestions, personalised ranking
|-- style_assistant.py             # Grounded prompts and the rule-based fallback
|-- llm_client.py                  # Ollama / Groq / Gemini / OpenRouter client
|-- avatar_renderer.py             # Layered male and female avatars
|-- avatar_materials.py            # Fabric, denim and shoe shading for recoloured PNGs
|-- database.py                    # Saved looks and Like / Not for me, Supabase or SQLite
|-- supabase_*.py                  # Supabase client, auth and profile storage
|-- supabase_schema.sql            # Tables to create in Supabase
|-- session_manager.py             # Guest and signed-in session state
|-- knowledge_base.py, catalog.py  # Rule loading and shared option lists
|-- style_knowledge/               # JSON rules: palettes, seasons, styles, occasions
|-- avatar_assets/                 # Base avatars and garment overlays
|-- scripts/score_check.py         # Calibration report
|-- promo/                         # Promo video, its renderer and soundtrack
|-- tests/                         # pytest suite (117 tests)
```

## Running it locally

Python 3.13 is the tested version.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

The app runs without any cloud setup. Saved looks and reactions then go to `data/saved_outfits.db`, which Git ignores.

## Supabase (optional)

With Supabase configured, people can sign up, log in, and keep their looks and reactions across devices. Add these secrets to `.streamlit/secrets.toml` locally or to the Render environment:

```text
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-or-publishable-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

Use the base project URL, without `/auth/v1` or `/rest/v1`. The anon key handles sign-in; the service-role key reads and writes the tables on the server, so keep it out of Git.

Run `supabase_schema.sql` in the Supabase SQL editor. It creates `user_profiles` (unique email and nickname), `saved_outfits` and `outfit_feedback`, and adds the `metadata` column that stores the avatar and garment choices of a saved look. If the cloud is unreachable, saves and reactions go to the local SQLite file instead. Guests always stay local, and each guest session only sees its own looks.

If Supabase Auth requires email confirmation, new users have to confirm before they can log in.

## Tests

```bash
python -m pytest -q
```

On Windows, if pytest cannot write to its default temp folder, pass one it can use:

```powershell
python -m pytest -q --basetemp .pytest-tmp
```

## Promo video

`promo/render_promo.py` draws every frame with Pillow from the real engine and avatar renderer, and `promo/compose_music.py` synthesises the soundtrack with NumPy, so neither depends on licensed media. Rebuild the video after a change:

```bash
python promo/compose_music.py
python promo/render_promo.py
```

With `imageio-ffmpeg` installed the output is H.264 with AAC audio. Without it, the script writes a silent MPEG-4 file through OpenCV.

## Limitations

Skin tone and undertone come from a heuristic that is sensitive to lighting, and face detection uses OpenCV's lightweight detector rather than a face-parsing model. The avatars are 2D PNG overlays, so realism depends on those assets. The rules are explainable and fixed: reactions personalise the ranking, but the app does not follow trends. Password reset is not implemented.

## Credits

Built by Masanbat Mulu.
