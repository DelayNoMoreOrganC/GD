#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-601: WF2+3 切分质量基线脚本

验证兴泰贸易.pdf的文书切分质量：
1. 调用 WF1 摄入和 WF2+3 切分映射
2. 打印每个 unit 的详细信息
3. 汇总页覆盖统计
4. 写入 JSON 报告
5. 验证页覆盖率完整性
"""

import sys
import os
import json
from pathlib import Path

# 设置 UTF-8 编码输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from document_segmenter import DocumentSource, DOC_TYPE_DEFAULT
from archive_pipeline import ingest_archive_sources, segment_and_map_documents
from settings import load_config

def main():
    # 默认测试参数
    test_pdf = Path("test_sample/2014-兴泰贸易.pdf")
    case_type = "civil"

    # 解析命令行参数
    if len(sys.argv) > 1:
        test_pdf = Path(sys.argv[1])
    if len(sys.argv) > 2:
        case_type = sys.argv[2]

    if not test_pdf.exists():
        print(f"❌ 测试文件不存在: {test_pdf}")
        sys.exit(1)

    print(f"📋 T-601 切分质量基线验证")
    print(f"   测试文件: {test_pdf}")
    print(f"   案件类型: {case_type}")
    print()

    # 加载配置
    config = load_config()

    # 准备源文件列表（路径 A：单卷综合）
    doc_sources = [DocumentSource(path=str(test_pdf), doc_type=DOC_TYPE_DEFAULT)]

    # WF1: 统一 OCR 摄入
    print("🔍 WF1: 统一 OCR 摄入...")
    pdf_texts, page_texts_by_path, layout_blocks_by_path, ocr_calls, rapid_pages = ingest_archive_sources(
        doc_sources, config, log=print
    )
    print(f"   OCR 引擎调用: {ocr_calls} 次")
    print(f"   RapidOCR 回退: {rapid_pages} 页")
    print()

    # WF2+WF3: 文书切分与目录映射
    print("📄 WF2+WF3: 文书切分与目录映射...")
    units = segment_and_map_documents(
        doc_sources,
        case_type,
        config,
        pdf_texts_by_path=pdf_texts,
        page_texts_by_path=page_texts_by_path,
        layout_blocks_by_path=layout_blocks_by_path,
        log=print
    )
    print()

    # 打印每个 unit 的详细信息
    print("📋 文书切分详情:")
    print(f"{'doc_id':<6} {'doc_type':<15} {'页段':<12} {'catalog_seq':<12} {'title'}")
    print("-" * 80)

    for unit in units:
        page_range = f"{unit.start_page}-{unit.end_page}"
        catalog_seq_str = str(unit.catalog_seq) if unit.catalog_seq is not None else "None"
        print(f"{unit.doc_id:<6} {unit.doc_type:<15} {page_range:<12} {catalog_seq_str:<12} {unit.title}")

    print()

    # 汇总统计
    total_pages = sum(unit.end_page - unit.start_page + 1 for unit in units)
    expected_pages = len(page_texts_by_path.get(str(test_pdf), []))

    units_count = len(units)
    unknown_count = sum(1 for u in units if u.doc_type == "unknown")
    other_count = sum(1 for u in units if u.doc_type == "other")
    no_catalog_seq = sum(1 for u in units if u.catalog_seq is None)
    match_rate = ((units_count - no_catalog_seq) / units_count * 100) if units_count > 0 else 0

    # T-604: fragmentation 统计（同 doc_type 连续单页 unit 数）
    fragmentation = {}
    for i, u in enumerate(units):
        if u.end_page == u.start_page:  # 单页 unit
            doc_type = u.doc_type
            # 检查是否连续同类型
            if i > 0 and units[i - 1].doc_type == doc_type and units[i - 1].end_page + 1 == u.start_page:
                fragmentation[doc_type] = fragmentation.get(doc_type, 0) + 1

    print("📊 切分统计汇总:")
    print(f"   预期总页数: {expected_pages}")
    print(f"   实际覆盖页数: {total_pages}")
    print(f"   文书单元数: {units_count}")
    print(f"   目录映射匹配率: {match_rate:.1f}% ({units_count - no_catalog_seq}/{units_count})")
    print(f"   unknown 类型: {unknown_count}")
    print(f"   other 类型: {other_count}")
    print(f"   未匹配 catalog_seq: {no_catalog_seq}")
    if fragmentation:
        print(f"   碎片化统计(同类型连续单页): {fragmentation}")
    print()

    # 写入报告
    report = {
        "test_pdf": str(test_pdf),
        "case_type": case_type,
        "expected_pages": expected_pages,
        "pages_covered": total_pages,
        "units_count": units_count,
        "match_rate": round(match_rate, 1),
        "unknown_count": unknown_count,
        "other_count": other_count,
        "no_catalog_seq_count": no_catalog_seq,
        "fragmentation": fragmentation,
        "units": [
            {
                "doc_id": u.doc_id,
                "doc_type": u.doc_type,
                "start_page": u.start_page,
                "end_page": u.end_page,
                "catalog_seq": u.catalog_seq,
                "title": u.title,
                "source_path": u.source_path
            }
            for u in units
        ]
    }

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "wf2_units_report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📝 报告已写入: {report_path}")
    print()

    # 验证覆盖率
    if total_pages == expected_pages:
        print("✅ 验证通过: 页覆盖率 100%")
        sys.exit(0)
    else:
        coverage = (total_pages / expected_pages * 100) if expected_pages > 0 else 0
        print(f"❌ 验证失败: 页覆盖率 {coverage:.1f}% ({total_pages}/{expected_pages})")
        sys.exit(1)

if __name__ == "__main__":
    main()