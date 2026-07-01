"""Persist / restore ArchiveAnalysis between analyze and assemble (V6 review gate)."""
from __future__ import annotations

import json
import os
import shutil
from typing import Dict, List, Optional

SNAPSHOT_FILENAME = "analysis_snapshot.json"

SYSTEM_TEMPLATE_NAMES = (
    "立案审批表",
    "送达材料清单",
    "档案卷宗",
    "结案报告表",
    "质量监督卡",
)


def task_work_dir(org_id: str, case_id: str, task_id: int) -> str:
    from ..config import ORGS_DIR

    return os.path.join(str(ORGS_DIR), org_id, "cases", case_id, "tasks", str(task_id))


def snapshot_path(work_dir: str) -> str:
    return os.path.join(work_dir, SNAPSHOT_FILENAME)


def docx_dir(work_dir: str) -> str:
    return os.path.join(work_dir, "docx")


def preview_dir(work_dir: str) -> str:
    return os.path.join(work_dir, "preview")


def _unit_to_dict(u) -> dict:
    return {
        "doc_id": getattr(u, "doc_id", 0),
        "doc_type": getattr(u, "doc_type", ""),
        "start_page": getattr(u, "start_page", 0),
        "end_page": getattr(u, "end_page", 0),
        "title": getattr(u, "title", "") or "",
        "catalog_seq": getattr(u, "catalog_seq", None),
        "source_path": getattr(u, "source_path", "") or "",
        "score": float(getattr(u, "score", 0.0) or 0.0),
        "confidence": float(getattr(u, "confidence", 1.0) or 1.0),
    }


def _unit_from_dict(d: dict):
    from pdf_doc_locator import DocumentUnit

    return DocumentUnit(
        doc_id=int(d.get("doc_id", 0)),
        doc_type=str(d.get("doc_type", "")),
        start_page=int(d.get("start_page", 0)),
        end_page=int(d.get("end_page", 0)),
        title=str(d.get("title", "") or ""),
        catalog_seq=d.get("catalog_seq"),
        source_path=str(d.get("source_path", "") or ""),
        score=float(d.get("score", 0.0) or 0.0),
        confidence=float(d.get("confidence", 1.0) or 1.0),
    )


def stabilize_templates(analysis, work_dir: str, log=print) -> Dict[str, str]:
    dest_root = docx_dir(work_dir)
    os.makedirs(dest_root, exist_ok=True)
    stable: Dict[str, str] = {}
    for name, src in (analysis.generated_templates or {}).items():
        if not src or not os.path.isfile(src):
            continue
        dest = os.path.join(dest_root, f"{name}.docx")
        shutil.copy2(src, dest)
        stable[name] = dest
        log(f"       模板落盘: {name}")
    analysis.generated_templates = stable
    return stable


def save_snapshot(work_dir: str, analysis, *, base_name: str, order_mode: str = "catalog", skipped: Optional[List[int]] = None) -> str:
    os.makedirs(work_dir, exist_ok=True)
    fields = dict(analysis.fields or {})
    outcome_warnings = list(getattr(analysis, "outcome_warnings", None) or [])
    if outcome_warnings and "_outcome_warnings" not in fields:
        fields["_outcome_warnings"] = outcome_warnings
    payload = {
        "case_type": analysis.case_type,
        "original_pdf": analysis.original_pdf,
        "base_name": base_name,
        "order_mode": order_mode,
        "fields": fields,
        "generated_templates": dict(analysis.generated_templates or {}),
        "doc_spans": [_unit_to_dict(u) for u in (analysis.doc_spans or [])],
        "found_seqs": sorted(analysis.found_seqs or []),
        "missing_items": list(analysis.missing_items or []),
        "low_confidence_items": list(getattr(analysis, "low_confidence_items", None) or []),
        "template_issues": list(getattr(analysis, "template_issues", None) or []),
        "outcome_warnings": outcome_warnings,
        "skipped": list(skipped or []),
    }
    path = snapshot_path(work_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load_snapshot_data(work_dir: str) -> dict:
    path = snapshot_path(work_dir)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"snapshot not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_analysis(work_dir: str):
    from archive_pipeline import ArchiveAnalysis

    data = load_snapshot_data(work_dir)
    doc_spans = [_unit_from_dict(d) for d in data.get("doc_spans", [])]
    analysis = ArchiveAnalysis(
        case_type=data["case_type"],
        original_pdf=data.get("original_pdf"),
        fields=dict(data.get("fields") or {}),
        generated_templates=dict(data.get("generated_templates") or {}),
        doc_spans=doc_spans,
        found_seqs=set(data.get("found_seqs") or []),
        missing_items=list(data.get("missing_items") or []),
        low_confidence_items=list(data.get("low_confidence_items") or []),
        template_issues=list(data.get("template_issues") or []),
        outcome_warnings=list(data.get("outcome_warnings") or []),
    )
    return analysis, data


def update_snapshot_fields(work_dir: str, fields: dict, generated_templates: Optional[dict] = None) -> None:
    data = load_snapshot_data(work_dir)
    merged = dict(data.get("fields") or {})
    merged.update(fields or {})
    data["fields"] = merged
    if generated_templates is not None:
        data["generated_templates"] = dict(generated_templates)
    with open(snapshot_path(work_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
