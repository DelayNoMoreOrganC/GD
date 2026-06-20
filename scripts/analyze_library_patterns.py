# -*- coding: utf-8 -*-
"""P3 全库切分模式统计：complaint 巨块、信用卡案、seq12/13 缺失。

用法:
  py scripts/analyze_library_patterns.py
  → outputs/_library_patterns.json
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import archive_catalog as ac
import document_segmenter as ds
import pdf_doc_locator as pdl
from archive_pipeline import ingest_archive_sources
from catalog_expectations import (
    SUMMONS_SEQ,
    has_summons_slot,
    usually_absent_seqs,
)
from settings import load_config

COMPLAINT_SEQ = 5
MEGA_BLOCK_PAGES = 40
COURT_RECORD_SEQ = 13


def _silent(*a, **k):
    pass


def analyze_case(path: str, case_type: str, config: dict) -> dict:
    bn = os.path.basename(path)
    is_credit = "信用卡" in bn
    doc = [ds.DocumentSource(path=path, doc_type=ds.DOC_TYPE_DEFAULT)]
    pdf_texts, page_texts, layout_blocks, _, _ = ingest_archive_sources(
        doc, config, log=_silent
    )
    units = pdl.build_units_from_sources(
        doc, case_type, config,
        pdf_texts=pdf_texts,
        page_texts_by_path=page_texts,
        layout_blocks_by_path=layout_blocks,
        log=_silent,
    )
    catalog = ac.get_catalog(case_type)
    auto_seqs = {it.seq for it in catalog if it.source in ("pdf", "mixed")}
    found = {u.catalog_seq for u in units if u.catalog_seq is not None}

    mega = []
    for u in units:
        if u.catalog_seq == COMPLAINT_SEQ:
            n = u.end_page - u.start_page + 1
            if n >= MEGA_BLOCK_PAGES:
                mega.append({"p": f"{u.start_page}-{u.end_page}", "pages": n})

    # seq12：传票(summons) 即出庭通知槽位；seq13 庭审笔录通常无卷
    has_summons = has_summons_slot(found)
    missing_summons = SUMMONS_SEQ in auto_seqs and not has_summons
    court_record_absent = COURT_RECORD_SEQ in auto_seqs and COURT_RECORD_SEQ not in found
    missing_scored = []  # 缺失项跳过，不作结构缺陷统计

    return {
        "case": bn,
        "credit_card": is_credit,
        "pages": len(page_texts.get(path, [])),
        "units": len(units),
        "mega_complaint": mega,
        "has_summons_seq12": has_summons,
        "missing_summons_seq12": missing_summons,
        "court_record_absent_expected": court_record_absent,
        "missing_auto_seqs_scored": missing_scored,
        "found_auto_seqs": sorted(found & auto_seqs),
        "missing_auto_seqs": sorted(auto_seqs - found),
    }


def main():
    config = load_config()
    pdfs = sorted(glob.glob("test_sample/test_file/*.pdf"))
    rows = [analyze_case(p, "civil", config) for p in pdfs if "mock" not in p]

    mega_cases = [r for r in rows if r["mega_complaint"]]
    credit = [r for r in rows if r["credit_card"]]
    miss12 = sum(1 for r in rows if r["missing_summons_seq12"])
    has12 = sum(1 for r in rows if r["has_summons_seq12"])
    absent13 = sum(1 for r in rows if r["court_record_absent_expected"])

    summary = {
        "total": len(rows),
        "mega_complaint_cases": len(mega_cases),
        "credit_card_cases": len(credit),
        "has_summons_seq12": f"{has12}/{len(rows)}",
        "missing_summons_seq12": f"{miss12}/{len(rows)}",
        "court_record_absent": f"{absent13}/{len(rows)} (通常无卷，预期)",
    }

    print("P3 全库模式统计")
    print(f"  案件数: {summary['total']}")
    print(f"  complaint 巨块(>={MEGA_BLOCK_PAGES}p): {summary['mega_complaint_cases']}")
    for r in mega_cases:
        print(f"    - {r['case']}: {r['mega_complaint']}")
    print(f"  信用卡案: {summary['credit_card_cases']} {[r['case'] for r in credit]}")
    print(f"  seq12 传票/出庭通知已识别: {summary['has_summons_seq12']}")
    print(f"  seq12 未识别传票: {summary['missing_summons_seq12']}")
    print(f"  seq13 庭审笔录无卷: {summary['court_record_absent']}")

    dest = "outputs/_library_patterns.json"
    os.makedirs("outputs", exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "cases": rows}, f, ensure_ascii=False, indent=2)
    print(f"\nsaved {dest}")


if __name__ == "__main__":
    main()
