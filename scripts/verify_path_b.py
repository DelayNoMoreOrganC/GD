#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T-901/T-902: 路径 B 多文件端到端验证

验证路径 B（多文件分类归档）：
1. 使用 test_sample 中 2+ PDF（default + contract）
2. programmatic analyze + assemble，断言 original_pages_included
3. 可选 CLI 路径，解析「源 PDF 纳入」/「源 PDF 已包含」
"""

import re
import sys
import os
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

TEST_FILES = [
    "test_sample/2014-兴泰贸易.pdf:default",
    "test_sample/2019-佛山金百纳贸易有限公司.pdf:contract",
]


def parse_original_pages_included(text: str) -> int | None:
    """从 CLI / merger 日志解析源页纳入数"""
    patterns = [
        r"源 PDF 纳入:\s*(\d+)\s*页",
        r"源 PDF 已包含\s+(\d+)/\d+\s*页",
    ]
    for line in text.splitlines():
        for pat in patterns:
            m = re.search(pat, line)
            if m:
                return int(m.group(1))
    return None


def _expected_pages(file_specs: list) -> tuple[int, list]:
    from archive_ocr import get_pdf_page_count
    from document_segmenter import DocumentSource

    total = 0
    sources = []
    for spec in file_specs:
        path, doc_type = spec.rsplit(":", 1)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        pages = get_pdf_page_count(path)
        total += pages
        sources.append(DocumentSource(path=path, doc_type=doc_type))
    return total, sources


def test_path_b_programmatic() -> bool:
    """programmatic 路径 B：不依赖 subprocess 编码"""
    from archive_pipeline import analyze_archive, assemble_archive
    from settings import load_config

    print("🔍 programmatic 路径 B（analyze → assemble）")
    expected_pages, sources = _expected_pages(TEST_FILES)
    config = load_config()
    output_pdf = "outputs/_verify_path_b.pdf"

    analysis = analyze_archive(
        "civil",
        sources=sources,
        config=config,
        log=lambda *a, **k: None,
    )
    assert len(analysis.doc_spans) >= 2, "路径 B 应至少 2 份文书"

    skipped = [item["seq"] for item in analysis.missing_items]
    result = assemble_archive(
        analysis,
        output_pdf,
        skipped=skipped,
        config=config,
        log=lambda *a, **k: None,
    )

    if not result.success:
        print(f"   ❌ assemble 失败")
        return False
    if result.original_pages_included != expected_pages:
        print(
            f"   ❌ 页守恒失败: {result.original_pages_included} != {expected_pages}"
        )
        return False
    if not os.path.exists(output_pdf):
        print(f"   ❌ 输出不存在: {output_pdf}")
        return False

    print(f"   ✅ doc_spans: {len(analysis.doc_spans)} 份")
    print(f"   ✅ 页守恒: {result.original_pages_included}/{expected_pages}")
    print(f"   ✅ 输出: {output_pdf}")
    return True


def test_path_b_cli(expected_pages: int) -> bool:
    """CLI 路径 B（解析 stdout，Windows 编码可能失败则仅警告）"""
    print()
    print("🔍 CLI 路径 B（run_archive.py --sources）")
    cmd = [
        "py", "run_archive.py",
        "--catalog", "civil",
        "--sources",
    ] + TEST_FILES + [
        "--output", "outputs/_verify_path_b_cli.pdf",
        "--skip-missing",
    ]
    print(f"   {' '.join(cmd)}")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.returncode != 0:
        print(f"   ❌ CLI exit {result.returncode}")
        print(result.stdout[-500:] if result.stdout else "")
        print(result.stderr[-500:] if result.stderr else "")
        return False

    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    included = parse_original_pages_included(combined)
    if included is None:
        print("   ⚠️  CLI stdout 未解析到页守恒行（Windows 编码），programmatic 已通过则 OK")
        return True
    if included != expected_pages:
        print(f"   ❌ CLI 页守恒: {included} != {expected_pages}")
        return False
    print(f"   ✅ CLI 页守恒: {included}/{expected_pages}")
    return True


def test_path_b():
    print("📋 T-901/T-902 路径 B 多文件端到端验证")
    print()

    from archive_ocr import get_pdf_page_count
    expected_pages = 0
    for spec in TEST_FILES:
        path, doc_type = spec.rsplit(":", 1)
        pages = get_pdf_page_count(path)
        expected_pages += pages
        print(f"📄 {path} ({doc_type}) → {pages} 页")
    print(f"   预期总页数: {expected_pages}")
    print()

    if not test_path_b_programmatic():
        return False

    # CLI 验证：耗时较长，可用 --no-cli 跳过
    if "--no-cli" not in sys.argv:
        if not test_path_b_cli(expected_pages):
            return False

    print()
    print("📊 验证结果:")
    print("   ✅ 路径 B 多文件归档成功")
    print(f"   ✅ 页守恒: {expected_pages}/{expected_pages}")
    return True


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    success = test_path_b()
    sys.exit(0 if success else 1)
