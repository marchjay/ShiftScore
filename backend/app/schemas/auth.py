from __future__ import annotations

from pydantic import BaseModel, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_credentials: bool = False


class BootstrapOwnerIn(BaseModel):
    bar_name: str = Field(min_length=1, max_length=200)
    bar_timezone: str = Field(default="America/New_York", min_length=1, max_length=64)

    owner_name: str = Field(min_length=1, max_length=100)
    owner_login: str = Field(min_length=1, max_length=255)
    owner_password: str = Field(min_length=8, max_length=128)


class MeOut(BaseModel):
    id: int
    bar_id: int
    email: str
    name: str
    role: str
    is_active: bool
    must_change_credentials: bool


class FirstLoginUpdateIn(BaseModel):
    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
