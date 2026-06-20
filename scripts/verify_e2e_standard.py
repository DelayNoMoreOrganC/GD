# -*- coding: utf-8 -*-
"""P2 端到端：test_file 切分 vs standard_sample 槽位/页数对照。

同名配对（当前仅 2019）。比较：
  - 槽位召回（seq 是否出现）
  - 金标准目录声明的各 seq 页数 vs AI 切分页数（仅作参考，物理页不可 1:1）

用法:
  py scripts/verify_e2e_standard.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import archive_catalog as ac
import document_segmenter as ds
import pdf_doc_locator as pdl
from archive_pipeline import ingest_archive_sources
from compare_to_standard import compare_case, _load_standard_catalogs
from settings import load_config


def _page_counts_by_seq(units):
    from collections import defaultdict
    counts = defaultdict(int)
    for u in units:
        if u.catalog_seq is not None:
            counts[u.catalog_seq] += u.end_page - u.start_page + 1
    return dict(counts)


def _standard_page_counts(std_cat: dict) -> dict[int, int]:
    """从金标准目录页码推算相邻 seq 的页数差（成品卷内相对页数）。"""
    items = sorted(std_cat.get("items", []), key=lambda x: x["catalog_page"])
    counts: dict[int, int] = {}
    for i, it in enumerate(items):
        seq = it["seq"]
        start = it["catalog_page"]
        end = items[i + 1]["catalog_page"] - 1 if i + 1 < len(items) else None
        if end is not None and end >= start:
            counts[seq] = end - start + 1
    return counts


def analyze_pair(test_path: str, std_path: str, config: dict) -> dict:
    bn = os.path.basename(test_path)
    std_map = _load_standard_catalogs()
    std_cat = std_map.get(bn)
    if not std_cat:
        return {"case": bn, "error": "无金标准目录"}

    slot = compare_case(test_path, "civil", config, std_cat)

    doc = [ds.DocumentSource(path=test_path, doc_type=ds.DOC_TYPE_DEFAULT)]
    pdf_texts, page_texts, layout_blocks, _, _ = ingest_archive_sources(
        doc, config, log=lambda *a, **k: None
    )
    units = pdl.build_units_from_sources(
        doc, "civil", config,
        pdf_texts=pdf_texts,
        page_texts_by_path=page_texts,
        layout_blocks_by_path=layout_blocks,
        log=lambda *a, **k: None,
    )
    ai_pages = _page_counts_by_seq(units)
    std_pages = _standard_page_counts(std_cat)

    # 成品卷含系统表；test 扫描件无封面/目录 — 仅比较 pdf/mixed 槽相对页数数量级
    catalog = ac.get_catalog("civil")
    auto = {it.seq for it in catalog if it.source in ("pdf", "mixed")}
    page_diff = []
    for seq in sorted(auto & set(std_pages) & set(ai_pages)):
        sp, ap = std_pages[seq], ai_pages[seq]
        if sp > 0:
            ratio = ap / sp
            if ratio < 0.5 or ratio > 2.0:
                page_diff.append({
                    "seq": seq,
                    "standard_pages": sp,
                    "ai_pages": ap,
                    "ratio": round(ratio, 2),
                })

    import fitz
    d1 = fitz.open(std_path)
    std_n = d1.page_count
    d1.close()
    d2 = fitz.open(test_path)
    test_n = d2.page_count
    d2.close()

    return {
        "case": bn,
        "test_pages": test_n,
        "standard_pages": std_n,
        "slot_recall": slot["slot_recall"],
        "missing_seq": slot["missing"],
        "multi_island": slot["multi_island"],
        "ai_pages_by_seq": ai_pages,
        "standard_pages_by_seq": std_pages,
        "page_count_outliers": page_diff,
    }


def main():
    config = load_config()
    if not os.path.isfile("outputs/_standard_catalogs.json"):
        print("请先运行: py scripts/extract_standard_catalog.py")
        sys.exit(1)

    pairs = []
    std_dir = "test_sample/standard_sample"
    test_dir = "test_sample/test_file"
    for name in os.listdir(std_dir):
        if not name.endswith(".pdf"):
            continue
        tp = os.path.join(test_dir, name)
        sp = os.path.join(std_dir, name)
        if os.path.isfile(tp):
            pairs.append((tp, sp))

    if not pairs:
        print("无同名配对")
        sys.exit(1)

    results = []
    failed = False
    for tp, sp in pairs:
        r = analyze_pair(tp, sp, config)
        results.append(r)
        print(f"\n=== {r['case']} ===")
        print(f"  页数: test={r.get('test_pages')} standard={r.get('standard_pages')}")
        print(f"  槽位召回: {r.get('slot_recall')}  missing={r.get('missing_seq')}")
        if r.get("multi_island"):
            print(f"  同seq多段: {r['multi_island']}")
        if r.get("page_count_outliers"):
            print(f"  页数偏差>2x: {r['page_count_outliers']}")
        if r.get("slot_recall", 0) < 0.7 and r.get("missing_seq"):
            # 仅当仍有「已识别槽位」与金标准不一致时才判失败；纯缺失跳过
            failed = True

    out = "outputs/_verify_e2e_standard.json"
    os.makedirs("outputs", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nsaved {out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
