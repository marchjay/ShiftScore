from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SpotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bar_id: int
    name: str


class SpotCreateIn(BaseModel):
    bar_id: int
    name: str = Field(min_length=1, max_length=100)
