#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-1302: CLI 补充上传与多文件补充验证

两部分（均免 OCR，秒级）：
1. CLI 解析：run_archive.parse_supplements 正确解析 SEQ:FILE，忽略非法/缺失项。
2. 多文件补充插入：build_full_archive 对同一 seq 的多个补充文件全部插入，
   且源 PDF 页守恒不受影响（验证 T-1204 合并器不再 break-after-first）。
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import fitz
import pdf_archive_merger as pam
from pdf_doc_locator import DocumentUnit
import run_archive

PDF_A = "test_sample/2014-兴泰贸易.pdf"


def _make_tiny_pdf(path, pages=1):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=300, height=300)
    doc.save(path)
    doc.close()


def test_cli_parse():
    print("🔍 部分1: CLI --supplement 解析")
    os.makedirs("outputs", exist_ok=True)
    tmp = "outputs/_supp_parse.pdf"
    _make_tiny_pdf(tmp)
    parsed = run_archive.parse_supplements(
        [f"2:{tmp}", f"2:{tmp}", f"7:{tmp}", "bad", "9:does_not_exist.pdf", f"x:{tmp}"]
    )
    os.remove(tmp)
    expected = {2: [tmp, tmp], 7: [tmp]}
    if parsed != expected:
        print(f"   ❌ 解析结果不符: {parsed}")
        return False
    print(f"   ✅ 解析正确（同 seq 可多文件、非法项被忽略）: {parsed}")
    print()
    return True


def test_multi_supplement_insert():
    print("🔍 部分2: 多文件补充插入 + 页守恒")
    na = pam._pdf_page_count(PDF_A)
    spans = [DocumentUnit(doc_id=0, doc_type="judgment", start_page=0,
                          end_page=na - 1, catalog_seq=14, source_path=PDF_A)]

    supp1 = "outputs/_supp1.pdf"
    supp2 = "outputs/_supp2.pdf"
    _make_tiny_pdf(supp1, pages=2)
    _make_tiny_pdf(supp2, pages=3)

    logs = []
    result = pam.build_full_archive(
        case_type="civil",
        original_pdf=PDF_A,
        generated_templates={},
        doc_spans=spans,
        supplements={2: [supp1, supp2]},  # 同一 seq 两个文件
        skipped=[s for s in range(0, 18) if s not in (2, 14)],
        output_pdf="outputs/_verify_cli_supplement.pdf",
        log=lambda *a, **k: logs.append(" ".join(str(x) for x in a)),
    )

    ok = True
    if not result.success:
        print("   ❌ assemble success=False")
        ok = False
    if result.original_pages_included != na:
        print(f"   ❌ 源页守恒失败: {result.original_pages_included}/{na}")
        ok = False

    # seq2 描述应包含两个补充文件
    seq2_desc = result.sources.get(2, "")
    if "_supp1.pdf" not in seq2_desc or "_supp2.pdf" not in seq2_desc:
        print(f"   ❌ seq2 未包含全部补充文件: {seq2_desc}")
        ok = False
    else:
        print(f"   ✅ seq2 两个补充文件均插入: {seq2_desc}")

    # 输出页数应 = TOC + 源80 + 补充(2+3)=5（无系统模板）
    out_pages = pam._pdf_page_count("outputs/_verify_cli_supplement.pdf")
    print(f"   源页守恒: {result.original_pages_included}/{na}, 输出 {out_pages} 页")
    # 补充 5 页必须计入（80 源 + 5 补充 + 目录页）
    if out_pages < na + 5:
        print(f"   ❌ 输出页数偏少，疑似补充文件未全部插入: {out_pages}")
        ok = False
    else:
        print(f"   ✅ 补充 5 页已计入输出")

    for p in (supp1, supp2):
        try:
            os.remove(p)
        except OSError:
            pass

    print()
    return ok


def main():
    print("📋 T-1302 CLI 补充上传与多文件补充验证")
    print()
    if not test_cli_parse():
        return False
    if not test_multi_supplement_insert():
        return False
    print("📊 验证结果:")
    print("   ✅ CLI --supplement 解析正确")
    print("   ✅ 同 seq 多文件补充全部插入，源页守恒不变")
    return True


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    sys.exit(0 if main() else 1)
