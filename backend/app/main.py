from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import get_engine
import app.models  # noqa: F401
from app.models.base import Base


app = FastAPI(title="ShiftScore API", version="0.1.0")


# Dev-friendly CORS. Tighten this in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "ShiftScore API is running. See /docs or /health."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.on_event("startup")
def _startup_create_tables():
    # Dev-friendly: auto-create tables. For production, we’ll switch to migrations.
    if not get_settings().auto_create_tables:
        return

    def _ensure_bartender_temp_columns() -> None:
        engine = get_engine()
        inspector = inspect(engine)
        if "bartenders" not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns("bartenders")}
        dialect = engine.dialect.name

        col_user_id = "INTEGER" if dialect == "sqlite" else "INT"
        col_temp_username = "VARCHAR(100)"
        col_temp_password = "VARCHAR(512)"

        statements: list[str] = []
        if "user_id" not in existing:
            statements.append(f"ALTER TABLE bartenders ADD COLUMN user_id {col_user_id} NULL")
        if "temp_username" not in existing:
            statements.append(f"ALTER TABLE bartenders ADD COLUMN temp_username {col_temp_username} NULL")
        if "temp_password_enc" not in existing:
            statements.append(f"ALTER TABLE bartenders ADD COLUMN temp_password_enc {col_temp_password} NULL")

        if not statements:
            return

        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))

    # Uvicorn's reload can trigger overlapping startups. MySQL DDL isn't atomic with
    # SQLAlchemy's check-then-create, so we retry a few times on transient errors.
    for attempt in range(5):
        try:
            Base.metadata.create_all(bind=get_engine())
            _ensure_bartender_temp_columns()
            return
        except OperationalError as exc:
            message = str(getattr(exc, "orig", exc))
            is_transient = (
                "already exists" in message
                or "Table" in message and "already exists" in message
                or "definition is being modified by concurrent DDL" in message
            )
            if is_transient and attempt < 4:
                time.sleep(0.3 * (attempt + 1))
                continue
            raise


app.include_router(api_router)
