# StyleMatch AI

StyleMatch AI is a Python + Streamlit web app that helps users explore clothing color recommendations based on skin tone, undertone, style, and occasion.

## Link to the Live Demo app:
https://stylematch-ai-h9lu.onrender.com
The app includes:
- skin tone and undertone estimation from an uploaded image
- manual outfit building
- automatic generation of 5 outfit ideas
- avatar preview
- grounded style assistant
- saved outfits with SQLite

---
<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/126d2922-b4b5-4e3b-89c8-1becb403c89f" />

## Features

### 1. Image Analyzer
Upload a front-facing image and get:
- estimated skin tone
- estimated undertone
- dominant skin color swatch
- brightness score

### 2. Outfit Builder
Build a look manually by choosing:
- shirt color
- pants color
- shoes color

The app then calculates an outfit score and explains why the look works.

### 3. Generate 5 Looks
Automatically generates 5 outfit combinations based on:
- skin tone
- undertone
- style
- occasion

### 4. AI Style Assistant
Provides grounded styling suggestions using built-in color and styling rules.

### 5. Saved Looks
Save outfit combinations locally and review them later.

---

## Tech Stack

- Python
- Streamlit
- Pillow
- OpenCV
- NumPy
- SQLite
- Pydantic

---

## Project Structure

```text
stylematch_ai_v3/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── avatar_renderer.py
├── database.py
├── image_analysis.py
├── knowledge_base.py
├── models.py
├── recommendation_engine.py
├── style_assistant.py
├── ui_components.py
└── assets/

#### Windows PowerShell:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

#### Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

#### Windows CMD:
python -m venv .venv
.\.venv\Scripts\activate.bat

## Run the app:
streamlit run app.py


## Deploying Online
#### This project is best deployed with:

Streamlit Community Cloud
Render
Hugging Face Spaces
