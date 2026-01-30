from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ShiftCreateIn(BaseModel):
    bar_id: int
    spot_id: int
    bartender_name: str = Field(min_length=1, max_length=80)
    shift_date: date

    personal_sales_volume: float = Field(ge=0)
    total_bar_sales: float = Field(gt=0)
    personal_tips: float = Field(ge=0)
    hours_worked: float = Field(gt=0)
    transactions_count: int | None = Field(default=None, ge=0)


class ShiftUpdateIn(BaseModel):
    spot_id: int | None = None
    bartender_name: str | None = Field(default=None, min_length=1, max_length=80)
    shift_date: date | None = None

    personal_sales_volume: float | None = Field(default=None, ge=0)
    total_bar_sales: float | None = Field(default=None, gt=0)
    personal_tips: float | None = Field(default=None, ge=0)
    hours_worked: float | None = Field(default=None, gt=0)
    transactions_count: int | None = Field(default=None, ge=0)


class ShiftDeleteOut(BaseModel):
    deleted: bool


class ShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bar_id: int
    spot_id: int
    bartender_name: str
    shift_date: date

    personal_sales_volume: float
    total_bar_sales: float
    personal_tips: float
    hours_worked: float
    transactions_count: int | None

    pct_of_bar_sales: float
    tip_pct: float
    sales_per_hour: float

    score_total: float | None = None
    score_version: str | None = None
    breakdown: dict | None = None

    @classmethod
    def from_orm_with_score(cls, shift, score_result):
        data = cls.model_validate(shift).model_dump()
        if score_result is not None:
            data["score_total"] = float(score_result.score_total)
            data["score_version"] = score_result.score_version
            data["breakdown"] = score_result.breakdown_json
        return cls(**data)
