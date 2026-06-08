#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行：一份 PDF → 归档资料；支持批量与分类多文件"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from archive_pipeline import process_archive, process_archive_sources
from batch_processor import process_batch
from document_segmenter import DocumentSource, guess_doc_type_from_filename


def parse_sources(items):
    sources = []
    for item in items:
        if ":" in item:
            path, doc_type = item.rsplit(":", 1)
        else:
            path, doc_type = item, guess_doc_type_from_filename(item)
        sources.append(DocumentSource(path=path.strip(), doc_type=doc_type.strip()))
    return sources


def main():
    parser = argparse.ArgumentParser(description="案件档案一键归档 V3")
    parser.add_argument("pdf", nargs="?", help="单个 PDF 路径")
    parser.add_argument("max_pages", nargs="?", type=int, default=0, help="OCR 最大页数")
    parser.add_argument("--batch", nargs="+", metavar="PDF", help="批量：多个 PDF，每案一个")
    parser.add_argument(
        "--sources",
        nargs="+",
        metavar="FILE:TYPE",
        help="分类多文件，如 判决.pdf:judgment 合同.pdf:contract",
    )
    args = parser.parse_args()

    if args.batch:
        result = process_batch(args.batch, max_pages=args.max_pages or None, log=print)
    elif args.sources:
        sources = parse_sources(args.sources)
        result = process_archive_sources(
            sources, max_pages=args.max_pages or None, log=print
        )
    elif args.pdf:
        result = process_archive(args.pdf, max_pages=args.max_pages or None, log=print)
    else:
        parser.print_help()
        sys.exit(1)

    print()
    print("=" * 60)
    if result.get("batch_root"):
        print(f"[OK] 批量完成 {result.get('ok_count')}/{result.get('total')}")
        print(f"  批次目录: {result['batch_root']}")
        sys.exit(0 if result.get("success") else 1)

    if result.get("success"):
        print("[OK] 归档完成")
        print(f"  输出目录: {result['output_dir']}")
        if result.get("layout_issues"):
            print(f"  版式待核对: {len(result['layout_issues'])} 项")
        sys.exit(0)
    print("[FAIL] 失败:", result.get("error"))
    sys.exit(1)


if __name__ == "__main__":
    main()
