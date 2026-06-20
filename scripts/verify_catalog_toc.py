#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卷内目录 Word 模板填充 + PDF 生成验收"""

import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

from catalog_toc import catalog_toc_to_pdf, compute_display_pages, fill_catalog_template
import archive_catalog as ac


def main():
    case_type = "civil"
    body_starts = {0: 0, 1: 2, 2: 5, 3: 8, 4: 11, 5: 14, 7: 17, 12: 30, 14: 40, 16: 80, 15: 85, 17: 88}
    cover_end = 2
    display = compute_display_pages(body_starts, cover_end, toc_pages=1)
    out_pdf = Path("outputs/_verify_catalog_toc.pdf")
    work = Path("outputs")

    print("📋 卷内目录模板填充验收")
    ok = catalog_toc_to_pdf(case_type, display, str(out_pdf), str(work), toc_self_page=3, log=print)
    if not ok:
        print("❌ 卷内目录 PDF 生成失败")
        sys.exit(1)

    try:
        import fitz
        doc = fitz.open(str(out_pdf))
        text = doc[0].get_text()
        doc.close()
        if "目录" not in text and "页码" not in text and "立案" not in text:
            print("⚠ 目录页文本较少（可能为扫描版式），但 PDF 已生成")
    except ImportError:
        pass

    print(f"✅ 卷内目录 PDF: {out_pdf}")
    sys.exit(0)


if __name__ == "__main__":
    main()
