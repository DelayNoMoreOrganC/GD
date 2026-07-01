"""Pydantic API request/response models."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    org_id: str
    is_active: bool

    model_config = {"from_attributes": True}


# ---- Cases ----
class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    case_type: str = "civil"


class CaseOut(BaseModel):
    id: str
    title: str
    case_type: str
    created_at: str
    file_count: int = 0
    last_task_status: Optional[str] = None


class CaseFileOut(BaseModel):
    id: str
    filename: str
    doc_type: str
    file_size: int
    created_at: str


class CaseFileUpdate(BaseModel):
    doc_type: str = Field(..., min_length=1, max_length=50)


class DocTypeOption(BaseModel):
    value: str
    label: str
    seq: Optional[int] = None


class TaskBriefOut(BaseModel):
    id: int
    status: str
    finished_at: Optional[str] = None
    output_pdf: str = ""

class CaseDetail(CaseOut):
    files: list[CaseFileOut] = []
    done_tasks: list[TaskBriefOut] = []


# ---- Tasks ----
class TaskOut(BaseModel):
    id: int
    case_id: str
    status: str
    progress: float
    stage: str
    error: str
    fields: Optional[dict] = None
    catalog_status: Optional[list] = None
    output_pdf: str = ""
    created_at: str
    finished_at: Optional[str] = None


class GenerateRequest(BaseModel):
    order_mode: str = "catalog"


class FieldUpdate(BaseModel):
    """Edited field values, used to re-fill templates only (no re-OCR)."""
    fields: dict[str, Any]
    order_mode: str = "catalog"
    outcome_type: str = "auto"


# ---- Settings ----
class SystemSettings(BaseModel):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    mineru_api_token: str = ""
    order_mode: str = "catalog"


class SystemSettingsUpdate(SystemSettings):
    pass


# ---- Admin ----
class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "lawyer"
    org_id: Optional[str] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class OrgOut(BaseModel):
    id: str
    name: str

class OrgCreate(BaseModel):
    name: str
