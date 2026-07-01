"""Archive task endpoints: generate, status, download, WebSocket progress."""
from __future__ import annotations
import asyncio
import os
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ORGS_DIR
from ..database import AsyncSessionLocal, get_db
from ..deps import get_current_user
from ..models import ArchiveTask, Case, CaseFile, TaskStatus, User
from ..schemas import AssembleRequest, FieldUpdate, FieldsPatch, GenerateRequest, RegenerateRequest, TaskOut
from ..security import decode_token
from ..services.analysis_snapshot import SYSTEM_TEMPLATE_NAMES
from ..services.archive_service import (
    get_template_docx_path,
    preview_template_pdf,
    refill_templates,
    save_template_docx,
    regenerate_templates,
    run_archive,
    run_assemble,
    update_task_fields,
)
from ..services.output_cleanup import remove_task_outputs
from ..services.task_manager import task_manager

router = APIRouter(tags=["tasks"])


async def _load_task_for_user(db, task_id, org_id):
    res = await db.execute(select(ArchiveTask).join(Case, ArchiveTask.case_id == Case.id).where(ArchiveTask.id == task_id, Case.org_id == org_id))
    return res.scalar_one_or_none()


def _task_out(task):
    finished = task.finished_at.isoformat() if task.finished_at else None
    return TaskOut(id=task.id, case_id=task.case_id, status=task.status.value, progress=task.progress, stage=task.stage, error=task.error, fields=task.fields, catalog_status=task.catalog_status, output_pdf=task.output_pdf, created_at=task.created_at.isoformat(), finished_at=finished)


@router.post("/api/cases/{case_id}/generate", response_model=TaskOut, status_code=201)
async def generate(body: GenerateRequest, case_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    res = await db.execute(select(Case).where(Case.id == case_id, Case.org_id == user.org_id))
    case = res.scalar_one_or_none()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found")
    fres = await db.execute(select(CaseFile).where(CaseFile.case_id == case_id))
    files = fres.scalars().all()
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no files uploaded")
    task = ArchiveTask(case_id=case_id, status=TaskStatus.pending, order_mode=body.order_mode)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    task_manager.start(task.id, run_archive(task.id, case_id, user.org_id, body.order_mode))
    return _task_out(task)


@router.get("/api/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return _task_out(task)


@router.get("/api/tasks/{task_id}/templates")
async def list_templates(task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return {"templates": list(SYSTEM_TEMPLATE_NAMES)}


@router.patch("/api/tasks/{task_id}/fields", response_model=TaskOut)
async def patch_fields(body: FieldsPatch, task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if task.status not in (TaskStatus.awaiting_review, TaskStatus.done):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "task not editable")
    task.fields = await update_task_fields(task, user.org_id, body.fields)
    await db.commit()
    await db.refresh(task)
    return _task_out(task)


@router.post("/api/tasks/{task_id}/regenerate-templates", response_model=TaskOut)
async def regenerate(body: RegenerateRequest, task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if task.status != TaskStatus.awaiting_review:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "task not in review")
    await regenerate_templates(task, user.org_id, body.fields, body.outcome_type)
    task.stage = "表格已更新，请预览后合并"
    await db.commit()
    await db.refresh(task)
    return _task_out(task)


@router.post("/api/tasks/{task_id}/assemble", response_model=TaskOut)
async def assemble(body: AssembleRequest, task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if task.status != TaskStatus.awaiting_review:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "task not in review")
    if task_manager.is_running(task_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "task already running")
    task.status = TaskStatus.running
    task.stage = "正在合并归档"
    await db.commit()
    task_manager.start(task.id, run_assemble(task.id, task.case_id, user.org_id, body.order_mode, body.skipped or None))
    await db.refresh(task)
    return _task_out(task)


@router.get("/api/tasks/{task_id}/preview/{template_name}")
async def preview(task_id: int, template_name: str, token: str = "", db: AsyncSession = Depends(get_db)):
    from ..security import decode_token as _dt
    payload = _dt(token) if token else None
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "需要登录")
    org_id = payload.get("org")
    task = await _load_task_for_user(db, task_id, org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if template_name not in SYSTEM_TEMPLATE_NAMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown template")
    try:
        pdf_path = await preview_template_pdf(task, org_id, template_name)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "template not ready")
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{template_name}.pdf")




@router.get("/api/tasks/{task_id}/docx/{template_name}")
async def get_docx(task_id: int, template_name: str, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if template_name not in SYSTEM_TEMPLATE_NAMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown template")
    try:
        path = get_template_docx_path(task, user.org_id, template_name)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "docx not ready")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{template_name}.docx",
        content_disposition_type="inline",
    )


@router.put("/api/tasks/{task_id}/docx/{template_name}")
async def put_docx(task_id: int, template_name: str, file: UploadFile = File(...), user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if task.status not in (TaskStatus.awaiting_review, TaskStatus.done):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "task not editable")
    if template_name not in SYSTEM_TEMPLATE_NAMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown template")
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty file")
    try:
        await save_template_docx(task, user.org_id, template_name, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    await db.commit()
    return {"ok": True, "template": template_name}

@router.post("/api/tasks/{task_id}/refill", response_model=TaskOut)
async def refill(body: FieldUpdate, task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if task.status == TaskStatus.awaiting_review:
        await regenerate_templates(task, user.org_id, body.fields, body.outcome_type)
        await db.commit()
        await db.refresh(task)
        return _task_out(task)
    await refill_templates(task, body.fields, body.order_mode, body.outcome_type, user.org_id)
    await db.commit()
    await db.refresh(task)
    return _task_out(task)


@router.get("/api/tasks/{task_id}/download/{kind}")
async def download(task_id: int, kind: str, token: str = "", db: AsyncSession = Depends(get_db)):
    from ..security import decode_token as _dt
    payload = _dt(token) if token else None
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "需要登录才能下载")
    org_id = payload.get("org")
    if not org_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "令牌无效")
    task = await _load_task_for_user(db, task_id, org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if kind == "archive":
        if not task.output_pdf or not os.path.exists(task.output_pdf):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "archive not ready")
        return FileResponse(task.output_pdf, media_type="application/pdf", filename=os.path.basename(task.output_pdf))
    if kind == "docx":
        d = task.output_docx_dir
        if not d or not os.path.isdir(d):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "docx not ready")
        docs = [f for f in os.listdir(d) if f.lower().endswith(".docx")]
        if not docs:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no docx")
        return FileResponse(os.path.join(d, docs[0]), filename=docs[0])
    if kind == "zip":
        d = task.output_docx_dir
        if not d or not os.path.isdir(d):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "no outputs")
        zip_path = d + ".zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in os.listdir(d):
                if f.lower().endswith(".docx"):
                    zf.write(os.path.join(d, f), f)
        return FileResponse(zip_path, filename=os.path.basename(zip_path))
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad kind")


@router.websocket("/api/ws/tasks/{task_id}")
async def task_ws(websocket: WebSocket, task_id: int):
    token = websocket.query_params.get("token", "")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4401)
        return
    org = payload.get("org")
    await websocket.accept()
    async with AsyncSessionLocal() as db:
        task = await _load_task_for_user(db, task_id, org)
    if not task:
        await websocket.send_json({"type": "error", "error": "task not found"})
        await websocket.close()
        return
    tracker = task_manager.get_tracker(task_id)
    q = await tracker.subscribe()
    for line in tracker.log_lines[-200:]:
        await websocket.send_json({"type": "log", "text": line})
    await websocket.send_json({"type": "progress", "progress": tracker.progress, "stage": tracker.stage})
    try:
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=25.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue
            await websocket.send_json(msg)
            mtype = msg.get("type")
            if mtype == "done" or mtype == "error":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await tracker.unsubscribe(q)
        await websocket.close()


@router.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    if task.status not in (TaskStatus.done, TaskStatus.awaiting_review):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "only completed or review tasks can be deleted")
    remove_task_outputs(task)
    await db.delete(task)
    await db.commit()
    return None
