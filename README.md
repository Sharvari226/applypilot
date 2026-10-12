# ApplyPilot

Private AI-powered job and internship discovery, fit scoring, and application tracker.

## Run locally (Windows PowerShell)

1. `docker compose up -d`  (PostgreSQL on port 5433)
2. Backend: `cd backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload`
3. Frontend: `cd frontend; npm run dev`

Copy `backend/.env.example` to `backend/.env` first. Never commit `.env` files.