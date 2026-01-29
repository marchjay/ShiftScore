from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.bar import Bar
from app.models.bartender import Bartender
from app.models.user import User, UserRole
from app.schemas.auth import BootstrapOwnerIn, FirstLoginUpdateIn, MeOut, TokenOut


TEMP_LOGIN_PREFIX = "tmp_"


def _must_change_credentials(user: User) -> bool:
    return user.email.lower().startswith(TEMP_LOGIN_PREFIX)


def _normalize_login(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        raise HTTPException(status_code=422, detail="Username/email is required")
    return normalized


router = APIRouter(prefix="/auth")


@router.post("/bootstrap", response_model=TokenOut)
def bootstrap_owner(payload: BootstrapOwnerIn, db: Session = Depends(get_db)):
    existing_owner = db.query(User).filter(User.role == UserRole.owner).first()
    if existing_owner is not None:
        raise HTTPException(status_code=400, detail="Owner already exists; bootstrap disabled")

    bar = Bar(name=payload.bar_name, timezone=payload.bar_timezone)
    db.add(bar)
    db.flush()

    user = User(
        bar_id=bar.id,
        email=_normalize_login(payload.owner_login),
        name=payload.owner_name,
        role=UserRole.owner,
        password_hash=hash_password(payload.owner_password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role.value, bar_id=user.bar_id)
    return TokenOut(access_token=token, must_change_credentials=False)


@router.post("/login", response_model=TokenOut)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identifier = _normalize_login(form_data.username)
    user = (
        db.query(User)
        .filter((User.email == identifier) | (User.email == f"{TEMP_LOGIN_PREFIX}{identifier}"))
        .first()
    )
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id), role=user.role.value, bar_id=user.bar_id)
    return TokenOut(access_token=token, must_change_credentials=_must_change_credentials(user))


@router.post("/first-login", response_model=TokenOut)
def first_login_update(payload: FirstLoginUpdateIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _must_change_credentials(current):
        raise HTTPException(status_code=400, detail="First-login flow is not required for this account")

    new_login = _normalize_login(payload.login)
    if new_login.startswith(TEMP_LOGIN_PREFIX):
        raise HTTPException(status_code=400, detail="Username cannot start with reserved prefix")

    existing = db.query(User).filter(User.email == new_login).first()
    if existing is not None and existing.id != current.id:
        raise HTTPException(status_code=400, detail="Username/email is already in use")

    current.email = new_login
    current.password_hash = hash_password(payload.password)
    db.add(current)

    bartender = db.query(Bartender).filter(Bartender.user_id == current.id).first()
    if bartender is not None:
        bartender.temp_username = None
        bartender.temp_password_enc = None
        db.add(bartender)

    db.commit()

    token = create_access_token(subject=str(current.id), role=current.role.value, bar_id=current.bar_id)
    return TokenOut(access_token=token, must_change_credentials=False)


@router.get("/me", response_model=MeOut)
def me(current: User = Depends(get_current_user)):
    return MeOut(
        id=current.id,
        bar_id=current.bar_id,
        email=current.email,
        name=current.name,
        role=current.role.value,
        is_active=current.is_active,
        must_change_credentials=_must_change_credentials(current),
    )
