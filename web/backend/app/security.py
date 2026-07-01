"""JWT issuance/verification + password hashing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_settings = get_settings()


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(subject: str, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_settings.access_token_expire_minutes)
    return _create_token(subject, expire, "access", extra)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=_settings.refresh_token_expire_days)
    return _create_token(subject, expire, "refresh", {})


def _create_token(subject: str, expire: datetime, token_type: str, extra: dict | None) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": token_type,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _settings.secret_key, algorithm=_settings.algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _settings.secret_key, algorithms=[_settings.algorithm])
    except JWTError:
        return None
