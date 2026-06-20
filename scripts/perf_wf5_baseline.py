#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WF1+WF2+WF5 端到端性能基线：耗时、OCR 次数、页覆盖、assemble 耗时"""

import json
import os
import sys
import time

# 设置 UTF-8 编码输出（Windows 兼容）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_PDF = os.path.join(ROOT, "test_sample", "2014-兴泰贸易.pdf")
OUTPUT_JSON = os.path.join(ROOT, "outputs", "wf5_baseline.json")


def run_full_baseline(pdf_path: str, case_type: str = "civil") -> dict:
    """端到端性能基线：analyze (WF1+WF2+WF3+WF4) + assemble (WF5)"""
    from archive_ocr import get_pdf_page_count
    from archive_pipeline import analyze_archive, assemble_archive
    from settings import load_config

    config = load_config()
    expected_pages = get_pdf_page_count(pdf_path)

    # 阶段1：analyze (WF1+WF2+WF3+WF4)
    print(f"📊 WF5 性能基线: {pdf_path}")
    print()

    t0 = time.perf_counter()
    analysis = analyze_archive(
        case_type=case_type,
        original_pdf=pdf_path,
        config=config,
        log=print
    )
    t1 = time.perf_counter()

    analyze_seconds = round(t1 - t0, 2)

    # 阶段2：assemble (WF5)
    output_pdf = os.path.join(ROOT, "outputs", "_baseline_full_archive.pdf")
    missing_seqs = [item['seq'] for item in analysis.missing_items]

    t2 = time.perf_counter()
    result = assemble_archive(
        analysis=analysis,
        output_pdf=output_pdf,
        skipped=missing_seqs,
        config=config,
        log=print
    )
    t3 = time.perf_counter()

    wf5_seconds = round(t3 - t2, 2)
    total_seconds = round(t3 - t0, 2)

    # 统计分析结果
    units_count = len(analysis.doc_spans)
    covered = sum(u.end_page - u.start_page + 1 for u in analysis.doc_spans if u.source_path == pdf_path or not u.source_path)

    report = {
        "pdf": pdf_path,
        "case_type": case_type,
        "expected_pages": expected_pages,
        "units_count": units_count,
        "pages_covered_by_units": covered,
        "missing_items_count": len(analysis.missing_items),
        "original_pages_included": result.original_pages_included,
        "page_count": result.page_count if result.success else 0,
        "success": result.success,
        # 性能指标
        "analyze_seconds": analyze_seconds,  # WF1+WF2+WF3+WF4
        "wf5_seconds": wf5_seconds,  # WF5 assemble
        "total_seconds": total_seconds,  # 端到端
        # 兼容旧字段
        "wf1_seconds": analyze_seconds,  # 向后兼容
        "wf2_seconds": 0,  # 不再单独统计，已合并到 analyze
    }
    return report


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    if not os.path.isfile(pdf):
        print(f"[FAIL] PDF 不存在: {pdf}")
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

    try:
        report = run_full_baseline(pdf)

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print()
        print("=" * 60)
        print("📊 性能基线报告:")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"写入: {OUTPUT_JSON}")
        print()

        # 验证关键指标
        if report["original_pages_included"] == report["expected_pages"]:
            print(f"✅ 页守恒: {report['original_pages_included']}/{report['expected_pages']}")
        else:
            print(f"⚠️  页守恒: {report['original_pages_included']}/{report['expected_pages']}")

        if report["success"]:
            print(f"✅ assemble 成功")
        else:
            print(f"❌ assemble 失败")

        print()
        print(f"⏱️  性能统计:")
        print(f"   analyze (WF1~4): {report['analyze_seconds']}s")
        print(f"   assemble (WF5): {report['wf5_seconds']}s")
        print(f"   端到端: {report['total_seconds']}s")

        sys.exit(0)

    except Exception as e:
        print(f"❌ 基线测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()