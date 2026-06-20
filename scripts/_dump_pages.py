# -*- coding: utf-8 -*-
"""导出每页 OCR 标题快照，用于人工建立 ground-truth 标注。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import document_segmenter as ds
from archive_pipeline import ingest_archive_sources
from settings import load_config


def _silent(*a, **k):
    pass


def main():
    config = load_config()
    pdfs = sys.argv[1:]
    out = {}
    for path in pdfs:
        srcs = [ds.DocumentSource(path=path, doc_type=ds.DOC_TYPE_DEFAULT)]
        _pt, page_texts, _lb, _c, _r = ingest_archive_sources(srcs, config, log=_silent)
        pages = page_texts.get(path, [])
        snaps = []
        for i, t in enumerate(pages):
            s = (t or "").strip().replace("\n", " ")
            snaps.append({"p": i, "head": s[:80]})
        out[os.path.basename(path)] = {"n": len(pages), "pages": snaps}
    with open("outputs/_page_snaps.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("saved outputs/_page_snaps.json")


if __name__ == "__main__":
    main()
