#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V1.3.6 发布入口：百度 OCR + zip/pdf 输出（无 MinerU 切换为默认）"""

import legal_archive_gui as app
from app_version import V1_VERSION

app.APP_VERSION = V1_VERSION

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        pages = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        sys.exit(app.run_cli(sys.argv[1], pages))
    app.ArchiveApp().mainloop()
