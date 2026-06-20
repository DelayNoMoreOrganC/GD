#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试模式使用示例"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import load_config
from pdf_doc_locator import build_units_from_sources
from document_segmenter import DocumentSource

def main():
    print("=== 启用调试模式演示 ===")

    # 加载配置并启用调试
    config = load_config()
    config.setdefault("debug", {})["match_details"] = True

    # 测试文书定位
    sources = [DocumentSource(path='test_sample/2014-兴泰贸易.pdf', doc_type='default')]

    print("开始文书定位（调试模式已启用）...")
    units = build_units_from_sources(sources, 'civil', config)

    print("\n=== 文书定位结果 ===")
    for unit in units:
        print(f'doc_id={unit.doc_id}, type={unit.doc_type}, '
              f'pages={unit.start_page}-{unit.end_page}, conf={unit.confidence:.3f}')

    print("\n=== 调试信息 ===")
    print("详细调试日志已保存到 outputs/debug_logs/ 目录")
    print("可以使用 JSON 查看器分析匹配过程")

if __name__ == "__main__":
    main()