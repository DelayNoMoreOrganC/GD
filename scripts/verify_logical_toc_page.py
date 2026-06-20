#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证：逻辑命中项（已识别但页面在其他目录项插入）能回填卷内目录页码。

构造一个证据(evidence)文书，但其 catalog_seq 指向 seq8（mixed），
则 seq7（证据材料）无直接匹配 → 逻辑命中 → 应回填指向 seq8 的实际页码。
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz
import pdf_archive_merger as pam
import catalog_toc
from pdf_doc_locator import DocumentUnit

WORK = "outputs/_verify_logical"
os.makedirs(WORK, exist_ok=True)


def _make_pdf(path, n, label):
    d = fitz.open()
    for i in range(n):
        p = d.new_page()
        p.insert_text((72, 72), f"{label} page {i}")
    d.save(path)
    d.close()


src = os.path.join(WORK, "src.pdf")
_make_pdf(src, 6, "evi")

# evidence 文书放在 seq8（mixed 槽），seq7（evidence）将无直接匹配
units = [
    DocumentUnit(doc_id=0, doc_type="evidence", start_page=0, end_page=5,
                 title="证据材料", catalog_seq=8, confidence=0.9),
]
for u in units:
    u.source_path = src

captured = {}
orig = catalog_toc.compute_display_pages
def spy(body_starts, cover_end_idx, toc_pages=1):
    captured["body_starts"] = dict(body_starts)
    return orig(body_starts, cover_end_idx, toc_pages)
catalog_toc.compute_display_pages = spy

silent = lambda *a, **k: None
res = pam.build_full_archive(
    case_type="civil",
    original_pdf=src,
    generated_templates={},
    doc_spans=units,
    supplements={},
    skipped=[],
    output_pdf=os.path.join(WORK, "out.pdf"),
    log=silent,
)

bs = captured.get("body_starts", {})
print("success:", res.success)
print("body_starts:", bs)
print("sources seq7:", res.sources.get(7))
print("sources seq8:", res.sources.get(8))

assert res.success, "归档应成功"
assert 8 in bs, "seq8 应有页码（evidence 实际插入位置）"
assert 7 in bs, "seq7（证据材料）应回填页码（逻辑命中）"
assert bs[7] == bs[8], f"seq7 页码应指向 evidence 实际位置 seq8: {bs[7]} vs {bs[8]}"
print("\n[PASS] 逻辑命中项卷内目录页码回填正确：seq7 -> body_idx", bs[7])
