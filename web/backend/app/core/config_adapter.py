"""Build the V4 config dict from per-account API settings."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Role, Setting, User, UserSetting
from ..config import get_settings


DEFAULTS: dict[str, str] = {
    "deepseek_api_key": "",
    "deepseek_base_url": "https://api.deepseek.com",
    "deepseek_model": "deepseek-v4-flash",
    "mineru_api_token": "",
    "order_mode": "catalog",
}


async def load_user_settings(db: AsyncSession, user_id: str) -> dict[str, str]:
    """Load one account's settings without falling back to another account."""
    result = await db.execute(select(UserSetting).where(UserSetting.user_id == user_id))
    user_rows = result.scalars().all()
    rows = {r.key: r.value for r in user_rows}

    # Preserve an existing installation's global configuration for the admin
    # account only. Ordinary accounts always start from clean defaults.
    if not user_rows:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.role == Role.admin:
            legacy_result = await db.execute(select(Setting))
            rows.update({r.key: r.value for r in legacy_result.scalars().all()})

    merged = dict(DEFAULTS)
    merged.update(rows)
    return merged


async def build_v4_config(db: AsyncSession, user_id: str) -> dict:
    """Translate V6 account settings into the config dict core modules expect."""
    s = await load_user_settings(db, user_id)
    preview_only = get_settings().preview_only
    return {
        "ocr": {
            "engine": "mineru_api",
            "page_engine": "mineru_api",
            "cache": True,
        },
        "deepseek": {
            "api_key": s["deepseek_api_key"],
            "base_url": s["deepseek_base_url"],
            "model": s["deepseek_model"],
        },
        "mineru": {
            "api_token": s["mineru_api_token"],
            "api_model_version": "vlm",
            "backend": "hybrid-auto-engine",
            "method": "ocr",
            "lang": "ch",
            "force_ocr": True,
            "quality": "ultra",
        },
        "local_ocr": {
            "max_pages": 0,
        },
        "output": {
            "custom_path": "",
            "docx_only": False,
            "preview_only": preview_only,
        },
        "fill": {
            "mode": "textbox",
        },
        "extraction": {
            "mode": "segmented",
        },
        "archive": {
            "order_mode": s["order_mode"],
        },
        "baidu_ocr": {},
    }
