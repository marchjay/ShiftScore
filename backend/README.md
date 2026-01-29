# ShiftScore Backend (FastAPI)

This folder contains the FastAPI backend API for ShiftScore.

## What’s included
- FastAPI app with a `/health` endpoint
- SQLAlchemy wiring (engine + session)
- Environment-based settings (MySQL URL)

## Local setup (Windows PowerShell)

Create a virtual env and install deps:

```powershell
cd backend
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

Create an `.env` file (example):

```text
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/shiftscore
```

Run the API:

```powershell
uvicorn app.main:app --reload
```

Open:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs
