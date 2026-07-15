from __future__ import annotations

import logging
import os
import asyncio

from sqlalchemy import select

from ..config import ORGS_DIR, get_settings
from ..core.config_adapter import build_v4_config
from ..core.v4_bridge import archive_pipeline
from ..database import AsyncSessionLocal
from ..models import ArchiveTask, Case, CaseFile, Org, TaskStatus
from ..services.analysis_snapshot import (
    SYSTEM_TEMPLATE_NAMES,
    docx_dir,
    load_analysis,
    load_snapshot_data,
    preview_dir,
    save_snapshot,
    stabilize_templates,
    task_work_dir,
    update_snapshot_fields,
)
from ..services.task_manager import task_manager
from ..services.browser_pdf_service import render_system_form_pdfs
from ..services.word_service import run_word

logger = logging.getLogger("v6.archive")


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _build_sources(files):
    import document_segmenter as ds
    return [ds.DocumentSource(path=f.abs_path, doc_type=f.doc_type) for f in files]


def _build_catalog_status(analysis):
    out = []
    for seq in sorted(analysis.found_seqs):
        out.append({"seq": seq, "found": True})
    for m in analysis.missing_items:
        out.append({"seq": m.get("seq"), "found": False, "name": m.get("name", "")})
    return out


def _persist_fields(analysis) -> dict:
    fields = dict(analysis.fields or {})
    warnings = getattr(analysis, "outcome_warnings", None) or []
    if warnings:
        fields["_outcome_warnings"] = list(warnings)
    return fields


async def _persist_task(task_id, **fields):
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ArchiveTask).where(ArchiveTask.id == task_id))
        task = res.scalar_one_or_none()
        if task is not None:
            for k, v in fields.items():
                setattr(task, k, v)
            await db.commit()


async def _load_case_context(case_id, org_id, user_id):
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Case).where(Case.id == case_id, Case.org_id == org_id))
        case = res.scalar_one_or_none()
        if not case:
            return None
        fres = await db.execute(select(CaseFile).where(CaseFile.case_id == case_id).order_by(CaseFile.created_at))
        files = fres.scalars().all()
        config = await build_v4_config(db, user_id)
        return case, files, config


async def _load_org_name(org_id: str) -> str:
    async with AsyncSessionLocal() as db:
        value = await db.scalar(select(Org.name).where(Org.id == org_id))
        return value or ""


def _work_dir_for(task, org_id: str) -> str:
    return task_work_dir(org_id, task.case_id, task.id)


async def run_archive(task_id, case_id, org_id, user_id, order_mode="catalog"):
    tracker = task_manager.get_tracker(task_id)
    ap = archive_pipeline()
    try:
        ctx = await _load_case_context(case_id, org_id, user_id)
        if not ctx:
            tracker.fail("案件不存在")
            return
        case, files, config = ctx
        if not files:
            tracker.fail("未上传文件")
            return
        case_type = case.case_type
        sources = _build_sources(files)
        base_name = os.path.splitext(files[0].filename)[0]
        order_mode = order_mode or "catalog"
        config.setdefault("archive", {})["order_mode"] = order_mode

        ds_key = (config.get("deepseek") or {}).get("api_key", "").strip()
        mineru_tok = (config.get("mineru") or {}).get("api_token", "").strip()
        if not ds_key:
            tracker.fail("未配置 DeepSeek API Key")
            await _persist_task(task_id, status=TaskStatus.failed, error="未配置 DeepSeek API Key", finished_at=_now())
            return
        if not mineru_tok:
            tracker.fail("未配置 MinerU API Token")
            await _persist_task(task_id, status=TaskStatus.failed, error="未配置 MinerU API Token", finished_at=_now())
            return

        await _persist_task(task_id, status=TaskStatus.running, stage="OCR 识别中", order_mode=order_mode)
        tracker.update(5.0, "正在 OCR 识别")
        analysis = await run_word(ap.analyze_archive, case_type, sources=sources, config=config, log=tracker.log)
        preview_only = get_settings().preview_only
        tracker.update(55.0, "正在生成浏览器预览" if preview_only else "正在生成系统表")

        work = task_work_dir(org_id, case_id, task_id)
        os.makedirs(work, exist_ok=True)
        if not preview_only:
            stabilize_templates(analysis, work, log=tracker.log)
        save_snapshot(work, analysis, base_name=base_name, order_mode=order_mode)
        persist_fields = _persist_fields(analysis)
        dx = "" if preview_only else docx_dir(work)

        await _persist_task(
            task_id,
            status=TaskStatus.awaiting_review,
            progress=60.0,
            stage="待核对浏览器预览与字段" if preview_only else "待核对表格与字段",
            fields=persist_fields,
            catalog_status=_build_catalog_status(analysis),
            output_docx_dir=dx,
            error="",
            finished_at=None,
        )
        tracker.update(60.0, "待核对浏览器预览与字段" if preview_only else "待核对表格与字段")
        tracker.finish()
    except Exception as exc:
        logger.exception("archive task %s failed", task_id)
        await _persist_task(task_id, status=TaskStatus.failed, error=str(exc), finished_at=_now())
        tracker.fail(str(exc))


async def run_assemble(task_id, case_id, org_id, user_id, order_mode=None, skipped=None):
    tracker = task_manager.get_tracker(task_id)
    try:
        ap = archive_pipeline()
        ctx = await _load_case_context(case_id, org_id, user_id)
        if not ctx:
            tracker.fail("案件不存在")
            return
        case, files, config = ctx
        work = task_work_dir(org_id, case_id, task_id)
        analysis, snap = load_analysis(work)
        order_mode = order_mode or snap.get("order_mode") or "catalog"
        base_name = snap.get("base_name") or (os.path.splitext(files[0].filename)[0] if files else "archive")
        config.setdefault("archive", {})["order_mode"] = order_mode
        skip = skipped if skipped is not None else snap.get("skipped") or []

        preview_only = get_settings().preview_only
        if preview_only:
            if not get_settings().chromium_executable:
                raise RuntimeError("未找到 Chrome/Chromium，无法把浏览器表格生成 PDF")
            await _persist_task(task_id, status=TaskStatus.running, stage="正在生成系统表 PDF")
            tracker.update(65.0, "正在生成系统表 PDF")
            organization_name = await _load_org_name(org_id)
            analysis.generated_templates = await asyncio.to_thread(
                render_system_form_pdfs,
                analysis.fields,
                organization_name,
                work,
                tracker.log,
            )
            save_snapshot(
                work,
                analysis,
                base_name=base_name,
                order_mode=order_mode,
                skipped=skip,
            )

        await _persist_task(task_id, status=TaskStatus.running, stage="正在合并归档 PDF")
        tracker.update(75.0, "正在合并归档 PDF")
        output_pdf = os.path.join(work, base_name + "_完整归档.pdf")
        assemble_call = lambda: ap.assemble_archive(
            analysis,
            output_pdf=output_pdf,
            config=config,
            skipped=skip,
            log=tracker.log,
        )
        result = await asyncio.to_thread(assemble_call) if preview_only else await run_word(assemble_call)
        persist_fields = _persist_fields(analysis)
        dx = "" if preview_only else docx_dir(work)
        if result.success:
            await _persist_task(
                task_id,
                status=TaskStatus.done,
                progress=100.0,
                stage="完成",
                fields=persist_fields,
                catalog_status=_build_catalog_status(analysis),
                output_pdf=result.output_pdf,
                output_docx_dir=dx,
                error="",
                order_mode=order_mode,
                finished_at=_now(),
            )
            tracker.update(100.0, "完成")
            tracker.finish()
        else:
            await _persist_task(
                task_id,
                status=TaskStatus.failed,
                error="归档合并失败",
                fields=persist_fields,
                catalog_status=_build_catalog_status(analysis),
                finished_at=_now(),
            )
            tracker.fail("归档合并失败")
    except Exception as exc:
        logger.exception("assemble task %s failed", task_id)
        await _persist_task(task_id, status=TaskStatus.failed, error=str(exc), finished_at=_now())
        tracker.fail(str(exc))


async def update_task_fields(task, org_id: str, field_updates: dict) -> dict:
    work = _work_dir_for(task, org_id)
    data = load_snapshot_data(work)
    merged = dict(data.get("fields") or {})
    merged.update(field_updates or {})
    if "结案小结" in field_updates:
        v = field_updates["结案小结"]
        merged["审（办）结果"] = v
        merged["审办结果"] = v
        # The warnings were generated for the previous outcome text and become stale
        # after a user edit or deterministic execution-evidence recomputation.
        merged["_outcome_warnings"] = []
    update_snapshot_fields(work, merged)
    task.fields = merged
    return merged


async def regenerate_templates(
    task, org_id: str, user_id: str, field_overrides=None, outcome_type="auto"
):
    ap = archive_pipeline()
    ctx = await _load_case_context(task.case_id, org_id, user_id)
    if not ctx:
        raise RuntimeError("案件不存在")
    case, _files, config = ctx
    work = _work_dir_for(task, org_id)
    analysis, snap = load_analysis(work)
    merged = dict(analysis.fields or {})
    merged.update(field_overrides or {})
    if outcome_type and outcome_type != "auto":
        from case_outcome import apply_outcome_type_override, unify_case_outcome_fields
        merged = apply_outcome_type_override(merged, outcome_type, "")
        merged = unify_case_outcome_fields(merged)
    analysis.fields = merged
    if get_settings().preview_only:
        analysis.generated_templates = {}
        save_snapshot(
            work,
            analysis,
            base_name=snap.get("base_name", "archive"),
            order_mode=snap.get("order_mode", "catalog"),
        )
        task.fields = _persist_fields(analysis)
        task.output_docx_dir = ""
        return {}
    import archive_catalog as ac
    catalog = ac.get_catalog(analysis.case_type)
    dx = docx_dir(work)
    os.makedirs(dx, exist_ok=True)
    generated = await run_word(
        ap.generate_system_templates,
        catalog,
        merged,
        log=lambda m: None,
        work_dir=dx,
    )
    analysis.generated_templates = generated
    save_snapshot(work, analysis, base_name=snap.get("base_name", "archive"), order_mode=snap.get("order_mode", "catalog"))
    task.fields = _persist_fields(analysis)
    task.output_docx_dir = dx
    return generated


async def preview_template_pdf(task, org_id: str, template_name: str) -> str:
    if template_name not in SYSTEM_TEMPLATE_NAMES:
        raise ValueError(f"unknown template: {template_name}")
    work = _work_dir_for(task, org_id)
    _analysis, snap = load_analysis(work)
    templates = snap.get("generated_templates") or {}
    docx_path = templates.get(template_name)
    if not docx_path or not os.path.isfile(docx_path):
        raise FileNotFoundError(f"template not ready: {template_name}")
    prev = preview_dir(work)
    os.makedirs(prev, exist_ok=True)
    pdf_path = os.path.join(prev, f"{template_name}.pdf")

    def _convert():
        from archive_pipeline import docx_to_pdf
        ok = docx_to_pdf(docx_path, pdf_path, log=lambda m: None)
        if not ok or not os.path.isfile(pdf_path):
            raise RuntimeError(f"preview failed: {template_name}")
        return pdf_path

    return await run_word(_convert)


async def refill_templates(
    task,
    field_overrides,
    order_mode,
    outcome_type="auto",
    org_id: str = "",
    user_id: str = "",
):
    if not org_id:
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Case).where(Case.id == task.case_id))
            case = res.scalar_one_or_none()
            if not case:
                raise RuntimeError("案件不存在")
            org_id = case.org_id
            user_id = user_id or case.created_by
    if not user_id:
        raise RuntimeError("无法确定当前账号，不能读取 API 配置")
    work = _work_dir_for(task, org_id)
    if os.path.isfile(os.path.join(work, "analysis_snapshot.json")):
        await regenerate_templates(task, org_id, user_id, field_overrides, outcome_type)
        if not get_settings().preview_only:
            task_manager.start(
                task.id,
                run_assemble(task.id, task.case_id, org_id, user_id, order_mode),
            )
        return
    ap = archive_pipeline()
    ctx = await _load_case_context(task.case_id, org_id, user_id)
    if not ctx:
        raise RuntimeError("案件不存在")
    case, files, config = ctx
    sources = _build_sources(files)
    analysis = await run_word(ap.analyze_archive, case.case_type, sources=sources, config=config, log=lambda m: None)
    merged = dict(analysis.fields or {})
    merged.update(field_overrides or {})
    analysis.fields = merged
    import archive_catalog as ac
    catalog = ac.get_catalog(case.case_type)
    analysis.generated_templates = await run_word(ap.generate_system_templates, catalog, merged, log=lambda m: None)
    config.setdefault("archive", {})["order_mode"] = order_mode or "catalog"
    base_name = os.path.splitext(files[0].filename)[0] if files else "archive"
    out_dir = work or task_work_dir(org_id, task.case_id, task.id)
    os.makedirs(out_dir, exist_ok=True)
    output_pdf = os.path.join(out_dir, base_name + "_完整归档.pdf")
    result = await run_word(ap.assemble_archive, analysis, output_pdf=output_pdf, config=config, log=lambda m: None)
    task.status = TaskStatus.done if result.success else TaskStatus.failed
    task.progress = 100.0
    task.fields = _persist_fields(analysis)
    task.catalog_status = _build_catalog_status(analysis)
    task.output_pdf = result.output_pdf if result.success else task.output_pdf
    if analysis.generated_templates:
        task.output_docx_dir = os.path.dirname(list(analysis.generated_templates.values())[0])
    task.order_mode = order_mode or "catalog"
    task.error = "" if result.success else "归档合并失败"
    task.finished_at = _now()

async def save_template_docx(task, org_id: str, template_name: str, content: bytes) -> str:
    if template_name not in SYSTEM_TEMPLATE_NAMES:
        raise ValueError(f"unknown template: {template_name}")
    work = _work_dir_for(task, org_id)
    analysis, snap = load_analysis(work)
    dx = docx_dir(work)
    os.makedirs(dx, exist_ok=True)
    path = os.path.join(dx, f"{template_name}.docx")
    with open(path, "wb") as f:
        f.write(content)
    templates = dict(snap.get("generated_templates") or {})
    templates[template_name] = path
    analysis.generated_templates = templates
    save_snapshot(work, analysis, base_name=snap.get("base_name", "archive"), order_mode=snap.get("order_mode", "catalog"))
    task.output_docx_dir = dx
    return path


def get_template_docx_path(task, org_id: str, template_name: str) -> str:
    if template_name not in SYSTEM_TEMPLATE_NAMES:
        raise ValueError(f"unknown template: {template_name}")
    work = _work_dir_for(task, org_id)
    _analysis, snap = load_analysis(work)
    path = (snap.get("generated_templates") or {}).get(template_name)
    if path and os.path.isfile(path):
        return path
    fallback = os.path.join(docx_dir(work), f"{template_name}.docx")
    if os.path.isfile(fallback):
        return fallback
    raise FileNotFoundError(template_name)
