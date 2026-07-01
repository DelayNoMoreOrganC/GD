# -*- coding: utf-8 -*-
"""从 standard_sample 金标准 PDF 提取结案小结/审办结果等字段 GT。

用法:
  py scripts/extract_standard_fields.py
  → outputs/_standard_fields_gt.json
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, SCRIPTS)

import fitz

from analyze_archive_standard import STANDARD_DIR, detect_page_role

OUTCOME_LABELS = ("结案小结", "审（办）结果", "审办结果")


def _parse_closing_report(text: str) -> dict:
    """从结案报告表页 OCR/文字层解析字段。"""
    fields = {}
    compact = re.sub(r"\s+", "", text or "")
    m = re.search(
        r"结案小结(.+?)(?:委托人|承办律师|主任审批|结案日期|委托人对)",
        compact,
    )
    if m:
        val = _normalize_spaces(m.group(1))
        if len(val) >= 8:
            fields["结案小结"] = val
            fields["审（办）结果"] = val
            fields["审办结果"] = val
            return fields

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line in OUTCOME_LABELS:
            parts = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt in OUTCOME_LABELS or nxt in (
                    "案件类别", "委托人名称", "案件或项目名称", "委托人对服务质量意见",
                    "应收业务费", "已收业务费", "承办律师意见", "主任审批意见", "结案日期",
                ):
                    break
                if len(nxt) > 4:
                    parts.append(nxt)
                j += 1
            val = _normalize_spaces("".join(parts) if parts else "")
            if not val and j < len(lines):
                val = _normalize_spaces(lines[j])
            if val and len(val) >= 8:
                fields["结案小结"] = val
                fields["审（办）结果"] = val
                fields["审办结果"] = val
            i = j
            continue
        # 同行「结案小结：xxx」
        for label in OUTCOME_LABELS:
            if line.startswith(label):
                rest = line[len(label) :].lstrip("：: \t")
                if rest and len(rest) >= 8:
                    fields["结案小结"] = _normalize_spaces(rest)
                    fields["审（办）结果"] = fields["结案小结"]
                    fields["审办结果"] = fields["结案小结"]
        i += 1
    return fields


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_from_pdf(path: str) -> dict:
    doc = fitz.open(path)
    closing_text = ""
    cover_outcome = ""
    for i in range(doc.page_count):
        text = doc[i].get_text().strip()
        role = detect_page_role(text)
        if role == "closing_report":
            closing_text = text
        if role == "cover" and not cover_outcome:
            m = re.search(r"审[（(]办[）)]结果\s*[:：]?\s*(.+)", text)
            if m:
                cover_outcome = _normalize_spaces(m.group(1))[:200]
    doc.close()

    fields = _parse_closing_report(closing_text)
    if not fields.get("结案小结") and cover_outcome:
        fields["结案小结"] = cover_outcome
        fields["审（办）结果"] = cover_outcome
        fields["审办结果"] = cover_outcome
    return fields


def main():
    pdfs = sorted(glob.glob(os.path.join(STANDARD_DIR, "*.pdf")))
    out = {"cases": {}, "with_outcome": 0, "total": len(pdfs)}
    for p in pdfs:
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            fields = extract_from_pdf(p)
            outcome = fields.get("结案小结", "")
            out["cases"][name] = {
                "path": p,
                "结案小结": outcome,
                "has_outcome": bool(outcome and len(outcome) >= 10),
            }
            if outcome:
                out["with_outcome"] += 1
        except Exception as e:
            out["cases"][name] = {"error": str(e), "has_outcome": False}

    os.makedirs("outputs", exist_ok=True)
    path = "outputs/_standard_fields_gt.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"saved {path} ({out['with_outcome']}/{out['total']} with 结案小结)")


if __name__ == "__main__":
    main()
