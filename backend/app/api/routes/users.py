from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.models import Role, User
from app.deps import CurrentUser, DbSession, hash_password, require_roles
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: DbSession,
    _admin: Annotated[User, Depends(require_roles(Role.admin))],
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DbSession,
    _admin: Annotated[User, Depends(require_roles(Role.admin))],
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    _admin: Annotated[User, Depends(require_roles(Role.admin))],
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data.pop("password"))
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/roles")
def list_roles(_: CurrentUser):
    return {"roles": [r.value for r in Role]}
