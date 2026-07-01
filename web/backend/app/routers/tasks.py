"""Archive task endpoints: generate, status, download, WebSocket progress."""
from __future__ import annotations
import asyncio
import os
import zipfile

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ORGS_DIR
from ..database import AsyncSessionLocal, get_db
from ..deps import get_current_user
from ..models import ArchiveTask, Case, CaseFile, TaskStatus, User
from ..schemas import FieldUpdate, GenerateRequest, TaskOut
from ..security import decode_token
from ..services.archive_service import run_archive, refill_templates
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
    task_manager.start(task.id, run_archive(task.id, case_id, user.org_id))
    return _task_out(task)


@router.get("/api/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return _task_out(task)


@router.post("/api/tasks/{task_id}/refill", response_model=TaskOut)
async def refill(body: FieldUpdate, task_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    task = await _load_task_for_user(db, task_id, user.org_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    await refill_templates(task, body.fields, body.order_mode, body.outcome_type)
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
    if task.status != TaskStatus.done:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "only completed tasks can be deleted")
    remove_task_outputs(task)
    await db.delete(task)
    await db.commit()
    return None

