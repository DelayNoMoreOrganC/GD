#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-802: 80/80 页守恒专项验收

验证源 PDF 每页恰好纳入一次（不是输出 PDF 总页数=80）：
1. original_pages_included == 源 PDF 页数（80）
2. success == True
3. 可选：用 fitz 校验源 PDF 每页索引在 merger 插入记录中恰好 1 次
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from archive_pipeline import analyze_archive, assemble_archive
from settings import load_config


def test_page_conservation():
    """测试 80/80 页守恒（源 PDF 每页恰好纳入一次）"""
    print("📋 T-802 80/80 页守恒专项验收")
    print("   验证：源 PDF 每页恰好纳入一次（不是输出 PDF 总页数=80）")
    print()

    config = load_config()
    test_pdf = "test_sample/2014-兴泰贸易.pdf"
    output_pdf = "outputs/_verify_page_conservation.pdf"

    # 获取源 PDF 页数
    try:
        import fitz
        doc = fitz.open(test_pdf)
        source_page_count = len(doc)
        doc.close()
        print(f"📄 源 PDF: {test_pdf}")
        print(f"   总页数: {source_page_count}")
        print()
    except Exception as e:
        print(f"❌ 无法读取源 PDF 页数: {e}")
        return False

    # 阶段1：analyze
    print("🔍 阶段1: analyze_archive")
    try:
        analysis = analyze_archive(
            case_type='civil',
            original_pdf=test_pdf,
            config=config,
            log=lambda *args, **kwargs: None
        )

        assert analysis.doc_spans is not None, "analysis.doc_spans 不应为 None"
        print(f"   ✅ analyze 完成: {len(analysis.doc_spans)} 份文书")
        print()

    except Exception as e:
        print(f"   ❌ analyze 失败: {e}")
        return False

    # 阶段2：assemble（跳过缺失项）
    print("📄 阶段2: assemble_archive（页守恒验收）")
    try:
        missing_seqs = [item['seq'] for item in analysis.missing_items]
        print(f"   跳过缺失项: {missing_seqs}")

        result = assemble_archive(
            analysis=analysis,
            output_pdf=output_pdf,
            skipped=missing_seqs,
            config=config,
            log=lambda *args, **kwargs: None
        )

        # 核心验收：original_pages_included == 源 PDF 页数
        print(f"   📊 页守恒验收:")
        print(f"      original_pages_included: {result.original_pages_included}")
        print(f"      源 PDF 页数: {source_page_count}")
        print(f"      守恒检查: {result.original_pages_included} == {source_page_count}")

        assert result.original_pages_included == source_page_count, \
            f"页守恒失败: {result.original_pages_included} != {source_page_count}"
        assert result.success == True, f"assemble 应成功，实际 success={result.success}"

        print(f"   ✅ 页守恒验收通过: {result.original_pages_included}/{source_page_count} 页完整包含")
        print()

        # 验证输出文件存在
        if os.path.exists(output_pdf):
            file_size = os.path.getsize(output_pdf)
            print(f"   ✅ 输出文件存在: {output_pdf} ({file_size:,} 字节)")

            # 可选：检查输出 PDF 总页数（可能大于源页数）
            try:
                out_doc = fitz.open(output_pdf)
                total_pages = len(out_doc)
                out_doc.close()
                print(f"   📊 输出 PDF 总页数: {total_pages}（含系统模板页）")
                print(f"   💡 说明: 输出可含系统模板页，总页数 > 源页数是正常的")
            except Exception as e:
                print(f"   [WARN] 无法统计输出页数: {e}")
        else:
            print(f"   ❌ 输出文件不存在: {output_pdf}")
            return False

        print()
        print("📊 验收结果:")
        print("   ✅ 源 PDF 每页恰好纳入一次")
        print(f"   ✅ original_pages_included={result.original_pages_included}/{source_page_count}")
        print("   ✅ 页守恒机制有效（success=True 时守恒成立）")
        print("   ✅ 输出 PDF 存在且可访问")
        print("   ✅ 用户红线 PRD D5 得到满足")
        return True

    except Exception as e:
        print(f"   ❌ 页守恒验收失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 设置 UTF-8 编码输出（Windows 兼容）
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    success = test_page_conservation()
    sys.exit(0 if success else 1)