from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_owner
from app.db.session import get_db
from app.models.bartender import Bartender
from app.models.bar import Bar
from app.models.spot import Spot
from app.models.spot_score_config import SpotCapMode, SpotScoreConfig
from app.models.user import User


router = APIRouter(prefix="/dev")


@router.post("/seed")
def seed(owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    """Create a default bar + a few spots if none exist.

    This is purely for local development to get the UI moving.
    """

    bar = db.query(Bar).filter(Bar.id == owner.bar_id).first()
    if bar is None:
        bar = Bar(name="Demo Bar", timezone="America/New_York")
        db.add(bar)
        db.flush()
        owner.bar_id = bar.id
        db.add(owner)

    existing_spots = db.query(Spot).filter(Spot.bar_id == bar.id).all()
    if not existing_spots:
        for name in ["Main Well", "Service Bar", "Patio"]:
            spot = Spot(bar_id=bar.id, name=name)
            db.add(spot)
            db.flush()

            cfg = SpotScoreConfig(
                bar_id=bar.id,
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

    existing_bartenders = db.query(Bartender).filter(Bartender.bar_id == bar.id).all()
    if not existing_bartenders:
        for name in ["Jay", "Alex", "Sam"]:
            db.add(Bartender(bar_id=bar.id, name=name))

    db.commit()
    return {"bar_id": bar.id}
