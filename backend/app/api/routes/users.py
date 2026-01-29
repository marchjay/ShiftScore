from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_owner
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.users import EmployeeCreateIn, OwnerCreateIn, UserOut


router = APIRouter(prefix="/users")


@router.post("/employees", response_model=UserOut)
def create_employee(payload: EmployeeCreateIn, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == str(payload.email).strip().lower()).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Username/email already in use")

    user = User(
        bar_id=owner.bar_id,
        email=str(payload.email).strip().lower(),
        name=payload.name,
        role=UserRole.employee,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/owners", response_model=UserOut)
def create_owner(payload: OwnerCreateIn, owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == str(payload.email).strip().lower()).first()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Username/email already in use")

    user = User(
        bar_id=owner.bar_id,
        email=str(payload.email).strip().lower(),
        name=payload.name,
        role=UserRole.owner,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
def list_users(owner: User = Depends(require_owner), db: Session = Depends(get_db)):
    users = (
        db.query(User)
        .filter(User.bar_id == owner.bar_id)
        .order_by(User.role.asc(), User.name.asc(), User.id.asc())
        .all()
    )
    return [UserOut.model_validate(u) for u in users]
