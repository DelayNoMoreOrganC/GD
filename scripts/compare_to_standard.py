# -*- coding: utf-8 -*-
"""将 AI 切分结果与 standard_sample 金标准目录做「槽位级」对照。

test_file（原始扫描）与 standard_sample（含系统表+目录的成品卷）页码不对齐，
故不做逐页 type_acc，而比较：
  - 各 seq 是否在切分结果中出现
  - 同一 seq 的段数（孤岛数）是否一致
  - seq 升序是否满足

仅支持同名配对（当前仅 2019-佛山金百纳贸易有限公司）。

用法:
  py scripts/compare_to_standard.py
  py scripts/compare_to_standard.py test_sample/test_file/2019-佛山金百纳贸易有限公司.pdf
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import archive_catalog as ac
import document_segmenter as ds
import pdf_doc_locator as pdl
from archive_pipeline import ingest_archive_sources
from settings import load_config

from catalog_expectations import required_auto_seqs, slot_recall_stats, usually_absent_seqs
TEST_DIR = "test_sample/test_file"
CATALOG_JSON = "outputs/_standard_catalogs.json"


def _silent(*a, **k):
    pass


def _load_standard_catalogs():
    if not os.path.isfile(CATALOG_JSON):
        return {}
    with open(CATALOG_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {row["case"]: row for row in data.get("catalogs", [])}


def _seq_spans(units):
    from collections import defaultdict

    spans = defaultdict(list)
    for u in units:
        if u.catalog_seq is not None:
            spans[u.catalog_seq].append((u.start_page, u.end_page))
    for seq in spans:
        spans[seq].sort()
    return dict(spans)


def compare_case(test_path: str, case_type: str, config: dict, std_cat: dict) -> dict:
    bn = os.path.basename(test_path)
    std_items = {it["seq"] for it in std_cat.get("items", [])}
    auto_seqs = {
        it.seq
        for it in ac.get_catalog(case_type)
        if it.source in ("pdf", "mixed") and it.seq >= 2
    }
    # 金标准目录里出现且为 pdf/mixed 的 seq；排除通常无卷项（如 seq13 庭审笔录）
    ref_seqs = std_items & required_auto_seqs(case_type)
    ref_optional = std_items & usually_absent_seqs(case_type)

    doc = [ds.DocumentSource(path=test_path, doc_type=ds.DOC_TYPE_DEFAULT)]
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
    got_spans = _seq_spans(units)
    got_seqs = set(got_spans.keys())

    recall = slot_recall_stats(ref_seqs, got_seqs)
    missing = recall["skipped_missing"]
    extra = sorted((got_seqs - ref_seqs) & auto_seqs)
    matched = recall["matched"]

    # 段数：金标准目录每项 1 行 ≈ 1 段；AI 切分同 seq 可多段（孤岛）
    multi_island = {
        seq: len(got_spans[seq])
        for seq in matched
        if len(got_spans[seq]) > 1
    }

    return {
        "case": bn,
        "ref_seqs": sorted(ref_seqs),
        "ref_optional_absent": sorted(ref_optional),
        "got_seqs": sorted(got_seqs),
        "matched": matched,
        "missing": missing,
        "skipped_missing": missing,
        "extra": extra,
        "multi_island": multi_island,
        "slot_recall": recall["slot_recall"],
        "spans": {str(k): v for k, v in sorted(got_spans.items())},
    }


def main():
    config = load_config()
    std_map = _load_standard_catalogs()
    if not std_map:
        print(f"请先运行: py scripts/extract_standard_catalog.py")
        sys.exit(1)

    if len(sys.argv) > 1:
        tests = [sys.argv[1]]
    else:
        tests = [
            os.path.join(TEST_DIR, name)
            for name in std_map
            if os.path.isfile(os.path.join(TEST_DIR, name))
        ]

    if not tests:
        print("无同名 test_file ↔ standard_sample 配对案件")
        sys.exit(1)

    results = []
    for tp in tests:
        bn = os.path.basename(tp)
        if bn not in std_map:
            print(f"[SKIP] {bn}: 无金标准目录")
            continue
        if not os.path.isfile(tp):
            print(f"[SKIP] {bn}: test_file 不存在")
            continue
        r = compare_case(tp, "civil", config, std_map[bn])
        results.append(r)
        print(f"\n=== {bn} ===")
        print(f"  槽位召回 slot_recall={r['slot_recall']}  matched={len(r['matched'])}/{len(r['ref_seqs'])}")
        if r["missing"]:
            print(f"  缺失 seq: {r['missing']}")
        if r["extra"]:
            print(f"  多余 seq: {r['extra']}")
        if r["multi_island"]:
            print(f"  同 seq 多段: {r['multi_island']}")

    out = "outputs/_compare_standard.json"
    os.makedirs("outputs", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
