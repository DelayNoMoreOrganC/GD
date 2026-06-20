# -*- coding: utf-8 -*-
"""批量导出 test_file 全部 OCR 页首快照（P1 GT 标注用）。

用法:
  py scripts/dump_all_test_pages.py
  → outputs/_page_snaps_all.json
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import document_segmenter as ds
from archive_pipeline import ingest_archive_sources
from settings import load_config


def _silent(*a, **k):
    pass


def main():
    config = load_config()
    pdfs = sorted(glob.glob("test_sample/test_file/*.pdf"))
    out = {}
    for path in pdfs:
        if "mock" in os.path.basename(path):
            continue
        print(f"dump {os.path.basename(path)} ...")
        srcs = [ds.DocumentSource(path=path, doc_type=ds.DOC_TYPE_DEFAULT)]
        _pt, page_texts, _lb, _c, _r = ingest_archive_sources(srcs, config, log=_silent)
        pages = page_texts.get(path, [])
        snaps = []
        for i, t in enumerate(pages):
            s = (t or "").strip().replace("\n", " ")
            snaps.append({"p": i, "head": s[:100]})
        out[os.path.basename(path)] = {"n": len(pages), "pages": snaps}
    dest = "outputs/_page_snaps_all.json"
    os.makedirs("outputs", exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"saved {dest} ({len(out)} cases)")


if __name__ == "__main__":
    main()
