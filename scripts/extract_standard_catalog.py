# -*- coding: utf-8 -*-
"""从 standard_sample 人工归档 PDF 提取卷内目录（seq → 目录页码）。

金标准 PDF 含封面/目录/系统表，目录页多为竖排 OCR 文本；本脚本用
关键词锚点 + 页码数字提取，输出 `outputs/_standard_catalogs.json`。

用法:
  py scripts/extract_standard_catalog.py
  py scripts/extract_standard_catalog.py test_sample/standard_sample/2024-左红贵.pdf
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
import archive_catalog as ac

# 目录页「名称」列常用简称（对齐 bundled 卷内目录_民事.doc）
_TOC_KEYWORDS: dict[int, tuple[str, ...]] = {
    1: ("立案审批表",),
    2: ("发票", "收费凭证"),
    3: ("委托代理合同", "委托合同", "法律服务合同"),
    4: ("授权委托书", "委托书"),
    5: ("起诉状", "上诉状", "答辩状"),
    6: ("阅卷笔录", "谈话笔录", "会见"),
    7: ("证据材料", "证据"),
    8: ("诉讼保全", "证据保全", "先行给付", "执保"),
    9: ("代理意见", "承办律师"),
    10: ("集体讨论", "讨论记录"),
    11: ("代理词", "辩护词"),
    12: ("出庭通知", "传票"),
    13: ("庭审笔录", "开庭笔录"),
    14: ("判决书", "裁定书", "调解书"),
    15: ("执行申请", "执行裁定", "执行相关"),
    16: ("委托人须知", "质量监督卡", "监督卡"),
    17: ("送达材料", "送达清单"),
    18: ("结案报告", "结案"),
}


def _collapse(text: str) -> str:
    """去掉空白与竖排分隔符，便于关键词检索。"""
    t = (text or "").replace("|", "").replace("\n", "")
    return re.sub(r"\s+", "", t)


def _find_toc_page(doc: fitz.Document, max_scan: int = 4) -> int | None:
    for i in range(min(max_scan, doc.page_count)):
        if "目录" in doc[i].get_text("text") or "页码" in doc[i].get_text("text"):
            return i
    return None


def extract_catalog_from_pdf(path: str, case_type: str = "civil") -> dict | None:
    """返回 {case, pages, toc_page, items: [{seq, name_hint, catalog_page, keyword}]}"""
    doc = fitz.open(path)
    toc_idx = _find_toc_page(doc)
    if toc_idx is None:
        doc.close()
        return None
    raw = doc[toc_idx].get_text("text")
    pages = doc.page_count
    doc.close()
    flat = _collapse(raw)
    if "目录" not in flat and "页码" not in flat:
        return None

    catalog = ac.get_catalog(case_type)
    name_by_seq = {it.seq: it.name for it in catalog}
    items = []
    for seq in range(1, 19):
        kws = _TOC_KEYWORDS.get(seq, ())
        found_kw = None
        pos = -1
        for kw in kws:
            p = flat.find(kw)
            if p >= 0 and (pos < 0 or p < pos):
                pos = p
                found_kw = kw
        if pos < 0:
            continue
        before = flat[max(0, pos - 4) : pos]
        m = re.search(r"(\d{1,3})$", before)
        if not m:
            continue
        items.append({
            "seq": seq,
            "name": name_by_seq.get(seq, ""),
            "keyword": found_kw,
            "catalog_page": int(m.group(1)),
        })

    if len(items) < 12:
        return None
    return {
        "case": os.path.basename(path),
        "pages": pages,
        "toc_page": toc_idx,
        "items": items,
    }


def main():
    paths = sys.argv[1:] or sorted(glob.glob("test_sample/standard_sample/*.pdf"))
    out_rows = []
    ok, fail = 0, 0
    for p in paths:
        row = extract_catalog_from_pdf(p)
        if row:
            ok += 1
            out_rows.append(row)
            n = len(row["items"])
            print(f"[OK ] {row['case']}: {n} seq, toc_p={row['toc_page']}")
        else:
            fail += 1
            print(f"[SKIP] {os.path.basename(p)}: 目录未解析")
    dest = "outputs/_standard_catalogs.json"
    os.makedirs("outputs", exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"parsed": ok, "skipped": fail, "catalogs": out_rows}, f, ensure_ascii=False, indent=2)
    print(f"\nsaved {dest} ({ok} parsed, {fail} skipped)")


if __name__ == "__main__":
    main()
