#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分路提取结果合并"""

from case_outcome import synthesize_outcome_narrative
from document_segmenter import (
    DOC_TYPE_COMPLAINT,
    DOC_TYPE_CONTRACT,
    DOC_TYPE_EXECUTION,
    DOC_TYPE_JUDGMENT,
)

FIELD_PRIORITY = {
    "委托人": [DOC_TYPE_CONTRACT, DOC_TYPE_JUDGMENT, DOC_TYPE_COMPLAINT],
    "委托人名称": [DOC_TYPE_CONTRACT],
    "委托人电话": [DOC_TYPE_CONTRACT],
    "委托人联系地址及电话": [DOC_TYPE_CONTRACT],
    "收案日期": [DOC_TYPE_CONTRACT],
    "立案日期": [DOC_TYPE_CONTRACT],
    "案号": [DOC_TYPE_JUDGMENT, DOC_TYPE_EXECUTION],
    "法院收案号": [DOC_TYPE_JUDGMENT, DOC_TYPE_EXECUTION],
    "案由": [DOC_TYPE_JUDGMENT],
    "审理法院": [DOC_TYPE_JUDGMENT],
    "审级": [DOC_TYPE_JUDGMENT],
    "委托方": [DOC_TYPE_JUDGMENT],
    "承办律师": [DOC_TYPE_JUDGMENT],
    "代理律师": [DOC_TYPE_JUDGMENT],
    "当事人": [DOC_TYPE_COMPLAINT, DOC_TYPE_JUDGMENT],
    "地址": [DOC_TYPE_COMPLAINT],
    "对方当事人": [DOC_TYPE_COMPLAINT],
    "案情简介": [DOC_TYPE_COMPLAINT, DOC_TYPE_JUDGMENT],
    "案件或项目名称": [DOC_TYPE_JUDGMENT],
    "结案小结": [DOC_TYPE_JUDGMENT, DOC_TYPE_EXECUTION],
    "审（办）结果": [DOC_TYPE_JUDGMENT, DOC_TYPE_EXECUTION],
    "法院文件清单": [DOC_TYPE_JUDGMENT, DOC_TYPE_EXECUTION],
}


def _pick_value(field: str, partials: dict) -> str:
    for doc_type in FIELD_PRIORITY.get(field, []):
        bucket = partials.get(doc_type) or {}
        val = (bucket.get(field) or "").strip()
        if val:
            return val
    for bucket in partials.values():
        val = (bucket.get(field) or "").strip()
        if val:
            return val
    return ""


def merge_partial_fields(partials: dict) -> dict:
    """partials: {doc_type: {field: value}} → flat dict"""
    all_keys = set()
    for bucket in partials.values():
        all_keys.update(bucket.keys())

    merged = {}
    for key in sorted(all_keys):
        val = _pick_value(key, partials)
        if val:
            merged[key] = val

    j_part = (partials.get(DOC_TYPE_JUDGMENT) or {}).get("结案小结", "")
    e_part = (partials.get(DOC_TYPE_EXECUTION) or {}).get("结案小结", "")
    j_review = (partials.get(DOC_TYPE_JUDGMENT) or {}).get("审（办）结果", "")
    e_review = (partials.get(DOC_TYPE_EXECUTION) or {}).get("审（办）结果", "")
    if not j_part and j_review:
        j_part = j_review
    if not e_part and e_review:
        e_part = e_review

    if j_part and e_part:
        combined = synthesize_outcome_narrative(j_part, e_part)
        if combined:
            merged["结案小结"] = combined
            merged["审（办）结果"] = combined
    elif j_part and not merged.get("结案小结"):
        merged["结案小结"] = j_part
        merged["审（办）结果"] = j_part
    elif e_part and not merged.get("结案小结"):
        merged["结案小结"] = e_part
        merged["审（办）结果"] = e_part

    doc_lists = []
    for dt in (DOC_TYPE_JUDGMENT, DOC_TYPE_EXECUTION):
        raw = (partials.get(dt) or {}).get("法院文件清单", "")
        if raw:
            doc_lists.append(raw)
    if doc_lists:
        items = []
        seen = set()
        for raw in doc_lists:
            for part in raw.replace("，", "、").split("、"):
                p = part.strip()
                if p and p not in seen:
                    seen.add(p)
                    items.append(p)
        if items:
            merged["法院文件清单"] = "、".join(items)

    merged.setdefault("案件类别", "民事")
    merged.setdefault("律师事务所", "广东至高律师事务所")
    merged.setdefault("委托人对服务质量意见", "委托人对承办律师服务质量表示满意")

    return merged
