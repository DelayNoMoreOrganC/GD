#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-702: WF4 异常保护验证（mock测试）

验证 WF4 全部失败时，analyze_archive 仍能正常返回 doc_spans 和 missing_items：
1. 用 mock 让 extract_fields_auto 抛异常
2. 用 mock 让 generate_system_templates 返回 {}
3. 调用 analyze_archive，断言 doc_spans≥10，missing_items 非None，不抛异常
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from archive_pipeline import analyze_archive, extract_fields_from_text, generate_system_templates
from settings import load_config


def test_wf4_isolation():
    """测试 WF4 完全失败时的隔离性"""
    print("📋 T-702 WF4 异常保护验证")
    print("   模拟场景：extract_fields_auto 抛异常 + generate_system_templates 返回 {}")
    print()

    config = load_config()
    test_pdf = "test_sample/2014-兴泰贸易.pdf"

    # Mock extract_fields_auto 抛异常
    with patch('archive_pipeline.extract_fields_auto') as mock_extract:
        mock_extract.side_effect = Exception("Mock: LLM API 失败")

        # Mock generate_system_templates 返回空字典
        with patch('archive_pipeline.generate_system_templates') as mock_templates:
            mock_templates.return_value = {}

            try:
                # 调用 analyze_archive
                result = analyze_archive(
                    case_type='civil',
                    original_pdf=test_pdf,
                    config=config,
                    log=lambda *args, **kwargs: None  # 静默日志输出
                )

                # 断言核心结果不受影响
                assert result.doc_spans is not None, "doc_spans 不应为 None"
                assert len(result.doc_spans) >= 10, f"doc_spans 应 ≥10，实际 {len(result.doc_spans)}"
                assert result.missing_items is not None, "missing_items 不应为 None"
                assert result.generated_templates == {}, "generated_templates 应为空字典"

                print(f"✅ 测试通过:")
                print(f"   doc_spans: {len(result.doc_spans)} 份")
                print(f"   missing_items: {len(result.missing_items)} 项")
                print(f"   generated_templates: {len(result.generated_templates)} 份")
                print()
                print("📊 验证结果:")
                print("   ✅ WF4 完全失败时，WF2/3 核心结果不受影响")
                print("   ✅ doc_spans 正常生成（≥10 份文书）")
                print("   ✅ missing_items 正常计算")
                print("   ✅ 不抛异常，不中断流程")
                return True

            except Exception as e:
                print(f"❌ 测试失败: {e}")
                print(f"   WF4 异常时 analyze_archive 应仍能返回有效结果")
                return False


if __name__ == "__main__":
    # 设置 UTF-8 编码输出（Windows 兼容）
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    success = test_wf4_isolation()
    sys.exit(0 if success else 1)