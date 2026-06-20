#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-1005: 文书排序回归验证

两部分：
1. 检测器自检（快）：_verify_document_order 对乱序必报、对正序不误报，
   防止该函数再次退化为恒不触发（历史 bug：先 sort(doc_id) 再判 doc_id 递减）。
2. 端到端（兴泰贸易）：analyze → assemble，断言
   - 同 (catalog_seq, source_path) 内文书按源页序插入（order_issues 为空）
   - 页守恒 80/80，success=True
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pdf_archive_merger as pam
from archive_pipeline import analyze_archive, assemble_archive
from settings import load_config


class _U:
    def __init__(self, doc_id, seq, start_page, end_page, src=""):
        self.doc_id = doc_id
        self.catalog_seq = seq
        self.start_page = start_page
        self.end_page = end_page
        self.source_path = src


def test_detector():
    print("🔍 部分1: 乱序检测器自检")

    # 正序单源：无 issue
    ok_spans = [_U(0, 7, 0, 2, "a.pdf"), _U(1, 7, 3, 5, "a.pdf"), _U(2, 14, 6, 7, "a.pdf")]
    if pam._verify_document_order(None, ok_spans):
        print("   ❌ 正序被误报为乱序")
        return False

    # 同槽同源页序回退：必须报 1 个 issue
    bad_spans = [_U(0, 7, 5, 6, "a.pdf"), _U(1, 7, 0, 2, "a.pdf")]
    issues = pam._verify_document_order(None, bad_spans)
    if len(issues) != 1 or issues[0]["seq"] != 7:
        print(f"   ❌ 乱序未被检测: {issues}")
        return False

    # 多源同槽：分组互不干扰，不误报
    multi = [_U(0, 7, 3, 4, "a.pdf"), _U(1, 7, 0, 1, "b.pdf")]
    if pam._verify_document_order(None, multi):
        print("   ❌ 多源分组被误报")
        return False

    print("   ✅ 检测器：正序不误报、乱序必报、多源分组正确")
    print()
    return True


def test_end_to_end():
    print("🔍 部分2: 端到端排序验证（兴泰贸易）")
    config = load_config()
    test_pdf = "test_sample/test_file/2014-兴泰贸易.pdf"
    output_pdf = "outputs/_verify_doc_order.pdf"
    silent = lambda *a, **k: None

    try:
        analysis = analyze_archive(
            case_type="civil", original_pdf=test_pdf, config=config, log=silent
        )
    except Exception as e:
        print(f"   ❌ analyze 失败: {e}")
        return False

    # doc_spans 自身排序：同 (seq, source) 内按源页序
    pre_issues = pam._verify_document_order(None, analysis.doc_spans)
    if pre_issues:
        print("   ❌ analyze 产出的 doc_spans 存在同槽页序回退:")
        for it in pre_issues:
            print(f"      - {it['description']}")
        return False
    print(f"   ✅ doc_spans 同槽页序正确（{len(analysis.doc_spans)} 份，无回退）")

    missing_seqs = [item["seq"] for item in analysis.missing_items]
    try:
        result = assemble_archive(
            analysis=analysis, output_pdf=output_pdf,
            skipped=missing_seqs, config=config, log=silent,
        )
    except Exception as e:
        print(f"   ❌ assemble 失败: {e}")
        return False

    if not result.success:
        print("   ❌ assemble success=False")
        return False
    if result.original_pages_included != 80:
        print(f"   ❌ 页守恒失败: {result.original_pages_included}/80")
        return False
    if result.order_issues:
        print("   ❌ result.order_issues 非空:")
        for it in result.order_issues:
            print(f"      - {it['description']}")
        return False

    print(f"   ✅ 页守恒 80/80，success=True，order_issues 为空")
    if os.path.exists(output_pdf):
        print(f"   ✅ 输出: {output_pdf} ({os.path.getsize(output_pdf):,} 字节)")
    print()
    return True


def main():
    print("📋 T-1005 文书排序回归验证")
    print()
    ok = test_detector()
    if not ok:
        return False
    ok = test_end_to_end()
    if not ok:
        return False
    print("📊 验证结果:")
    print("   ✅ 乱序检测器有效（防退化）")
    print("   ✅ 同槽内文书按源页序插入")
    print("   ✅ 页守恒 80/80")
    return True


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    sys.exit(0 if main() else 1)
