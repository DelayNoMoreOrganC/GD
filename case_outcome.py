#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结案小结 / 审（办）结果：综合判决书与执行终本裁定，控制字数"""

import re

CASE_OUTCOME_MAX_LEN = 150

EXEC_MARKERS = (
    "执行",
    "终本",
    "终结本次",
    "拍卖",
    "查封",
    "扣划",
    "可供执行",
    "恢复执行",
    "立案执行",
)

OUTCOME_REFERENCE_SHORT = (
    "判决被告何锦刚偿还贷款本金688204.93元及利息，支付律师代理费3000元，"
    "其他被告承担连带清偿责任。执行过程中拍卖部分财产，"
    "但因被执行人无其他可供执行财产，终结本次执行程序。"
)


def _normalize_spaces(text: str) -> str:
    s = re.sub(r"[ \t\r\n]+", " ", (text or "").strip())
    s = re.sub(r" +", " ", s)
    return s


def truncate_chinese(text: str, max_len: int = CASE_OUTCOME_MAX_LEN) -> str:
    """按字符数截断（中文按字计）"""
    s = _normalize_spaces(text)
    if len(s) <= max_len:
        return s
    cut = s[:max_len]
    for sep in ("。", "；", "，"):
        idx = cut.rfind(sep)
        if idx > max_len * 0.6:
            return cut[: idx + 1]
    return cut.rstrip("，、；") + "。"


def _outcome_exec_score(text: str) -> int:
    t = text or ""
    return sum(1 for m in EXEC_MARKERS if m in t)


def pick_best_outcome_text(fields: dict) -> str:
    """优先含执行/终本表述的候选，避免仅判决书内容入选"""
    candidates = []
    for key in ("结案小结", "审（办）结果", "审办结果"):
        v = (fields.get(key) or "").strip()
        if v:
            candidates.append(v)
    if not candidates:
        return ""
    return max(candidates, key=lambda t: (_outcome_exec_score(t) * 200 + len(t)))


def extract_execution_blurb(pdf_text: str, max_chars: int = 600) -> str:
    """从 OCR 全文截取执行裁定/终本段落（LLM 漏读时补全）"""
    if not pdf_text:
        return ""
    text = pdf_text.replace("\r", "\n")
    patterns = (
        r"执行裁定书[\s\S]{0,4000}?终结本次执行[\s\S]{0,1200}?[。；]",
        r"终结本次执行程序[\s\S]{0,1500}?[。；]",
        r"执行裁定书[\s\S]{0,3000}?[。；]",
        r"恢复执行[\s\S]{0,2000}?[。；]",
    )
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            blurb = _normalize_spaces(m.group(0))
            if len(blurb) > 30:
                return blurb[:max_chars]
    idx = text.find("执行裁定书")
    if idx < 0:
        idx = text.find("终结本次执行")
    if idx >= 0:
        return _normalize_spaces(text[idx : idx + max_chars])
    return ""


def _compress_exec_sentence(exec_blurb: str, max_len: int = 85) -> str:
    s = _normalize_spaces(exec_blurb)
    if not s:
        return ""
    if len(s) <= max_len:
        return s if s.endswith(("。", "；")) else s + "。"
    for sep in ("。", "；"):
        pos = s.find(sep, 30)
        if 0 < pos < max_len + 40:
            return s[: pos + 1]
    return s[:max_len].rstrip("，、；") + "。"


def synthesize_outcome_narrative(
    judgment_part: str, execution_part: str, max_len: int = CASE_OUTCOME_MAX_LEN
) -> str:
    """
    将判决书与执行裁定书分路提取的片段合成为一段连贯表述。
    结构：判决主文 + 执行过程/终本，避免简单分号拼接。
    """
    j = _normalize_spaces(judgment_part).rstrip("。；，")
    e = _normalize_spaces(execution_part).rstrip("。；，")
    if not j and not e:
        return ""
    if not j:
        return truncate_chinese(e + "。", max_len)
    if not e:
        return truncate_chinese(j + "。", max_len)
    if e in j or j in e:
        return truncate_chinese((j if len(j) >= len(e) else e) + "。", max_len)
    if _outcome_exec_score(j) >= 2:
        return truncate_chinese(j + "。", max_len)

    for prefix in (
        "执行过程中，",
        "执行过程中",
        "本案执行过程中，",
        "本院执行过程中，",
        "执行中，",
        "执行阶段，",
    ):
        if e.startswith(prefix):
            e = e[len(prefix) :].lstrip("，")
            break
    if e.startswith("执行"):
        e = e[2:].lstrip("，")

    if not j.endswith(("。", "；")):
        j = j + "。"
    if e.startswith(("因", "经", "后", "但", "遂", "故", "现", "已")):
        merged = j + e
    else:
        merged = j + "执行过程中，" + e

    merged = merged.replace("。。", "。").replace("，。", "。")
    return truncate_chinese(merged, max_len)


def ensure_outcome_covers_execution(fields: dict, pdf_text: str = "") -> dict:
    """
    若结案小结仅有判决无主文执行要点，且 PDF 含执行裁定书，则从全文补一段执行表述。
    提示词与 LLM 逻辑未删；多为长卷宗截取或模型漏读导致。
    """
    if not fields:
        return fields
    m = dict(fields)
    text = pick_best_outcome_text(m)
    if not text:
        return m
    if _outcome_exec_score(text) >= 2:
        return m
    if not pdf_text:
        return m
    if "执行裁定" not in pdf_text and "终结本次" not in pdf_text and "执" not in pdf_text:
        return m

    exec_blurb = extract_execution_blurb(pdf_text)
    if not exec_blurb:
        return m

    exec_short = _compress_exec_sentence(exec_blurb)
    if not exec_short:
        return m

    base = text.rstrip("。；，")
    if _outcome_exec_score(base) >= 1:
        exec_body = exec_short.rstrip("。；")
        for prefix in ("执行过程中，", "执行过程中"):
            if exec_body.startswith(prefix):
                exec_body = exec_body[len(prefix) :].lstrip("，")
                break
        merged = f"{base}。执行过程中，{exec_body}。"
    else:
        exec_body = exec_short.lstrip("执行").lstrip("过程中").lstrip("，")
        merged = f"{base}。执行过程中，{exec_body}"

    merged = truncate_chinese(merged, CASE_OUTCOME_MAX_LEN)
    m["结案小结"] = merged
    m["审（办）结果"] = merged
    m["审办结果"] = merged
    return m


def unify_case_outcome_fields(fields: dict) -> dict:
    """结案小结与审（办）结果使用同一综合表述（≤150字）"""
    if not fields:
        return fields
    m = dict(fields)
    text = pick_best_outcome_text(m)
    if not text:
        return m
    text = truncate_chinese(text, CASE_OUTCOME_MAX_LEN)
    m["结案小结"] = text
    m["审（办）结果"] = text
    m["审办结果"] = text
    return m
