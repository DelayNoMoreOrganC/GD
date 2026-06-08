#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量案件归档处理"""

import json
import os
from datetime import datetime
from typing import Callable, List, Optional

from archive_pipeline import process_archive, process_archive_sources
from document_segmenter import DocumentSource


def process_batch(
    pdf_paths: List[str],
    max_pages=None,
    log=print,
    on_progress: Optional[Callable[[dict], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    output_options=None,
) -> dict:
    """
    批量处理多个案件 PDF（每案 1 个 PDF）。
    输出：outputs/batch_{timestamp}/{序号}_{stem}_{子时间戳}/
    """
    if not pdf_paths:
        return {"success": False, "error": "未选择任何 PDF"}

    from app_paths import get_outputs_dir

    batch_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_root = os.path.join(get_outputs_dir(), f"batch_{batch_stamp}")
    os.makedirs(batch_root, exist_ok=True)

    results = []
    ok_count = 0

    for i, pdf_path in enumerate(pdf_paths, 1):
        if cancel_check and cancel_check():
            log(f"[BATCH] 用户取消，跳过剩余 {len(pdf_paths) - i + 1} 个")
            break

        stem = os.path.splitext(os.path.basename(pdf_path))[0]
        sub_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        case_dir = os.path.join(batch_root, f"{i:02d}_{stem}_{sub_stamp}")

        item = {
            "index": i,
            "pdf": pdf_path,
            "status": "running",
            "output_dir": case_dir,
        }
        if on_progress:
            on_progress(item)

        log(f"\n[BATCH {i}/{len(pdf_paths)}] {os.path.basename(pdf_path)}")
        if not os.path.isfile(pdf_path):
            item.update({"status": "failed", "error": "文件不存在"})
            results.append(item)
            if on_progress:
                on_progress(item)
            continue

        r = process_archive(
            pdf_path,
            output_dir=case_dir,
            max_pages=max_pages,
            log=log,
            output_options=output_options,
        )
        if r.get("success"):
            ok_count += 1
            item.update(
                {
                    "status": "success",
                    "field_count": r.get("field_count"),
                    "verify_issues": r.get("verify_issues", []),
                    "layout_issues": r.get("layout_issues", []),
                }
            )
        else:
            item.update({"status": "failed", "error": r.get("error")})
        results.append(item)
        if on_progress:
            on_progress(item)

    summary_path = os.path.join(batch_root, "batch_summary.json")
    summary = {
        "batch_id": batch_stamp,
        "batch_root": batch_root,
        "total": len(pdf_paths),
        "success": ok_count,
        "failed": len(results) - ok_count,
        "cases": results,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    log(f"\n[BATCH] 完成 {ok_count}/{len(pdf_paths)}，汇总 → {summary_path}")

    return {
        "success": ok_count > 0,
        "batch_root": batch_root,
        "summary_path": summary_path,
        "ok_count": ok_count,
        "total": len(pdf_paths),
        "cases": results,
    }
