# FitBuddy – AI Fitness Plan Generator

A FastAPI web app that uses Google Gemini models to generate personalized 7-day
workout plans and nutrition tips, with SQLite storage and a feedback loop.

## Project structure
```
fitbuddy/
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── routes.py                  # All route handlers
│   ├── database.py                # SQLAlchemy models + DB helpers
│   ├── schemas.py                 # Pydantic request models
│   ├── gemini_generator.py        # Gemini Pro – workout plan generator
│   ├── gemini_flash_generator.py  # Gemini Flash – nutrition tips
│   ├── updated_plan.py            # Feedback-based plan updater
│   ├── nutrition.py                # Wraps Gemini Flash + fallback tips
│   ├── templates/
│   │   ├── index.html             # Input form
│   │   ├── result.html            # Plan + tip + feedback form
│   │   └── all_users.html         # Admin dashboard
│   └── static/images/
└── fitbuddy.db                    # Created automatically on first run
```

## 1. Set up the environment
```bash
cd fitbuddy
python -m venv fitbuddy-env

# Windows
fitbuddy-env\Scripts\activate
# macOS / Linux
source fitbuddy-env/bin/activate

pip install -r requirements.txt
```

## 2. Add your Gemini API key
1. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and paste your key:
   ```
   GOOGLE_API_KEY=your_real_key_here
   ```

> Note: the doc this project is based on names `gemini-1.5-pro` / `gemini-1.5-flash`.
> Google periodically retires older model versions — if you get a "model not found"
> error, check https://ai.google.dev/gemini-api/docs/models for current model names
> and set `GEMINI_PRO_MODEL` / `GEMINI_FLASH_MODEL` in `.env` accordingly (e.g. a
> current `gemini-2.x-flash` / `gemini-2.x-pro` variant).

## 3. Run the server
```bash
uvicorn app.main:app --reload
```

- App: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs
- Admin dashboard: http://127.0.0.1:8000/view-all-users

## 4. How it works
1. **Home page (`/`)** – user fills in name, ID, age, weight, goal, intensity.
2. **`POST /generate-workout`** – saves the user, calls Gemini Pro for a 7-day plan
   and Gemini Flash for a nutrition tip, stores both, and renders `result.html`.
3. **`POST /submit-feedback`** – takes feedback text, sends the original plan +
   feedback to Gemini Pro, stores the revised plan, and re-renders `result.html`.
4. **`GET /view-all-users`** – admin dashboard listing every user with their
   original and updated plans side by side.

Raw JSON API endpoints are also available for testing directly (e.g. via `/docs`):
- `POST /generate-workout/gemini`
- `GET /nutrition-tip?goal=...`
- `POST /update-plan/{user_id}`

## Troubleshooting
- **`Error: ...` inside the plan text** – usually means the API key is missing/invalid,
  or the model name is outdated. Check `.env` and the model-name note above.
- **Import errors on startup** – make sure you run uvicorn from the `fitbuddy/`
  folder so `app.main:app` resolves correctly.
