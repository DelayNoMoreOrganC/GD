"""Case + case-file CRUD with org isolation."""
from __future__ import annotations

import os
import shutil
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ORGS_DIR, get_settings
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import ArchiveTask, Case, CaseFile, User
from ..schemas import CaseCreate, CaseDetail, CaseFileOut, CaseFileUpdate, CaseOut, DocTypeOption
from ..services.doc_type_service import list_upload_doc_types
from ..services.output_cleanup import remove_task_outputs

router = APIRouter(prefix="/api/cases", tags=["cases"])

_settings = get_settings()


def _org_case_dir(org_id, case_id):
    d = os.path.join(str(ORGS_DIR), org_id, "cases", case_id)
    os.makedirs(d, exist_ok=True)
    return d


@router.get("/meta/doc-types", response_model=list[DocTypeOption])
async def get_doc_types(case_type: str = "civil", user=Depends(get_current_user)):
    return list_upload_doc_types(case_type)


@router.get("", response_model=list[CaseOut])
async def list_cases(user=Depends(get_current_user), db=Depends(get_db)):
    res = await db.execute(select(Case).where(Case.org_id == user.org_id).order_by(Case.created_at.desc()))
    cases = res.scalars().all()
    out = []
    for c in cases:
        files = await db.execute(select(CaseFile).where(CaseFile.case_id == c.id))
        file_count = len(files.scalars().all())
        task_res = await db.execute(select(ArchiveTask).where(ArchiveTask.case_id == c.id).order_by(ArchiveTask.created_at.desc()).limit(1))
        last_task = task_res.scalars().first()
        out.append(CaseOut(id=c.id, title=c.title, case_type=c.case_type, created_at=c.created_at.isoformat(), file_count=file_count, last_task_status=last_task.status.value if last_task else None))
    return out


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(body: CaseCreate, user=Depends(get_current_user), db=Depends(get_db)):
    case = Case(title=body.title, case_type=body.case_type, org_id=user.org_id, created_by=user.id)
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return CaseOut(id=case.id, title=case.title, case_type=case.case_type, created_at=case.created_at.isoformat(), file_count=0, last_task_status=None)


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(case_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    res = await db.execute(select(Case).where(Case.id == case_id, Case.org_id == user.org_id))
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    fres = await db.execute(select(CaseFile).where(CaseFile.case_id == case_id).order_by(CaseFile.created_at))
    files = fres.scalars().all()
    task_res = await db.execute(select(ArchiveTask).where(ArchiveTask.case_id == case_id).order_by(ArchiveTask.created_at.desc()).limit(1))
    last_task = task_res.scalars().first()
    file_list = [CaseFileOut(id=f.id, filename=f.filename, doc_type=f.doc_type, file_size=f.file_size, created_at=f.created_at.isoformat()) for f in files]
    all_tasks = await db.execute(
        select(ArchiveTask).where(ArchiveTask.case_id == case_id).order_by(ArchiveTask.created_at.desc())
    )
    done_task_list = []
    for t in all_tasks.scalars().all():
        if t.status.value == "done":
            from ..schemas import TaskBriefOut
            has_docx = bool(
                t.output_docx_dir
                and os.path.isdir(t.output_docx_dir)
                and any(name.lower().endswith(".docx") for name in os.listdir(t.output_docx_dir))
            )
            done_task_list.append(TaskBriefOut(
                id=t.id,
                status=t.status.value,
                finished_at=t.finished_at.isoformat() if t.finished_at else None,
                output_pdf=t.output_pdf or "",
                preview_only=_settings.preview_only,
                has_docx=has_docx,
            ))
    return CaseDetail(
        id=case.id, title=case.title, case_type=case.case_type,
        created_at=case.created_at.isoformat(), file_count=len(files),
        last_task_status=last_task.status.value if last_task else None,
        files=file_list, done_tasks=done_task_list,
    )


@router.delete("/{case_id}", status_code=204)
async def delete_case(case_id: str, user=Depends(require_admin), db=Depends(get_db)):
    res = await db.execute(select(Case).where(Case.id == case_id, Case.org_id == user.org_id))
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    task_res = await db.execute(select(ArchiveTask).where(ArchiveTask.case_id == case_id))
    for task in task_res.scalars().all():
        remove_task_outputs(task)
    file_res = await db.execute(select(CaseFile).where(CaseFile.case_id == case_id))
    for cf in file_res.scalars().all():
        abs_path = str(ORGS_DIR / cf.stored_name)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass
    case_dir = os.path.join(str(ORGS_DIR), user.org_id, "cases", case_id)
    if os.path.isdir(case_dir):
        try:
            shutil.rmtree(case_dir)
        except OSError:
            pass
    await db.execute(delete(CaseFile).where(CaseFile.case_id == case_id))
    await db.execute(delete(ArchiveTask).where(ArchiveTask.case_id == case_id))
    await db.delete(case)
    await db.commit()
    return None


@router.post("/{case_id}/files", response_model=CaseFileOut)
async def upload_file(case_id: str, doc_type: str = Form("default"), file: UploadFile = File(...), user=Depends(get_current_user), db=Depends(get_db)):
    res = await db.execute(select(Case).where(Case.id == case_id, Case.org_id == user.org_id))
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    content = await file.read()
    if len(content) > _settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large")
    safe = os.path.basename(file.filename or "upload.pdf")
    stored = case_id + "_" + safe
    case_dir = _org_case_dir(user.org_id, case_id)
    dest = os.path.join(case_dir, stored)
    with open(dest, "wb") as f:
        f.write(content)
    cf = CaseFile(case_id=case_id, filename=safe, stored_name=os.path.join(user.org_id, "cases", case_id, stored), doc_type=doc_type, file_size=len(content))
    db.add(cf)
    await db.commit()
    await db.refresh(cf)
    return CaseFileOut(id=cf.id, filename=cf.filename, doc_type=cf.doc_type, file_size=cf.file_size, created_at=cf.created_at.isoformat())


@router.patch("/{case_id}/files/{file_id}", response_model=CaseFileOut)
async def update_file(case_id: str, file_id: str, body: CaseFileUpdate, user=Depends(get_current_user), db=Depends(get_db)):
    res = await db.execute(select(Case).where(Case.id == case_id, Case.org_id == user.org_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    fres = await db.execute(select(CaseFile).where(CaseFile.id == file_id, CaseFile.case_id == case_id))
    cf = fres.scalar_one_or_none()
    if not cf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    cf.doc_type = body.doc_type
    await db.commit()
    await db.refresh(cf)
    return CaseFileOut(id=cf.id, filename=cf.filename, doc_type=cf.doc_type, file_size=cf.file_size, created_at=cf.created_at.isoformat())


@router.delete("/{case_id}/files/{file_id}", status_code=204)
async def delete_file(case_id: str, file_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    res = await db.execute(select(CaseFile).where(CaseFile.id == file_id, CaseFile.case_id == case_id))
    cf = res.scalar_one_or_none()
    if not cf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    abs_path = str(ORGS_DIR / cf.stored_name)
    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            pass
    await db.delete(cf)
    await db.commit()
    return None
