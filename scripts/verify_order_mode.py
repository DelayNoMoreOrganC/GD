#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-1104: 归档正文排序模式验证（catalog vs original）

直接调用 build_full_archive（构造合成 doc_spans 指向真实测试 PDF，免 OCR）：
- 两份源：A=兴泰贸易(80p, judgment→seq14)，B=金百纳(99p, contract→seq3)
- 源原始顺序：A(seq14) → B(seq3)；目录顺序：seq3 → seq14
- catalog 模式：正文按 seq 升序（先 seq3 后 seq14）
- original 模式：正文保持源页序（先 seq14 后 seq3）
两模式均须页守恒 179/179、success=True。
"""

import re
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pdf_archive_merger as pam
from pdf_doc_locator import DocumentUnit

PDF_A = "test_sample/2014-兴泰贸易.pdf"
PDF_B = "test_sample/2019-佛山金百纳贸易有限公司.pdf"


def _build_spans():
    na = pam._pdf_page_count(PDF_A)
    nb = pam._pdf_page_count(PDF_B)
    spans = [
        DocumentUnit(doc_id=0, doc_type="judgment", start_page=0, end_page=na - 1,
                     title="民事判决书", catalog_seq=14, source_path=PDF_A),
        DocumentUnit(doc_id=1, doc_type="contract", start_page=0, end_page=nb - 1,
                     title="委托代理合同", catalog_seq=3, source_path=PDF_B),
    ]
    return spans, na + nb


def _content_seq_order(log_lines):
    """从日志解析实际插入正文的 seq 顺序（仅取带内容的目录项）。

    catalog 模式：'目录 N: 名称' 头行 + 后续 '→ 源描述' 行分离；
    original 模式：'目录 N: 文件: 类型 (页..)' 单行即含内容。
    """
    order = []
    cur_seq = None
    for line in log_lines:
        m = re.search(r"目录 (\d+):", line)
        if m:
            cur_seq = int(m.group(1))
            # original 模式：头行自带内容
            if (".pdf" in line or "页" in line) and "缺失" not in line:
                if cur_seq not in order:
                    order.append(cur_seq)
            continue
        # catalog 模式：内容描述出现在头行之后
        if cur_seq is not None and ("→" in line) and ("缺失" not in line) and ("留空" not in line):
            if (".pdf" in line or "页" in line or "用户补充" in line or "已识别" in line):
                if cur_seq not in order:
                    order.append(cur_seq)
    return order


def _run(order_mode):
    spans, expected = _build_spans()
    logs = []
    result = pam.build_full_archive(
        case_type="civil",
        original_pdf=PDF_A,
        generated_templates={},
        doc_spans=spans,
        supplements={},
        skipped=[],
        output_pdf=f"outputs/_verify_order_{order_mode}.pdf",
        log=lambda *a, **k: logs.append(" ".join(str(x) for x in a)),
        order_mode=order_mode,
    )
    return result, expected, _content_seq_order(logs)


def main():
    print("📋 T-1104 归档正文排序模式验证")
    print()

    ok = True

    print("🔍 catalog 模式（按目录顺序）")
    res_c, expected, order_c = _run("catalog")
    print(f"   页守恒: {res_c.original_pages_included}/{expected}, success={res_c.success}")
    print(f"   正文 seq 插入顺序: {order_c}")
    if not res_c.success or res_c.original_pages_included != expected:
        print("   ❌ catalog 模式页守恒失败")
        ok = False
    # 目录顺序：seq3 在 seq14 之前
    if order_c.index(3) > order_c.index(14):
        print("   ❌ catalog 模式 seq 顺序错误（应 seq3 先于 seq14）")
        ok = False
    else:
        print("   ✅ catalog 模式：seq3 先于 seq14（目录序）")
    print()

    print("🔍 original 模式（保持源 PDF 页序）")
    res_o, expected, order_o = _run("original")
    print(f"   页守恒: {res_o.original_pages_included}/{expected}, success={res_o.success}")
    print(f"   正文 seq 插入顺序: {order_o}")
    if not res_o.success or res_o.original_pages_included != expected:
        print("   ❌ original 模式页守恒失败")
        ok = False
    # 源顺序：A(seq14) 先于 B(seq3)
    if order_o.index(14) > order_o.index(3):
        print("   ❌ original 模式顺序错误（应 seq14 先于 seq3，即源页序）")
        ok = False
    else:
        print("   ✅ original 模式：seq14 先于 seq3（源页序）")
    print()

    print("📊 验证结果:")
    if ok:
        print("   ✅ 两种排序模式均页守恒")
        print("   ✅ catalog 按目录序、original 按源页序，行为可区分")
    else:
        print("   ❌ 排序模式验证未通过")
    return ok


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    sys.exit(0 if main() else 1)
