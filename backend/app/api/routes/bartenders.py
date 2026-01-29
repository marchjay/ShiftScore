from __future__ import annotations

import re
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.core.security import encrypt_temp_secret, hash_password, decrypt_temp_secret
from app.db.session import get_db
from app.models.bartender import Bartender
from app.models.score_result import ScoreResult
from app.models.shift import Shift
from app.models.user import User
from app.models.user import UserRole
from app.schemas.bartenders import (
    BartenderCreateIn,
    BartenderOut,
    BartenderProvisionIn,
    BartenderProvisionOut,
    BartenderUpdateIn,
)


router = APIRouter(prefix="/bartenders")


TEMP_LOGIN_PREFIX = "tmp_"


def _normalize_username_base(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "", name.strip().lower())
    return base or "bartender"


def _random_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("", response_model=list[BartenderOut])
def list_bartenders(
    bar_id: int = Query(...),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if bar_id != current.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    bartenders = (
        db.query(Bartender)
        .filter(Bartender.bar_id == bar_id)
        .order_by(Bartender.is_active.desc(), Bartender.name.asc(), Bartender.id.asc())
        .all()
    )
    out: list[BartenderOut] = []
    for b in bartenders:
        temp_username = None
        temp_password = None
        if current.role == UserRole.owner and b.temp_username and b.temp_password_enc:
            try:
                temp_username = b.temp_username
                temp_password = decrypt_temp_secret(b.temp_password_enc)
            except Exception:
                # If decryption fails (e.g. secret changed), don't leak or crash.
                temp_username = None
                temp_password = None

        out.append(
            BartenderOut(
                id=b.id,
                bar_id=b.bar_id,
                name=b.name,
                is_active=b.is_active,
                temp_username=temp_username,
                temp_password=temp_password,
            )
        )
    return out


@router.post("", response_model=BartenderOut)
def create_bartender(payload: BartenderCreateIn, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    if payload.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    bartender = Bartender(bar_id=payload.bar_id, name=payload.name)
    db.add(bartender)
    db.commit()
    db.refresh(bartender)
    return BartenderOut.model_validate(bartender)


@router.post("/provision", response_model=BartenderProvisionOut)
def provision_bartender(payload: BartenderProvisionIn, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    bartender = Bartender(bar_id=owner.bar_id, name=payload.name)
    db.add(bartender)
    db.flush()

    base = _normalize_username_base(payload.name)
    temporary_username = None
    for _ in range(25):
        suffix = secrets.randbelow(900) + 100  # 3 digits
        candidate = f"{base}{suffix}"
        exists = db.query(User).filter((User.email == candidate) | (User.email == f"{TEMP_LOGIN_PREFIX}{candidate}")).first()
        if exists is None:
            temporary_username = candidate
            break
    if temporary_username is None:
        # extremely unlikely fallback
        temporary_username = f"{base}{secrets.token_hex(2)}"

    temporary_password = _random_password(10)

    user = User(
        bar_id=owner.bar_id,
        email=f"{TEMP_LOGIN_PREFIX}{temporary_username}",
        name=payload.name,
        role=UserRole.employee,
        password_hash=hash_password(temporary_password),
        is_active=True,
    )
    db.add(user)

    db.flush()
    bartender.user_id = user.id
    bartender.temp_username = temporary_username
    bartender.temp_password_enc = encrypt_temp_secret(temporary_password)

    db.commit()
    db.refresh(bartender)

    return BartenderProvisionOut(
        bartender=BartenderOut.model_validate(bartender),
        temporary_username=temporary_username,
        temporary_password=temporary_password,
    )


@router.patch("/{bartender_id}", response_model=BartenderOut)
def update_bartender(
    bartender_id: int,
    payload: BartenderUpdateIn,
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    bartender = db.query(Bartender).filter(Bartender.id == bartender_id).first()
    if bartender is None:
        raise HTTPException(status_code=404, detail="Bartender not found")

    if bartender.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if payload.name is not None:
        bartender.name = payload.name
    if payload.is_active is not None:
        bartender.is_active = payload.is_active

    db.commit()
    db.refresh(bartender)
    return BartenderOut.model_validate(bartender)


@router.delete("/{bartender_id}")
def delete_bartender(
    bartender_id: int,
    clear_sales: bool = Query(False),
    owner: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    bartender = db.query(Bartender).filter(Bartender.id == bartender_id).first()
    if bartender is None:
        raise HTTPException(status_code=404, detail="Bartender not found")

    if bartender.bar_id != owner.bar_id:
        raise HTTPException(status_code=403, detail="Not allowed")

    deleted_shifts = 0
    deleted_scores = 0

    if clear_sales:
        shift_ids = [
            sid
            for (sid,) in (
                db.query(Shift.id)
                .filter(Shift.bar_id == owner.bar_id)
                .filter(Shift.bartender_name == bartender.name)
                .all()
            )
        ]
        if shift_ids:
            deleted_scores = (
                db.query(ScoreResult)
                .filter(ScoreResult.shift_id.in_(shift_ids))
                .delete(synchronize_session=False)
            )
            deleted_shifts = (
                db.query(Shift)
                .filter(Shift.id.in_(shift_ids))
                .delete(synchronize_session=False)
            )

    user_id = bartender.user_id
    db.delete(bartender)
    db.flush()

    deleted_user = False
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if user is not None:
            db.delete(user)
            deleted_user = True

    db.commit()
    return {
        "status": "deleted",
        "deleted_user": deleted_user,
        "deleted_shifts": deleted_shifts,
        "deleted_scores": deleted_scores,
    }
