#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-801: 两阶段流程验证（analyze 与 assemble 分离）

验证两阶段流程可独立调用、可脚本验收：
1. 阶段1：analyze_archive 生成分析结果
2. 阶段2：assemble_archive 拼装完整归档 PDF
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from archive_pipeline import analyze_archive, assemble_archive
from settings import load_config


def test_two_phase_flow():
    """测试两阶段流程：analyze → assemble"""
    print("📋 T-801 两阶段流程验证")
    print("   验证 analyze 与 assemble 可独立调用")
    print()

    config = load_config()
    test_pdf = "test_sample/2014-兴泰贸易.pdf"
    output_pdf = "outputs/_verify_two_phase.pdf"

    # 阶段1：analyze
    print("🔍 阶段1: analyze_archive")
    try:
        analysis = analyze_archive(
            case_type='civil',
            original_pdf=test_pdf,
            config=config,
            log=lambda *args, **kwargs: None  # 静默日志输出
        )

        assert analysis.doc_spans is not None, "analysis.doc_spans 不应为 None"
        assert len(analysis.doc_spans) >= 10, f"doc_spans 应 ≥10，实际 {len(analysis.doc_spans)}"

        print(f"   ✅ analyze 完成:")
        print(f"      doc_spans: {len(analysis.doc_spans)} 份")
        print(f"      missing_items: {len(analysis.missing_items)} 项")
        print(f"      found_seqs: {len(analysis.found_seqs)} 项")
        print()

    except Exception as e:
        print(f"   ❌ analyze 失败: {e}")
        return False

    # 阶段2：assemble（跳过缺失项）
    print("📄 阶段2: assemble_archive")
    try:
        # 获取所有缺失项的 seq
        missing_seqs = [item['seq'] for item in analysis.missing_items]
        print(f"   跳过缺失项: {missing_seqs}")

        result = assemble_archive(
            analysis=analysis,
            output_pdf=output_pdf,
            skipped=missing_seqs,
            config=config,
            log=lambda *args, **kwargs: None  # 静默日志输出
        )

        assert result.success, "assemble 应成功"
        assert result.original_pages_included == 80, f"original_pages_included 应为80，实际 {result.original_pages_included}"

        print(f"   ✅ assemble 完成:")
        print(f"      success: {result.success}")
        print(f"      original_pages_included: {result.original_pages_included}")
        print(f"      output_pdf: {output_pdf}")
        print()

        # 验证输出文件存在
        if os.path.exists(output_pdf):
            file_size = os.path.getsize(output_pdf)
            print(f"   ✅ 输出文件存在: {output_pdf} ({file_size:,} 字节)")
        else:
            print(f"   ❌ 输出文件不存在: {output_pdf}")
            return False

        print()
        print("📊 验证结果:")
        print("   ✅ 两阶段流程可独立调用")
        print("   ✅ analyze 正常生成分析结果（doc_spans≥10）")
        print("   ✅ assemble 正常拼装完整归档 PDF")
        print("   ✅ 页守恒：80/80 页完整包含")
        print("   ✅ 可脚本验收：可自动化验证")
        return True

    except Exception as e:
        print(f"   ❌ assemble 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 设置 UTF-8 编码输出（Windows 兼容）
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    success = test_two_phase_flow()
    sys.exit(0 if success else 1)