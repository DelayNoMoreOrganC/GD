from __future__ import annotations

import logging

from sqlalchemy import select

from .config import get_settings
from .database import AsyncSessionLocal
from .models import Org, Role, User
from .security import hash_password

logger = logging.getLogger("v6.bootstrap")


async def ensure_bootstrap_admin():
    """Create default org + admin on first run; always ensure default lawyer account."""
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).limit(1))
        if res.scalar_one_or_none() is None:
            org = Org(name="默认律所")
            db.add(org)
            await db.flush()
            db.add(User(
                username=settings.bootstrap_admin_user,
                display_name="管理员",
                role=Role.admin,
                org_id=org.id,
                hashed_password=hash_password(settings.bootstrap_admin_password),
            ))
            await db.commit()
            logger.info("Bootstrapped default org + admin user")

        org_res = await db.execute(select(Org).limit(1))
        org = org_res.scalar_one_or_none()
        if not org:
            return

        existing = await db.execute(select(User).where(User.username == "zgls"))
        if not existing.scalar_one_or_none():
            db.add(User(
                username="zgls",
                display_name="律师",
                role=Role.lawyer,
                org_id=org.id,
                hashed_password=hash_password("zgls123"),
            ))
            await db.commit()
            logger.info("Bootstrapped default lawyer user zgls")
