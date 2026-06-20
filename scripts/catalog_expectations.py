# -*- coding: utf-8 -*-
"""卷内目录槽位业务预期（民事等）— 用于评分/对照时排除「通常无卷」项。

业务确认（用户）：
- 缺失目录项：卷内无此材料则组装时跳过，不计入 pdf_missing 结构扣分。
- seq13 庭审笔录：一般无此材料，缺失为常态。
- seq12 出庭通知书：卷内常以「传票」出现，doc_type=summons 即视为命中 seq12。
- 未能识别具体类型的页/段：一律归入证据材料（seq7）。
"""
from __future__ import annotations

import archive_catalog as ac

# 通常不随卷归档的自动识别项（缺失不算结构缺陷）
USUALLY_ABSENT_SEQ: dict[str, frozenset[int]] = {
    "civil": frozenset({13}),
    "admin": frozenset({13}),
}

# 缺失项不参与结构评分（仅作参考输出）
SKIP_MISSING_IN_SCORE = True

# seq12 目录名 vs 实际 OCR 形态
SUMMONS_SEQ = 12
SUMMONS_DOC_TYPE = "summons"  # 含「传票」「出庭通知」锚点
EVIDENCE_SEQ_DEFAULT = 7


def usually_absent_seqs(case_type: str) -> frozenset[int]:
    return USUALLY_ABSENT_SEQ.get(case_type, frozenset())


def filter_scored_missing(case_type: str, missing_seqs: list[int]) -> list[int]:
    """从 pdf_missing 列表中剔除通常无卷的 seq（SKIP_MISSING_IN_SCORE 时返回空）。"""
    if SKIP_MISSING_IN_SCORE:
        return []
    absent = usually_absent_seqs(case_type)
    return [s for s in missing_seqs if s not in absent]


def scored_pdf_missing(case_type: str, missing_seqs_raw: list[int]) -> int:
    """参与综合分扣分的 pdf_missing 计数。"""
    return len(filter_scored_missing(case_type, missing_seqs_raw))


def required_auto_seqs(case_type: str) -> set[int]:
    """参与槽位召回分母的 pdf/mixed seq（排除通常无卷）。"""
    absent = usually_absent_seqs(case_type)
    return {
        it.seq
        for it in ac.get_catalog(case_type)
        if it.source in ("pdf", "mixed") and it.seq not in absent
    }


def slot_recall_stats(ref_seqs: set[int], got_seqs: set[int]) -> dict:
    """槽位对照：缺失项跳过，只统计已识别槽位与金标准的重合度。"""
    matched = ref_seqs & got_seqs
    skipped = ref_seqs - got_seqs
    extra = got_seqs - ref_seqs
    # 分母仅含「AI 已识别且金标准也有」的槽位；卷内缺失项不参与扣分
    denom = len(matched) if matched else len(ref_seqs)
    recall = round(len(matched) / denom, 3) if denom else None
    return {
        "matched": sorted(matched),
        "skipped_missing": sorted(skipped),
        "extra": sorted(extra),
        "slot_recall": recall if matched else (1.0 if not ref_seqs else 0.0),
    }


def has_summons_slot(found_seqs: set[int]) -> bool:
    return SUMMONS_SEQ in found_seqs
