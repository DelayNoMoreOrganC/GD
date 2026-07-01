"""Authentication endpoints: login, me, refresh, change-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse, UserOut
from ..security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
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
