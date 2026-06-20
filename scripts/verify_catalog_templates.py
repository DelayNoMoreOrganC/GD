#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查五类卷内目录 Word 模板是否就绪"""

import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

import archive_catalog as ac
from app_paths import get_catalog_template_path

def main():
    ok = True
    print("卷内目录模板检查（templates/bundled/）")
    print("占位符：【页码0】…【页码N】对应 catalog seq，【页码目录】= 目录自身页\n")
    for code, label in ac.CASE_TYPE_LABELS.items():
        p = get_catalog_template_path(code)
        exists = Path(p).is_file()
        mark = "✅" if exists else "❌"
        print(f"  {mark} {label} ({code}): {p}")
        if not exists:
            ok = False
    print()
    if ok:
        print("✅ 五类卷内目录模板齐全")
        sys.exit(0)
    print("❌ 请将卷内目录 Word 模板放入 templates/bundled/，文件名见 archive_catalog.CATALOG_TEMPLATE_FILES")
    sys.exit(1)

if __name__ == "__main__":
    main()
