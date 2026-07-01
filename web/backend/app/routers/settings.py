from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config_adapter import DEFAULTS
from ..database import get_db
from ..deps import require_admin
from ..models import Setting, User
from ..schemas import SystemSettings, SystemSettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_schema(merged):
    return SystemSettings(
        deepseek_api_key=merged.get("deepseek_api_key", ""),
        deepseek_base_url=merged.get("deepseek_base_url", "https://api.deepseek.com"),
        deepseek_model=merged.get("deepseek_model", "deepseek-chat"),
        mineru_api_token=merged.get("mineru_api_token", ""),
        order_mode=merged.get("order_mode", "catalog"),
    )


@router.get("", response_model=SystemSettings)
async def get_settings_route(user=Depends(require_admin), db=Depends(get_db)):
    res = await db.execute(select(Setting))
    rows = {r.key: r.value for r in res.scalars().all()}
    merged = dict(DEFAULTS)
    merged.update(rows)
    return _to_schema(merged)


@router.put("", response_model=SystemSettings)
async def update_settings(body: SystemSettingsUpdate, user=Depends(require_admin), db=Depends(get_db)):
    mapping = {
        "deepseek_api_key": body.deepseek_api_key,
        "deepseek_base_url": body.deepseek_base_url,
        "deepseek_model": body.deepseek_model,
        "mineru_api_token": body.mineru_api_token,
        "order_mode": body.order_mode,
    }
    for key, value in mapping.items():
        res = await db.execute(select(Setting).where(Setting.key == key))
        row = res.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))
    await db.commit()
    merged = dict(DEFAULTS)
    merged.update(mapping)
    return _to_schema(merged)
