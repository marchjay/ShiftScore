from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.shift import Shift
from app.models.spot import Spot
from app.models.spot_score_config import SpotCapMode, SpotScoreConfig
from app.models.user import User
from app.schemas.spots import SpotCreateIn, SpotOut


router = APIRouter(prefix="/spots")


@router.get("", response_model=list[SpotOut])
def list_spots(bar_id: int = Query(...), current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if bar_id != current.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    spots = db.query(Spot).filter(Spot.bar_id == bar_id).order_by(Spot.id.asc()).all()
    return [SpotOut.model_validate(s) for s in spots]


@router.post("", response_model=SpotOut)
def create_spot(payload: SpotCreateIn, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    if payload.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    spot = Spot(bar_id=payload.bar_id, name=payload.name)
    db.add(spot)
    db.flush()

    # Ensure scoring works immediately for new spots.
    cfg = SpotScoreConfig(
        bar_id=payload.bar_id,
        spot_id=spot.id,
        cap_mode=SpotCapMode.manual,
        sales_volume_low=200.0,
        sales_volume_high=1200.0,
        pct_of_bar_sales_low=0.05,
        pct_of_bar_sales_high=0.40,
        tip_pct_low=0.15,
        tip_pct_high=0.30,
        sales_per_hour_low=50.0,
        sales_per_hour_high=250.0,
    )
    db.add(cfg)

    db.commit()
    db.refresh(spot)
    return SpotOut.model_validate(spot)


@router.delete("/{spot_id}")
def delete_spot(spot_id: int, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")

    if spot.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    shift_exists = db.query(Shift.id).filter(Shift.spot_id == spot_id).first() is not None
    if shift_exists:
        raise HTTPException(status_code=400, detail="Cannot delete a spot that already has shifts")

    db.query(SpotScoreConfig).filter(SpotScoreConfig.spot_id == spot_id).delete()
    db.delete(spot)
    db.commit()

    return {"status": "ok"}
