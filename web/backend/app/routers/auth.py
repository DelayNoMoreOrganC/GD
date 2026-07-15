"""Authentication endpoints: login, me, refresh, change-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..config import get_settings
from ..deps import get_current_user
from ..models import Org, Role, User
from ..schemas import ChangePasswordRequest, LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not get_settings().registration_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "registration disabled")
    username = body.username.strip().lower()
    result = await db.execute(select(User).where(func.lower(User.username) == username.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")

    org = Org(name=body.org_name.strip())
    db.add(org)
    await db.flush()
    user = User(
        username=username,
        display_name=body.display_name.strip() or username,
        # Self-registered users receive a private organization but no access
        # to global system settings or user administration.
        role=Role.lawyer,
        org_id=org.id,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")
    await db.refresh(user)
    extra = {"org": user.org_id, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(user.id, extra),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(func.lower(User.username) == body.username.strip().lower())
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "disabled")
    extra = {"org": user.org_id, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(user.id, extra),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad refresh token")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user invalid")
    extra = {"org": user.org_id, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(user.id, extra),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "old password wrong")
    user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}
