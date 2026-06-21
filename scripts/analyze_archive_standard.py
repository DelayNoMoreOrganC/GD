# -*- coding: utf-8 -*-
"""从 standard_sample 历史归档成品提炼归档规律（目录/物理结构/字段）。

用法: py scripts/analyze_archive_standard.py
→ outputs/_archive_standard_analysis.json
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz

STANDARD_DIR = "test_sample/standard_sample"

# 系统表/目录页识别锚点
COVER_KW = "律师业务档案卷宗"
TOC_KW = ("卷内目录", "案卷目录", "民事案卷目录", "案卷目录")
FILING_KW = "立案审批表"
QUALITY_KW = ("质量监督卡", "办案质量监督")
DELIVERY_KW = ("送达材料清单", "送达清单")
CLIENT_KW = "委托人须知"
CLOSING_KW = ("结案报告", "结案报告表")


def _has(text, *kws):
    return any(k in text for k in kws)


def detect_page_role(text):
    """识别成品 PDF 单页的归档角色（系统表/目录/正文）。"""
    head = text[:300]
    if COVER_KW in head:
        return "cover"
    if _has(head, *TOC_KW):
        return "toc"
    if FILING_KW in head:
        return "filing_form"
    if _has(head, *QUALITY_KW):
        return "quality_card"
    if _has(head, *DELIVERY_KW):
        return "delivery_list"
    if CLIENT_KW in head:
        return "client_notice"
    if _has(head, *CLOSING_KW):
        return "closing_report"
    return "body"


def analyze_physical(path):
    """解析成品 PDF 物理结构：各系统表/目录页的实际位置。"""
    d = fitz.open(path)
    n = d.page_count
    roles = []
    cover_fields = {}
    for i in range(n):
        text = d[i].get_text().strip()
        role = detect_page_role(text)
        roles.append(role)
        if role == "cover" and not cover_fields:
            cover_fields = parse_cover_fields(text)
    d.close()
    sys_pages = {
        "cover": [i for i, r in enumerate(roles) if r == "cover"],
        "toc": [i for i, r in enumerate(roles) if r == "toc"],
        "filing_form": [i for i, r in enumerate(roles) if r == "filing_form"],
        "quality_card": [i for i, r in enumerate(roles) if r == "quality_card"],
        "delivery_list": [i for i, r in enumerate(roles) if r == "delivery_list"],
        "client_notice": [i for i, r in enumerate(roles) if r == "client_notice"],
        "closing_report": [i for i, r in enumerate(roles) if r == "closing_report"],
    }
    return {"pages": n, "sys_pages": sys_pages, "cover_fields": cover_fields}


def parse_cover_fields(text):
    """从封面文字层提炼字段（字段名与值分行的表格单元格形式）。"""
    fields = {}
    keys = [
        "案件类别", "合同号", "承办律师", "委托人", "当事人",
        "对方当事人", "案由", "收案日期", "结案日期", "审理法院", "审级",
        "法院收案号", "审（办）结果", "归档日期", "卷内页数", "档案号",
        "保存年限",
    ]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # 字段名与值分行：遇到字段名后，下一个非字段名的行即为值
    keyset = set(keys)
    i = 0
    while i < len(lines):
        cur = lines[i]
        if cur in keyset and cur not in fields:
            # 案由可能拆成「案」「由」两行，特殊处理
            if cur == "案" and i + 1 < len(lines) and lines[i + 1] == "由":
                # 取「由」之后的值
                j = i + 2
                if j < len(lines) and lines[j] not in keyset:
                    fields["案由"] = lines[j]
                    i = j
                else:
                    i += 2
                continue
            j = i + 1
            while j < len(lines) and lines[j] in keyset:
                j += 1
            if j < len(lines):
                val = lines[j]
                if val and len(val) <= 60:
                    fields[cur] = val
                    i = j
        i += 1
    return fields


def main():
    # 1) 目录规律（已提取的 _standard_catalogs.json）
    catalog_json = "outputs/_standard_catalogs.json"
    seq_freq = collections.Counter()
    item_count = collections.Counter()
    seq_names = collections.defaultdict(collections.Counter)
    case_seqs = {}
    if os.path.isfile(catalog_json):
        d = json.load(open(catalog_json, encoding="utf-8"))
        for c in d["catalogs"]:
            items = c["items"]
            item_count[len(items)] += 1
            seqs = sorted(it["seq"] for it in items)
            case_seqs[c["case"]] = seqs
            for it in items:
                seq_freq[it["seq"]] += 1
                seq_names[it["seq"]][it["name"]] += 1

    # 2) 物理结构（解析有文字层的成品）
    pdfs = sorted(glob.glob(os.path.join(STANDARD_DIR, "*.pdf")))
    phys = {}
    textlayer_count = 0
    for p in pdfs:
        try:
            r = analyze_physical(p)
            r["has_textlayer"] = True
            textlayer_count += 1
        except Exception as e:
            r = {"error": str(e), "has_textlayer": False}
        phys[os.path.basename(p)] = r

    # 3) 系统表位置规律统计
    role_order_stats = collections.Counter()
    delivery_in_catalog = 0
    delivery_as_syspage = 0
    cover_field_freq = collections.Counter()
    for bn, r in phys.items():
        if r.get("has_textlayer") and r.get("sys_pages"):
            sp = r["sys_pages"]
            # 卷末系统表顺序：记录 quality_card/client_notice/delivery_list/closing_report 出现的页序
            tail = sorted(
                sp.get("quality_card", [])
                + sp.get("delivery_list", [])
                + sp.get("client_notice", [])
                + sp.get("closing_report", [])
            )
            tail_roles = []
            allroles = {}
            for role_key in ("quality_card", "delivery_list", "client_notice", "closing_report"):
                for pg in sp.get(role_key, []):
                    allroles[pg] = role_key
            for pg in sorted(allroles):
                tail_roles.append(allroles[pg])
            role_order_stats[" > ".join(tail_roles)] += 1
            if sp.get("delivery_list"):
                delivery_as_syspage += 1
            for k in r.get("cover_fields", {}):
                cover_field_freq[k] += 1

    # 目录里是否出现 seq17（送达清单作为目录条目）
    delivery_in_catalog = seq_freq.get(17, 0)

    report = {
        "sample_count": len(pdfs),
        "textlayer_count": textlayer_count,
        "catalog_law": {
            "item_count_dist": dict(item_count),
            "seq_frequency": {f"seq{s}": f for s, f in sorted(seq_freq.items())},
            "seq17_in_catalog": delivery_in_catalog,
            "seq15_in_catalog": seq_freq.get(15, 0),
            "core_seqs_always_present": sorted(
                s for s, f in seq_freq.items() if f == max(seq_freq.values())
            ),
            "case_seqs": case_seqs,
        },
        "physical_structure": {
            "tail_role_order": dict(role_order_stats),
            "delivery_as_physical_page": delivery_as_syspage,
            "cover_field_frequency": dict(cover_field_freq.most_common()),
        },
        "per_case": phys,
    }

    out = "outputs/_archive_standard_analysis.json"
    os.makedirs("outputs", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
