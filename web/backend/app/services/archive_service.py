from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import select

from ..config import ORGS_DIR
from ..core.config_adapter import build_v4_config
from ..core.v4_bridge import archive_pipeline, pdf_doc_locator
from ..database import AsyncSessionLocal
from ..models import ArchiveTask, Case, CaseFile, TaskStatus
from ..services.task_manager import task_manager
from ..services.word_service import run_word

logger = logging.getLogger("v5.archive")


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _build_sources(files):
    """Build V4 DocumentSource list from CaseFile rows (path A or B)."""
    import document_segmenter as ds
    sources = []
    for f in files:
        sources.append(ds.DocumentSource(path=f.abs_path, doc_type=f.doc_type))
    return sources


def _build_catalog_status(analysis):
    """Render found/missing catalog items as a JSON-serializable list."""
    out = []
    for seq in sorted(analysis.found_seqs):
        out.append({"seq": seq, "found": True})
    for m in analysis.missing_items:
        out.append({"seq": m.get("seq"), "found": False, "name": m.get("name", "")})
    return out


async def _persist_task(task_id, **fields):
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ArchiveTask).where(ArchiveTask.id == task_id))
        task = res.scalar_one_or_none()
        if task is not None:
            for k, v in fields.items():
                setattr(task, k, v)
            await db.commit()


async def run_archive(task_id, case_id, org_id):
    tracker = task_manager.get_tracker(task_id)
    ap = archive_pipeline()
    try:
        # --- load case context inside a short-lived session, then release it ---
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Case).where(Case.id == case_id, Case.org_id == org_id))
            case = res.scalar_one_or_none()
            if not case:
                tracker.fail("案件不存在")
                return
            fres = await db.execute(select(CaseFile).where(CaseFile.case_id == case_id).order_by(CaseFile.created_at))
            files = fres.scalars().all()
            if not files:
                tracker.fail("未上传文件")
                return
            case_type = case.case_type
            config = await build_v4_config(db)
            sources = _build_sources(files)
            base_name = os.path.splitext(files[0].filename)[0]

        ds_key = (config.get("deepseek") or {}).get("api_key", "").strip()
        mineru_tok = (config.get("mineru") or {}).get("api_token", "").strip()
        if not ds_key:
            tracker.fail("未配置 DeepSeek API Key，请到「系统设置」填写后重新生成")
            await _persist_task(task_id, status=TaskStatus.failed, error="未配置 DeepSeek API Key", finished_at=_now())
            return
        if not mineru_tok:
            tracker.fail("未配置 MinerU API Token，请到「系统设置」填写后重新生成")
            await _persist_task(task_id, status=TaskStatus.failed, error="未配置 MinerU API Token", finished_at=_now())
            return

        # --- phase 1: analyze (OCR + segmentation + fields + templates) ---
        await _persist_task(task_id, status=TaskStatus.running, stage="OCR 识别中")
        tracker.update(5.0, "正在 OCR 识别")
        analyze_fn = ap.analyze_archive
        analysis = await run_word(analyze_fn, case_type, sources=sources, config=config, log=tracker.log)
        tracker.update(55.0, "正在生成文书")
        docx_dir = ""
        if analysis.generated_templates:
            docx_dir = os.path.dirname(list(analysis.generated_templates.values())[0])

        # --- phase 2: assemble merged archive PDF ---
        out_dir = os.path.join(str(ORGS_DIR), org_id, "cases", case_id, "tasks", str(task_id))
        os.makedirs(out_dir, exist_ok=True)
        output_pdf = os.path.join(out_dir, base_name + "_完整归档.pdf")
        assemble_fn = ap.assemble_archive
        result = await run_word(assemble_fn, analysis, output_pdf=output_pdf, config=config, log=tracker.log)
        tracker.update(95.0, "正在合并归档")


        persist_fields = dict(analysis.fields or {})
        if getattr(analysis, "outcome_warnings", None):
            persist_fields["_outcome_warnings"] = list(analysis.outcome_warnings)

        if result.success:
            await _persist_task(
                task_id,
                status=TaskStatus.done,
                progress=100.0,
                stage="完成",
                fields=persist_fields,
                catalog_status=_build_catalog_status(analysis),
                output_pdf=result.output_pdf,
                output_docx_dir=docx_dir,
                error="",
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
    except Exception as exc:
        logger.exception("archive task %s failed", task_id)
        await _persist_task(task_id, status=TaskStatus.failed, error=str(exc), output_docx_dir="", order_mode="catalog", finished_at=_now())
        tracker.fail(str(exc))


async def refill_templates(task, field_overrides, order_mode, outcome_type="auto"):
    """Re-fill Word templates using edited field values (no re-OCR).

    Reuses the last task's analysis doc_spans/catalog; only field values
    change. Persists new docx outputs + re-assembles the merged PDF.
    """
    ap = archive_pipeline()
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Case).where(Case.id == task.case_id))
        case = res.scalar_one_or_none()
        if not case:
            raise RuntimeError("案件不存在")
        fres = await db.execute(select(CaseFile).where(CaseFile.case_id == task.case_id).order_by(CaseFile.created_at))
        files = fres.scalars().all()
        config = await build_v4_config(db)
        sources = _build_sources(files)
        case_type = case.case_type
        base_name = os.path.splitext(files[0].filename)[0] if files else "archive"

    analyze_fn = ap.analyze_archive
    analysis = await run_word(analyze_fn, case_type, sources=sources, config=config, log=lambda m: None)

    merged_fields = dict(analysis.fields or {})
    merged_fields.update(field_overrides or {})
    if outcome_type and outcome_type != "auto":
        from case_outcome import apply_outcome_type_override, unify_case_outcome_fields

        pdf_text = ""
        merged_fields = apply_outcome_type_override(merged_fields, outcome_type, pdf_text)
        merged_fields = unify_case_outcome_fields(merged_fields)
    analysis.fields = merged_fields

    import archive_catalog as ac

    catalog = ac.get_catalog(case_type)
    analysis.generated_templates = ap.generate_system_templates(
        catalog, merged_fields, log=lambda m: None
    )

    config["archive"]["order_mode"] = order_mode or "catalog"

    org_id = case.org_id
    out_dir = os.path.join(str(ORGS_DIR), org_id, "cases", task.case_id, "tasks", str(task.id))
    os.makedirs(out_dir, exist_ok=True)
    output_pdf = os.path.join(out_dir, base_name + "_完整归档.pdf")
    assemble_fn = ap.assemble_archive
    result = await run_word(assemble_fn, analysis, output_pdf=output_pdf, config=config, log=lambda m: None)

    docx_dir = ""
    if analysis.generated_templates:
        docx_dir = os.path.dirname(list(analysis.generated_templates.values())[0])

    task.status = TaskStatus.done if result.success else TaskStatus.failed
    task.progress = 100.0
    task.fields = merged_fields
    task.catalog_status = _build_catalog_status(analysis)
    task.output_pdf = result.output_pdf if result.success else task.output_pdf
    task.output_docx_dir = docx_dir or task.output_docx_dir
    task.order_mode = order_mode or "catalog"
    task.error = "" if result.success else "归档合并失败"
    task.finished_at = _now()
