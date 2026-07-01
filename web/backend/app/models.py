"""ORM models: Org / User / Case / CaseFile / Task / Setting."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class Role(str, enum.Enum):
    admin = "admin"
    lawyer = "lawyer"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="org", cascade="all, delete-orphan")
    cases: Mapped[list["Case"]] = relationship(back_populates="org", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(String(32), ForeignKey("orgs.id"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.lawyer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    org: Mapped["Org"] = relationship(back_populates="users")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(String(32), ForeignKey("orgs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    case_type: Mapped[str] = mapped_column(String(50), default="civil", nullable=False)
    created_by: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    org: Mapped["Org"] = relationship(back_populates="cases")
    files: Mapped[list["CaseFile"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    tasks: Mapped[list["ArchiveTask"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseFile(Base):
    __tablename__ = "case_files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(300), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), default="default", nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    case: Mapped["Case"] = relationship(back_populates="files")

    @property
    def abs_path(self) -> str:
        """Absolute path on disk — resolved relative to project root at runtime."""
        from .config import ORGS_DIR
        return str(ORGS_DIR / self.stored_name)


class ArchiveTask(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id"), nullable=False, index=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String(200), default="")
    log_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    catalog_status: Mapped[list | None] = mapped_column(JSON, nullable=True)
    output_pdf: Mapped[str] = mapped_column(String(500), default="")
    output_docx_dir: Mapped[str] = mapped_column(String(500), default="")
    order_mode: Mapped[str] = mapped_column(String(20), default="catalog")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    case: Mapped["Case"] = relationship(back_populates="tasks")


class Setting(Base):
    """System-level key/value settings (api keys, model config, etc.)."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
