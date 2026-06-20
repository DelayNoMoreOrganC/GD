#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WF1+WF2 性能基线：耗时、OCR 次数、页覆盖（兴泰贸易等）"""

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_PDF = os.path.join(ROOT, "test_sample", "2014-兴泰贸易.pdf")
OUTPUT_JSON = os.path.join(ROOT, "outputs", "wf_baseline.json")


def run_baseline(pdf_path: str, case_type: str = "civil") -> dict:
    from archive_ocr import get_pdf_page_count
    from archive_pipeline import ingest_archive_sources, segment_and_map_documents
    from document_segmenter import DocumentSource, DOC_TYPE_DEFAULT
    from settings import load_config

    config = load_config()
    expected_pages = get_pdf_page_count(pdf_path)
    sources = [DocumentSource(path=pdf_path, doc_type=DOC_TYPE_DEFAULT)]

    t0 = time.perf_counter()
    pdf_texts, page_texts_map, layout_map, ocr_calls, rapid_pages = ingest_archive_sources(
        sources, config, log=print
    )
    t1 = time.perf_counter()

    units = segment_and_map_documents(
        sources,
        case_type,
        config,
        pdf_texts_by_path=pdf_texts,
        page_texts_by_path=page_texts_map,
        layout_blocks_by_path=layout_map,
        log=print,
    )
    t2 = time.perf_counter()

    covered = 0
    for u in units:
        if getattr(u, "source_path", "") == pdf_path or not getattr(u, "source_path", ""):
            covered += u.end_page - u.start_page + 1

    page_texts = page_texts_map.get(pdf_path) or []
    page_text_nonempty = sum(1 for p in page_texts if (p or "").strip())

    report = {
        "pdf": pdf_path,
        "case_type": case_type,
        "expected_pages": expected_pages,
        "units_count": len(units),
        "pages_covered_by_units": covered,
        "page_texts_count": len(page_texts),
        "page_text_nonempty": page_text_nonempty,
        "ocr_engine_calls": ocr_calls,
        "rapidocr_fallback_pages": rapid_pages,
        "layout_blocks": len(layout_map.get(pdf_path) or []),
        "full_text_chars": len(pdf_texts.get(pdf_path) or ""),
        "wf1_seconds": round(t1 - t0, 2),
        "wf2_seconds": round(t2 - t1, 2),
        "total_seconds": round(t2 - t0, 2),
        "page_conservation_ok": covered == expected_pages,
    }
    return report


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    if not os.path.isfile(pdf):
        print(f"[FAIL] PDF 不存在: {pdf}")
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    print(f"WF baseline: {pdf}")
    report = run_baseline(pdf)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"写入: {OUTPUT_JSON}")

    if not report["page_conservation_ok"]:
        print(
            f"[WARN] 页覆盖 {report['pages_covered_by_units']}/"
            f"{report['expected_pages']}"
        )
    if report["ocr_engine_calls"] > 1:
        print(f"[WARN] OCR 引擎调用 {report['ocr_engine_calls']} 次（目标 ≤1 重型 OCR）")

    sys.exit(0)


if __name__ == "__main__":
    main()
