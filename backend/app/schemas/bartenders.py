from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BartenderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bar_id: int
    name: str
    is_active: bool

    # Only populated for owners while the bartender account is still in first-login state.
    temp_username: str | None = None
    temp_password: str | None = None


class BartenderCreateIn(BaseModel):
    bar_id: int
    name: str = Field(min_length=1, max_length=100)


class BartenderUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class BartenderProvisionIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class BartenderProvisionOut(BaseModel):
    bartender: BartenderOut
    temporary_username: str
    temporary_password: str
