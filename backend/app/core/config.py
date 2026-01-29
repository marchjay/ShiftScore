from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # The backend reads DATABASE_URL from `backend/.env` (recommended) or from your
    # environment variables. This default is only a safe fallback.
    database_url: str = Field(
        default="sqlite+pysqlite:///./dev.db",
        validation_alias="DATABASE_URL",
    )

    auto_create_tables: bool = Field(
        default=True,
        validation_alias="AUTO_CREATE_TABLES",
    )

    jwt_secret_key: str = Field(
        default="change-me",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias="JWT_ALGORITHM",
    )
    access_token_exp_minutes: int = Field(
        default=60 * 24,
        validation_alias="ACCESS_TOKEN_EXP_MINUTES",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
