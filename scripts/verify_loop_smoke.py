# -*- coding: utf-8 -*-
"""P0 结构冒烟：3 案 GT + 全库 dup/gap 硬约束（免 LLM/Word）。

用法:
  py scripts/verify_loop_smoke.py           # 3 案 GT + 18 案 dup/gap
  py scripts/verify_loop_smoke.py --gt-only   # 仅 3 案 GT
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loop_metrics import score_case
from ground_truth import GROUND_TRUTH, GT_TIER1, GT_TIER1_MIN_ACC
from settings import load_config

# 有逐页 GT 的三案 + 最低 type_acc 门槛（Iteration 8 基线）
GT_CASES = dict(GT_TIER1_MIN_ACC)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt-only", action="store_true", help="仅跑 3 案 GT")
    args = ap.parse_args()

    config = load_config()
    case_type = "civil"
    failed = []

    print("P0-A: GT 三案（dup/gap=0 + type_acc 门槛）")
    type_accs = []
    for name, min_acc in GT_CASES.items():
        path = os.path.join("test_sample", "test_file", name)
        if not os.path.isfile(path):
            print(f"  [SKIP] {name}: 文件不存在")
            continue
        r = score_case(path, case_type, config)
        dup, gap = r["dup_pages"], r["gap_pages"]
        ta = r.get("type_acc")
        ok = dup == 0 and gap == 0 and ta is not None and ta >= min_acc
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] {name}: dup={dup} gap={gap} type_acc={ta} (min={min_acc})")
        if ta is not None:
            type_accs.append(ta)
        if not ok:
            failed.append(name)

    if type_accs:
        avg = sum(type_accs) / len(type_accs)
        print(f"  type_avg_gt_tier1={avg:.3f}")

    if args.gt_only:
        sys.exit(1 if failed else 0)

    print("\nP0-B: 全库 test_file dup/gap（18 案）")
    pdfs = sorted(glob.glob("test_sample/test_file/*.pdf"))
    bad = []
    for path in pdfs:
        if "mock" in os.path.basename(path):
            continue
        r = score_case(path, case_type, config)
        if r.get("dup_pages") or r.get("gap_pages"):
            bad.append((r["case"], r["dup_pages"], r["gap_pages"]))
    if bad:
        for c, d, g in bad:
            print(f"  [FAIL] {c}: dup={d} gap={g}")
        failed.extend(c["case"] if isinstance(c, str) else c[0] for c in bad)
    else:
        print(f"  [OK] {len(pdfs)} 案 dup/gap 全 0")

    print("\nP0-C: standard_sample 目录金标准")
    cat_path = "outputs/_standard_catalogs.json"
    if not os.path.isfile(cat_path):
        print("  [WARN] 未找到 outputs/_standard_catalogs.json，请运行 extract_standard_catalog.py")
    else:
        import json
        with open(cat_path, encoding="utf-8") as f:
            data = json.load(f)
        parsed, skipped = data.get("parsed", 0), data.get("skipped", 0)
        ok = parsed >= 28
        print(f"  [{'OK' if ok else 'WARN'}] 目录解析 {parsed}/31 (skipped={skipped})")
        if not ok:
            failed.append("standard_catalogs")

    print()
    if failed:
        print(f"FAIL: {len(failed)} 项未通过")
        sys.exit(1)
    print("PASS: P0 结构冒烟全部通过")
    sys.exit(0)


if __name__ == "__main__":
    main()
