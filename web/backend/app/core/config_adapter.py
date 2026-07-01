"""Build the V4 config dict from V5 system settings (DB Setting table)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Setting


DEFAULTS: dict[str, str] = {
    "deepseek_api_key": "",
    "deepseek_base_url": "https://api.deepseek.com",
    "deepseek_model": "deepseek-chat",
    "mineru_api_token": "",
    "order_mode": "catalog",
}


async def load_all_settings(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(select(Setting))
    rows = {r.key: r.value for r in result.scalars().all()}
    merged = dict(DEFAULTS)
    merged.update(rows)
    return merged


async def build_v4_config(db: AsyncSession) -> dict:
    """Translate V5 system settings into the config dict V4 modules expect."""
    s = await load_all_settings(db)
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
