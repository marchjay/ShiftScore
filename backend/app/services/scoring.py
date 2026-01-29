from __future__ import annotations

from dataclasses import dataclass

from app.models.shift import Shift
from app.models.spot_score_config import SpotScoreConfig
from app.schemas.shifts import ShiftCreateIn


def _clamp01(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def _linear_score(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return _clamp01((value - low) / (high - low))


@dataclass
class ScoreOutput:
    score_total: float
    score_version: str
    breakdown: dict


def compute_shift(payload: ShiftCreateIn, cfg: SpotScoreConfig) -> tuple[Shift, ScoreOutput]:
    pct_of_bar_sales = payload.personal_sales_volume / payload.total_bar_sales
    tip_pct = payload.personal_tips / payload.personal_sales_volume if payload.personal_sales_volume > 0 else 0.0
    sales_per_hour = payload.personal_sales_volume / payload.hours_worked

    # 4 metrics, equal weights: 25 each
    m_sales = _linear_score(payload.personal_sales_volume, cfg.sales_volume_low, cfg.sales_volume_high)
    m_pct = _linear_score(pct_of_bar_sales, cfg.pct_of_bar_sales_low, cfg.pct_of_bar_sales_high)
    m_tip = _linear_score(tip_pct, cfg.tip_pct_low, cfg.tip_pct_high)
    m_sph = _linear_score(sales_per_hour, cfg.sales_per_hour_low, cfg.sales_per_hour_high)

    breakdown = {
        "sales_volume": {"value": payload.personal_sales_volume, "normalized": m_sales, "points": m_sales * 20.0},
        "pct_of_bar_sales": {"value": pct_of_bar_sales, "normalized": m_pct, "points": m_pct * 50.0},
        "tip_pct": {"value": tip_pct, "normalized": m_tip, "points": m_tip * 10.0},
        "sales_per_hour": {"value": sales_per_hour, "normalized": m_sph, "points": m_sph * 20.0}
    }

    score_total = float(breakdown["sales_volume"]["points"] + breakdown["pct_of_bar_sales"]["points"] + breakdown["tip_pct"]["points"] + breakdown["sales_per_hour"]["points"])

    shift = Shift(
        bar_id=payload.bar_id,
        spot_id=payload.spot_id,
        bartender_name=payload.bartender_name,
        shift_date=payload.shift_date,
        personal_sales_volume=payload.personal_sales_volume,
        total_bar_sales=payload.total_bar_sales,
        personal_tips=payload.personal_tips,
        hours_worked=payload.hours_worked,
        transactions_count=payload.transactions_count,
        pct_of_bar_sales=pct_of_bar_sales,
        tip_pct=tip_pct,
        sales_per_hour=sales_per_hour,
    )

    return shift, ScoreOutput(score_total=score_total, score_version="v1", breakdown=breakdown)
