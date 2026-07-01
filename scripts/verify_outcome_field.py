# -*- coding: utf-8 -*-
"""对比系统生成的审办结果与金标准，输出 outcome_acc。

用法:
  py scripts/extract_standard_fields.py   # 首次生成 GT
  py scripts/verify_outcome_field.py
  py scripts/verify_outcome_field.py test_sample/test_file/2014-兴泰贸易.pdf
  py scripts/verify_outcome_field.py --no-llm   # 仅规则+分路，不调 DeepSeek
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

GT_PATH = os.path.join(ROOT, "outputs", "_standard_fields_gt.json")
TEST_DIR = os.path.join(ROOT, "test_sample", "test_file")


def _silent(*a, **k):
    pass


def _load_gt():
    if not os.path.isfile(GT_PATH):
        return {}
    with open(GT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v.get("结案小结", "") for k, v in data.get("cases", {}).items() if v.get("has_outcome")}


def _run_case(pdf_path: str, use_llm: bool = True) -> dict:
    from archive_pipeline import analyze_archive
    from document_segmenter import DocumentSource
    from outcome_metrics import pick_outcome_text, score_outcome

    config = {}
    if not use_llm:
        os.environ["GD_SKIP_LLM"] = "1"

    src = DocumentSource(path=pdf_path, doc_type="default")
    try:
        analysis = analyze_archive("civil", sources=[src], config=config, log=_silent)
    finally:
        os.environ.pop("GD_SKIP_LLM", None)

    fields = analysis.fields or {}
    return {
        "fields": fields,
        "outcome": pick_outcome_text(fields),
        "found_seqs": sorted(analysis.found_seqs),
    }


def _match_gt_name(pdf_basename: str, gt_names: dict) -> str:
    stem = os.path.splitext(pdf_basename)[0]
    if stem in gt_names:
        return stem
    for name in gt_names:
        if stem in name or name in stem:
            return name
    return ""


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*", help="指定 PDF，默认扫 test_file")
    ap.add_argument("--no-llm", action="store_true", help="跳过 LLM（仅测规则链路时需 mock）")
    args = ap.parse_args()

    if not os.path.isfile(GT_PATH):
        print("GT 不存在，先运行: py scripts/extract_standard_fields.py")
        sys.exit(1)

    gt = _load_gt()
    if not gt:
        print("GT 无结案小结条目")
        sys.exit(1)

    pdfs = args.pdfs
    if not pdfs:
        pdfs = [
            os.path.join(TEST_DIR, f)
            for f in os.listdir(TEST_DIR)
            if f.lower().endswith(".pdf")
        ]

    from outcome_metrics import score_outcome

    rows = []
    for pdf in sorted(pdfs):
        if not os.path.isfile(pdf):
            continue
        gt_key = _match_gt_name(os.path.basename(pdf), gt)
        gold = gt.get(gt_key, "") if gt_key else ""
        if not gold:
            rows.append({"pdf": os.path.basename(pdf), "skip": "no_gt"})
            continue
        try:
            res = _run_case(pdf, use_llm=not args.no_llm)
            sc = score_outcome(res["fields"], gold)
            rows.append({
                "pdf": os.path.basename(pdf),
                "gt_key": gt_key,
                "score": sc["score"],
                "similarity": sc["similarity"],
                "type_match": sc["type_match"],
                "pred_type": sc["pred_type"],
                "gold_type": sc["gold_type"],
                "pred_preview": (sc["pred"] or "")[:80],
            })
        except Exception as e:
            rows.append({"pdf": os.path.basename(pdf), "error": str(e)})

    scored = [r for r in rows if "score" in r]
    avg = sum(r["score"] for r in scored) / len(scored) if scored else 0.0
    type_acc = sum(1 for r in scored if r["type_match"]) / len(scored) if scored else 0.0

    report = {
        "outcome_acc_avg": round(avg, 3),
        "outcome_type_acc": round(type_acc, 3),
        "cases": rows,
    }
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    out_path = os.path.join(ROOT, "outputs", "outcome_field_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"outcome_acc_avg={report['outcome_acc_avg']}  type_acc={report['outcome_type_acc']}  n={len(scored)}")
    for r in scored:
        print(f"  {r['pdf']}: score={r['score']} type={r['type_match']} pred={r['pred_preview']!r}")
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
