from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config_adapter import DEFAULTS, load_user_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import UserSetting
from ..schemas import SystemSettings, SystemSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_schema(merged):
    return SystemSettings(
        deepseek_api_key=merged.get("deepseek_api_key", ""),
        deepseek_base_url=merged.get("deepseek_base_url", "https://api.deepseek.com"),
        deepseek_model=merged.get("deepseek_model", "deepseek-v4-flash"),
        mineru_api_token=merged.get("mineru_api_token", ""),
        order_mode=merged.get("order_mode", "catalog"),
    )


@router.get("", response_model=SystemSettings)
async def get_settings_route(user=Depends(get_current_user), db=Depends(get_db)):
    merged = await load_user_settings(db, user.id)
    return _to_schema(merged)


@router.put("", response_model=SystemSettings)
async def update_settings(body: SystemSettingsUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    mapping = {
        "deepseek_api_key": body.deepseek_api_key,
        "deepseek_base_url": body.deepseek_base_url,
        "deepseek_model": body.deepseek_model,
        "mineru_api_token": body.mineru_api_token,
        "order_mode": body.order_mode,
    }
    for key, value in mapping.items():
        res = await db.execute(
            select(UserSetting).where(
                UserSetting.user_id == user.id, UserSetting.key == key
            )
        )
        row = res.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(UserSetting(user_id=user.id, key=key, value=value))
    await db.commit()
    merged = dict(DEFAULTS)
    merged.update(mapping)
    return _to_schema(merged)
