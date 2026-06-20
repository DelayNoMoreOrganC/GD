#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目录槽材料提取验收 — 仅输出按目录重排的原 PDF 材料（无系统模板）

用法:
  py scripts/verify_catalog_extract.py [pdf] [case_type]
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from document_segmenter import DocumentSource, DOC_TYPE_DEFAULT
from archive_pipeline import ingest_archive_sources, segment_and_map_documents
from pdf_archive_merger import build_catalog_content_pdf
from settings import load_config
import archive_catalog as ac


def main():
    test_pdf = Path("test_sample/2014-兴泰贸易.pdf")
    case_type = "civil"
    if len(sys.argv) > 1:
        test_pdf = Path(sys.argv[1])
    if len(sys.argv) > 2:
        case_type = sys.argv[2]

    if not test_pdf.exists():
        print(f"❌ 测试文件不存在: {test_pdf}")
        sys.exit(1)

    print("📋 目录槽材料提取验收")
    print(f"   测试文件: {test_pdf}")
    print(f"   案件类型: {case_type}")
    print()

    config = load_config()
    sources = [DocumentSource(path=str(test_pdf), doc_type=DOC_TYPE_DEFAULT)]

    print("🔍 WF1: OCR 摄入...")
    pdf_texts, page_texts_by_path, layout_blocks_by_path, ocr_calls, _ = (
        ingest_archive_sources(sources, config, log=print)
    )
    expected_pages = len(page_texts_by_path.get(str(test_pdf), []))
    print(f"   页数: {expected_pages}, OCR 调用: {ocr_calls}")
    print()

    print("📄 WF2+3: 目录槽切分...")
    units = segment_and_map_documents(
        sources,
        case_type,
        config,
        pdf_texts_by_path=pdf_texts,
        page_texts_by_path=page_texts_by_path,
        layout_blocks_by_path=layout_blocks_by_path,
        log=print,
    )
    print()

    catalog = ac.get_catalog(case_type)
    catalog_names = {item.seq: item.name for item in catalog}

    print("📋 目录槽段明细:")
    print(f"{'doc_id':<6} {'seq':<4} {'页段':<12} {'页数':<6} 名称")
    print("-" * 70)
    for u in units:
        pages = u.end_page - u.start_page + 1
        name = catalog_names.get(u.catalog_seq, "?")
        print(f"{u.doc_id:<6} {u.catalog_seq:<4} {u.start_page}-{u.end_page:<8} {pages:<6} {name}")
    print()

    out_pdf = Path("outputs") / "catalog_extract_test.pdf"
    print("📦 生成目录材料 PDF（无系统模板）...")
    ok, out_pages, included = build_catalog_content_pdf(
        case_type,
        str(test_pdf),
        units,
        str(out_pdf),
        log=print,
    )
    print()

    report = {
        "test_pdf": str(test_pdf),
        "case_type": case_type,
        "expected_pages": expected_pages,
        "units_count": len(units),
        "output_pdf": str(out_pdf),
        "output_pages": out_pages,
        "pages_included": included,
        "units": [
            {
                "doc_id": u.doc_id,
                "catalog_seq": u.catalog_seq,
                "start_page": u.start_page,
                "end_page": u.end_page,
                "name": catalog_names.get(u.catalog_seq, ""),
            }
            for u in units
        ],
    }
    report_path = Path("outputs") / "catalog_extract_report.json"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📝 报告: {report_path}")
    print(f"📄 输出: {out_pdf} ({out_pages} 页)")
    print()

    if ok and included == expected_pages:
        print(f"✅ 通过: 原 PDF {included}/{expected_pages} 页全部按目录重排输出")
        sys.exit(0)

    print(f"❌ 失败: 页守恒 {included}/{expected_pages}, success={ok}")
    sys.exit(1)


if __name__ == "__main__":
    main()
