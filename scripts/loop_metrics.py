# -*- coding: utf-8 -*-
"""归档质量量化评分（0619 循环优化用）

对 test_sample 下每个案件 PDF 运行 analyze_archive（走 OCR 缓存，快），
量化以下指标，作为每轮循环的客观评分：

- dup_pages      : doc_spans 中重复纳入的源页数（必须为 0，>0 = 数据损坏）
- gap_pages      : 源 PDF 中未被任何 unit 覆盖的页数（漏页）
- pdf_missing    : 未识别到的目录项数（仅参考，不参与扣分；缺失项组装时跳过）
- todo_fields    : 抽取字段值含「待确认」的数量（越低越好）
- low_conf       : 低置信切分段数
- units          : 切分出的文书段数

综合 score（越高越好，满分 100/案）：
  100 - dup_pages*5 - gap_pages*3 - low_conf*1
  （pdf_missing 仅参考，缺失目录项跳过不计分）
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import Counter
import fitz  # PyMuPDF
import archive_catalog as ac
import pdf_doc_locator as pdl
import document_segmenter as ds
from archive_pipeline import ingest_archive_sources
from settings import load_config


def _silent(*a, **k):
    pass


def _pdf_pages(path):
    try:
        d = fitz.open(path)
        n = d.page_count
        d.close()
        return n
    except Exception:
        return 0


def score_case(path, case_type, config):
    """结构质量评分（仅 WF1+WF2+WF3，无 LLM/Word，走 OCR 缓存，快且确定）。"""
    n_pages = _pdf_pages(path)
    catalog = ac.get_catalog(case_type)
    seq_source = {it.seq: it.source for it in catalog}

    doc_sources = [ds.DocumentSource(path=path, doc_type=ds.DOC_TYPE_DEFAULT)]
    pdf_texts, page_texts, layout_blocks, _calls, _rapid = ingest_archive_sources(
        doc_sources, config, log=_silent
    )
    spans = pdl.build_units_from_sources(
        doc_sources, case_type, config,
        pdf_texts=pdf_texts, page_texts_by_path=page_texts,
        layout_blocks_by_path=layout_blocks, log=_silent,
    )

    # 页覆盖（按源文件聚合；test_sample 均为单卷路径 A）
    covered = []
    for u in spans:
        covered.extend(range(u.start_page, u.end_page + 1))
    cnt = Counter(covered)
    dup_pages = sum(v - 1 for v in cnt.values() if v > 1)
    gap_pages = max(0, n_pages - len(set(covered)))

    # 自动可识别(pdf/mixed)目录项的命中情况；manual 项靠人工上传不计入
    found_seqs = {u.catalog_seq for u in spans if u.catalog_seq is not None}
    auto_seqs = [it.seq for it in catalog if it.source in ("pdf", "mixed")]
    missing_pdf_seqs_raw = [s for s in auto_seqs if s not in found_seqs]
    from catalog_expectations import (
        filter_scored_missing,
        scored_pdf_missing,
        usually_absent_seqs,
    )
    missing_pdf_seqs = filter_scored_missing(case_type, missing_pdf_seqs_raw)
    optional_absent = [s for s in missing_pdf_seqs_raw if s in usually_absent_seqs(case_type)]
    pdf_missing = scored_pdf_missing(case_type, missing_pdf_seqs_raw)

    low_conf = sum(1 for u in spans if (u.confidence or 1.0) < 0.6)
    units = len(spans)

    # 类型正确率：每页归属 unit 的 catalog_seq 是否等于 ground-truth seq
    from ground_truth import GROUND_TRUTH, GT_TIER1
    gt = GROUND_TRUTH.get(os.path.basename(path))
    type_acc = None
    type_wrong = []
    if gt:
        page_seq = {}
        for u in spans:
            for p in range(u.start_page, u.end_page + 1):
                page_seq[p] = u.catalog_seq
        correct = 0
        for p, exp in gt.items():
            got = page_seq.get(p)
            if got == exp:
                correct += 1
            else:
                type_wrong.append({"p": p, "exp": exp, "got": got})
        type_acc = round(correct / len(gt), 3) if gt else None

    type_tier = "tier1" if os.path.basename(path) in GT_TIER1 else (
        "tier2" if gt else None
    )

    # 综合分：结构分 + 类型正确率(×40)
    score = max(0, 100 - dup_pages * 5 - gap_pages * 3 - low_conf * 1)
    if type_acc is not None:
        score = round(score * 0.4 + type_acc * 100 * 0.6)

    return {
        "case": os.path.basename(path),
        "pages": n_pages,
        "units": units,
        "dup_pages": dup_pages,
        "gap_pages": gap_pages,
        "pdf_missing": pdf_missing,
        "pdf_missing_optional": optional_absent,
        "missing_pdf_seqs": missing_pdf_seqs_raw,
        "low_conf": low_conf,
        "type_acc": type_acc,
        "type_tier": type_tier,
        "type_wrong": type_wrong,
        "score": score,
        "spans": [
            {"seq": u.catalog_seq, "type": u.doc_type,
             "p": f"{u.start_page}-{u.end_page}"}
            for u in sorted(spans, key=lambda u: (u.catalog_seq or 999, u.start_page))
        ],
    }


def main():
    config = load_config()
    case_type = "civil"
    pdfs = sys.argv[1:] if len(sys.argv) > 1 else [
        p for p in sorted(glob.glob("test_sample/test_file/*.pdf"))
        if "mock" not in os.path.basename(p)
    ]
    results = []
    for p in pdfs:
        try:
            r = score_case(p, case_type, config)
        except Exception as e:
            import traceback
            r = {"case": os.path.basename(p), "error": str(e),
                 "trace": traceback.format_exc(), "score": 0}
        results.append(r)
        if "error" in r:
            print(f"[ERR ] {r['case']}: {r['error']}")
        else:
            ta = r.get("type_acc")
            print(f"[{r['score']:3d}] {r['case']}: pages={r['pages']} units={r['units']} "
                  f"dup={r['dup_pages']} gap={r['gap_pages']} "
                  f"pdf_missing={r['pdf_missing']}{r['missing_pdf_seqs']} "
                  f"type_acc={ta}")

    valid = [r for r in results if "error" not in r]
    with_gt = [r for r in valid if r.get("type_acc") is not None]
    tier1 = [r for r in with_gt if r.get("type_tier") == "tier1"]
    tier2 = [r for r in with_gt if r.get("type_tier") == "tier2"]
    without_gt = [r for r in valid if r.get("type_acc") is None]
    total = sum(r["score"] for r in results)
    avg = total / len(results) if results else 0
    struct_avg = (
        sum(r["score"] for r in without_gt) / len(without_gt) if without_gt else None
    )
    type_avg_t1 = (
        sum(r["type_acc"] for r in tier1) / len(tier1) if tier1 else None
    )
    type_avg_t2 = (
        sum(r["type_acc"] for r in tier2) / len(tier2) if tier2 else None
    )
    print(f"\n==== TOTAL score={total} avg={avg:.1f} over {len(results)} cases ====")
    print(f"     结构分(无GT {len(without_gt)}案): "
          f"{struct_avg:.1f}" if struct_avg is not None else "     结构分: n/a")
    if type_avg_t1 is not None:
        print(f"     type_acc Tier1({len(tier1)}案): {type_avg_t1:.3f}")
    if type_avg_t2 is not None:
        print(f"     type_acc Tier2({len(tier2)}案): {type_avg_t2:.3f}")
    if not tier1 and not tier2:
        print(f"     类型准确率: 无 GT")
    if without_gt:
        print(f"     [WARN] 无 GT 案件: {', '.join(r['case'] for r in without_gt[:5])}"
              + (" ..." if len(without_gt) > 5 else ""))

    out = "outputs/_loop_metrics.json"
    os.makedirs("outputs", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "avg": avg,
            "total": total,
            "struct_avg_no_gt": struct_avg,
            "type_avg_tier1": type_avg_t1,
            "type_avg_tier2": type_avg_t2,
            "gt_coverage": f"{len(with_gt)}/{len(valid)}",
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
