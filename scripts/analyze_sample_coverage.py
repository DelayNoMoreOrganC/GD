# -*- coding: utf-8 -*-
"""分析 test_file / standard_sample 覆盖缺口与金标准可解析性。"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
from difflib import SequenceMatcher


def _stem(fn):
    return os.path.splitext(os.path.basename(fn))[0]


def _pages(path):
    try:
        d = fitz.open(path)
        n = d.page_count
        d.close()
        return n
    except Exception:
        return -1


def parse_text_toc(path, max_scan=3):
    """从金标准 PDF 目录页提取 (seq, name, display_page)。"""
    d = fitz.open(path)
    text = ""
    for i in range(min(max_scan, d.page_count)):
        t = d[i].get_text("text")
        if "目录" in t or "页码" in t:
            text = t
            break
    d.close()
    if not text:
        return None
    rows = []
    for m in re.finditer(r"(\d{1,2})\s*([^\d\n|]{2,40}?)\s+(\d{1,3})\s", text.replace("|", "\n")):
        seq, name, pg = int(m.group(1)), m.group(2).strip(), int(m.group(3))
        if 1 <= seq <= 18:
            rows.append((seq, name, pg))
    return rows if len(rows) >= 8 else None


def main():
    tf = sorted(glob.glob("test_sample/test_file/*.pdf"))
    ss = sorted(glob.glob("test_sample/standard_sample/*.pdf"))
    tf_stems = {_stem(p): p for p in tf}
    ss_stems = {_stem(p): p for p in ss}

    print("=" * 60)
    print("1. 样本规模")
    print(f"   test_file:       {len(tf)} 份")
    print(f"   standard_sample: {len(ss)} 份")
    print(f"   同名配对:        {len(set(tf_stems) & set(ss_stems))} 份")
    print(f"   仅 test_file:    {len(set(tf_stems) - set(ss_stems))} 份")
    print(f"   仅 standard:     {len(set(ss_stems) - set(tf_stems))} 份")

    print("\n2. standard_sample 目录可解析性（文字目录页）")
    cat_json = "outputs/_standard_catalogs.json"
    if os.path.isfile(cat_json):
        with open(cat_json, encoding="utf-8") as f:
            cat_data = json.load(f)
        print(f"   已提取槽位目录: {cat_data.get('parsed', 0)} / {len(ss)}")
        print(f"   (运行 py scripts/extract_standard_catalog.py 生成)")
    else:
        print("   未生成 outputs/_standard_catalogs.json，请先运行 extract_standard_catalog.py")
    parseable, not_parseable = [], []
    for p in ss:
        rows = parse_text_toc(p)
        if rows:
            parseable.append((os.path.basename(p), len(rows)))
        else:
            not_parseable.append(os.path.basename(p))
    print(f"   旧版粗解析(仅供参考): {len(parseable)} / {len(ss)}")

    print("\n3. ground_truth 覆盖")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from ground_truth import GROUND_TRUTH

    gt_names = set(GROUND_TRUTH.keys())
    print(f"   GT 案件数: {len(gt_names)} / {len(tf)} test_file")
    for p in tf:
        bn = os.path.basename(p)
        mark = "GT" if bn in gt_names else "—"
        print(f"     [{mark}] {bn} ({_pages(p)}p)")

    print("\n4. loop_metrics 全量 test_file（若存在缓存结果）")
    lm_path = "outputs/_loop_metrics.json"
    if os.path.isfile(lm_path):
        with open(lm_path, encoding="utf-8") as f:
            lm = json.load(f)
        gt_n = sum(1 for r in lm["results"] if r.get("type_acc") is not None)
        dup_bad = [r["case"] for r in lm["results"] if r.get("dup_pages") or r.get("gap_pages")]
        print(f"   已评分: {len(lm['results'])} 案, avg={lm.get('avg', 0):.1f}")
        print(f"   type_acc 有值: {gt_n} / {len(lm['results'])}")
        print(f"   dup/gap 异常: {dup_bad or '无'}")
        miss = {}
        for r in lm["results"]:
            for s in r.get("missing_pdf_seqs", []):
                miss[s] = miss.get(s, 0) + 1
        print(f"   高频 pdf_missing seq: {sorted(miss.items(), key=lambda x: -x[1])[:6]}")
    else:
        print("   (未找到 outputs/_loop_metrics.json，请先运行 loop_metrics.py)")

    print("\n5. test_file 无金标准配对的近似名（仅供参考，非正式配对）")
    for t in sorted(tf_stems):
        if t in ss_stems:
            continue
        best = max(ss_stems, key=lambda s: SequenceMatcher(None, t, s).ratio())
        r = SequenceMatcher(None, t, best).ratio()
        if r >= 0.65:
            print(f"   {t}")
            print(f"      ~ {best} ({r:.2f}), test={_pages(tf_stems[t])}p std={_pages(ss_stems[best])}p")


if __name__ == "__main__":
    main()
