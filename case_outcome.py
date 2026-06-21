#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结案小结 / 审（办）结果：按法律实务综合判决主文与执行结果，控制字数

实务结构（律所归档常用）：
  1. 判决主文：谁向谁承担何种给付/连带责任（不写执行、终本）
  2. 执行过程：立案查控 → 特殊终结事由（破产/和解/撤回等）或常规终本
"""

import re

CASE_OUTCOME_MAX_LEN = 150

# 执行结果类型（按实务优先级：特殊终结事由优先于「无财产终本」）
OUTCOME_TYPE_RULES = (
    ("bankruptcy", ("破产", "移送破产", "破产清算", "破产重整", "受理破产", "执转破")),
    ("settlement", ("执行和解", "和解协议", "和解")),
    ("withdraw", ("撤回执行", "撤回申请", "准许撤回")),
    ("participation", ("参与分配",)),
    ("denial", ("不予执行",)),
    ("suspension", ("中止执行",)),
    ("debt_cert", ("债权凭证",)),
    ("property_offset", ("以物抵债",)),
    ("completed", ("执行完毕", "履行完毕", "自动履行", "清偿完毕", "执行终结")),
    ("zhiben", ("终结本次执行", "终本", "暂无其他可供执行", "无其他可供执行财产")),
)

SPECIAL_OUTCOME_TYPES = frozenset({
    "bankruptcy", "settlement", "withdraw", "participation",
    "denial", "suspension", "debt_cert", "property_offset",
})

SPECIAL_EXEC_MARKERS = tuple(
    m for _t, markers in OUTCOME_TYPE_RULES if _t in SPECIAL_OUTCOME_TYPES for m in markers
)

EXEC_MARKERS = (
    "执行",
    "终本",
    "终结本次",
    "拍卖",
    "查封",
    "扣划",
    "冻结",
    "可供执行",
    "恢复执行",
    "立案执行",
) + SPECIAL_EXEC_MARKERS

# 判决段与执行段的分界标记
JUDGMENT_EXEC_SPLIT_MARKERS = (
    "执行过程中",
    "执行中被执行人",
    "执行中，",
    "执行中",
    "其后，",
    "申请执行人申请撤回",
    "申请执行人撤回",
    "本院立案执行",
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


def _normalize_court_terms(text: str) -> str:
    """将执行裁定书原文中的法院自称「本院」改为第三人称「法院」。

    律所归档以第三人称转述法院行为，摘抄执行裁定书原文时不得保留「本院」。
    """
    return (text or "").replace("本院", "法院")


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


def classify_execution_outcome(text: str) -> str:
    """识别执行结果类型（破产等特殊情况优先于常规终本）。"""
    t = text or ""
    for name, markers in OUTCOME_TYPE_RULES:
        if any(m in t for m in markers):
            return name
    if "执行" in t:
        return "generic"
    return ""


def _outcome_exec_score(text: str) -> int:
    t = text or ""
    score = sum(1 for m in EXEC_MARKERS if m in t)
    # 特殊终结事由在归档中更重要，加权
    if classify_execution_outcome(t) in SPECIAL_OUTCOME_TYPES:
        score += 3
    return score


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


def _has_enforcement_measures(text: str) -> bool:
    return any(k in (text or "") for k in ("查封", "冻结", "扣划", "拍卖", "变卖", "查控"))


def _strip_exec_prefix(body: str) -> str:
    """去掉片段开头的「执行过程中」等冗余前缀，便于拼接。"""
    s = (body or "").strip()
    for prefix in (
        "本案执行过程中，",
        "本院执行过程中，",
        "执行过程中，",
        "执行过程中",
        "执行中，",
        "执行阶段，",
    ):
        if s.startswith(prefix):
            return s[len(prefix) :].lstrip("，")
    return s


def _strip_execution_from_judgment(j: str) -> str:
    """判决主文段不应夹带执行/终本表述（实务上两段分开写）。"""
    s = _normalize_spaces(j)
    for marker in JUDGMENT_EXEC_SPLIT_MARKERS + ("终结本次", "裁定终结"):
        idx = s.find(marker)
        if idx > 6:
            s = s[:idx].rstrip("。；，")
    return s


def _polish_judgment_clause(j: str) -> str:
    """规范判决主文起句，便于与执行段衔接。"""
    s = _strip_execution_from_judgment(j).rstrip("。；，")
    if not s:
        return ""
    if not s.startswith(("法院判决", "判决")):
        m = re.search(r"(法院判决|判决)", s)
        if m:
            s = s[m.start() :]
        else:
            s = "法院判决" + s.lstrip("判")
    return s


def _split_judgment_execution(text: str) -> tuple:
    """将已有综合表述拆为判决段 + 执行段。"""
    s = _normalize_spaces(text)
    for marker in JUDGMENT_EXEC_SPLIT_MARKERS:
        idx = s.find(marker)
        if idx > 6:
            return s[:idx].rstrip("。；，"), s[idx:].lstrip("，")
    return s, ""


def format_execution_for_practice(blurb: str, outcome_type: str = "", max_len: int = 88) -> str:
    """将 OCR/LLM 片段改写为律所归档常用的执行结果表述。"""
    raw = _strip_exec_prefix(_normalize_spaces(blurb))
    if not raw:
        return ""
    outcome_type = outcome_type or classify_execution_outcome(raw)
    has_measures = _has_enforcement_measures(raw)

    clause = ""
    if outcome_type == "bankruptcy":
        if "移送破产" in raw:
            clause = (
                "因被执行人被裁定受理破产清算，本案移送破产审查，"
                "本院裁定终结对被执行人的本次执行程序"
            )
        elif "受理" in raw and "破产" in raw:
            clause = "因被执行人被裁定受理破产清算，本院裁定终结对被执行人的本次执行程序"
        else:
            clause = "因被执行人进入破产程序，本院裁定终结对被执行人的本次执行程序"
        if has_measures:
            clause = f"本院立案执行并采取查控措施，其后，{clause}"
    elif outcome_type == "settlement":
        if "撤回" in raw:
            clause = "执行过程中，双方达成执行和解协议，申请执行人撤回执行申请"
        elif "终结" in raw:
            clause = "执行过程中，双方达成执行和解协议，本院裁定终结本次执行程序"
        else:
            clause = "执行过程中，双方达成执行和解协议，并按协议履行"
    elif outcome_type == "withdraw":
        clause = "申请执行人申请撤回执行申请，本院裁定准许"
    elif outcome_type == "participation":
        clause = "执行过程中，被执行人财产不足以清偿全部债务，进入参与分配程序"
        if "受偿" in raw or "分配" in raw:
            clause += "，申请执行人依法受偿"
    elif outcome_type == "denial":
        clause = "本院裁定不予执行"
    elif outcome_type == "suspension":
        clause = "本院裁定中止执行"
    elif outcome_type == "debt_cert":
        clause = "因被执行人暂无财产可供执行，本院向申请执行人发放债权凭证"
    elif outcome_type == "property_offset":
        clause = "执行过程中，裁定以涉案财产抵债清偿债务"
    elif outcome_type == "completed":
        if "自动履行" in raw:
            clause = "执行过程中，被执行人已自动履行义务，本案执行完毕"
        else:
            clause = "执行过程中，本案已全部执行完毕"
    elif outcome_type == "zhiben":
        if has_measures:
            clause = (
                "本院立案执行并采取查封、拍卖等措施，"
                "因被执行人暂无其他可供执行财产，裁定终结本次执行程序"
            )
        else:
            clause = "本院立案执行，因被执行人暂无其他可供执行财产，裁定终结本次执行程序"
    else:
        clause = raw.rstrip("。；，")

    clause = clause.rstrip("。；，")
    if not clause:
        return ""
    if len(clause) > max_len:
        clause = truncate_chinese(clause + "。", max_len).rstrip("。")
    return _normalize_court_terms(clause) + "。"


def _pick_execution_connector(judgment: str, outcome_type: str) -> str:
    """按执行结果类型选择判决段与执行段之间的衔接词。"""
    if outcome_type == "withdraw":
        return ""  # 撤回执行为独立句，实务上常直接接在判决后
    if outcome_type in SPECIAL_OUTCOME_TYPES:
        if any(x in judgment for x in ("执行过程", "执行中", "立案执行", "查封", "拍卖", "查控")):
            return "其后，"
        return "执行过程中，"
    return "执行过程中，"


def synthesize_outcome_narrative(
    judgment_part: str, execution_part: str, max_len: int = CASE_OUTCOME_MAX_LEN
) -> str:
    """
    将判决书与执行裁定书分路提取的片段合成为一段连贯表述。
    结构：判决主文 + 执行过程/终结事由（实务两段式）。
    """
    j = _polish_judgment_clause(judgment_part)
    e_type = classify_execution_outcome(execution_part)
    if _text_covers_outcome_type(execution_part, e_type) and e_type in SPECIAL_OUTCOME_TYPES:
        e_body = _strip_exec_prefix(execution_part).rstrip("。；，")
        e = e_body + "。" if e_body else ""
    else:
        e = format_execution_for_practice(execution_part, e_type)
    e_body = _strip_exec_prefix(e).rstrip("。；，")

    if not j and not e_body:
        return ""
    if not j:
        return truncate_chinese(_normalize_court_terms(e), max_len)
    if not e_body:
        return truncate_chinese(j + "。", max_len)
    if e_body in j or j in e_body:
        return truncate_chinese(
            _normalize_court_terms((j if len(j) >= len(e_body) else e_body) + "。"),
            max_len,
        )

    if not j.endswith(("。", "；")):
        j = j + "。"

    connector = _pick_execution_connector(j, e_type)
    if connector:
        if e_body.startswith(("因", "经", "后", "但", "遂", "故", "现", "已", "本院")):
            merged = j + connector + e_body + "。"
        else:
            merged = j + connector + e_body + "。"
    else:
        merged = j + e_body + "。"

    merged = merged.replace("。。", "。").replace("，。", "。")
    return truncate_chinese(_normalize_court_terms(merged), max_len)


def extract_execution_blurb(pdf_text: str, max_chars: int = 600) -> str:
    """从 OCR 全文截取执行裁定/终本段落（LLM 漏读时补全）"""
    if not pdf_text:
        return ""
    text = pdf_text.replace("\r", "\n")
    # 若存在特殊终结事由，优先抽取该段，避免只抓到「无财产终本」而漏破产等
    special = extract_special_execution_blurb(text, max_chars=max_chars)
    if special and classify_execution_outcome(special) in SPECIAL_OUTCOME_TYPES:
        return special

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


SPECIAL_EXEC_PATTERNS = (
    r"(?:裁定)?受理[^。；\n]{0,40}破产[\s\S]{0,300}?[。；]",
    r"移送破产审查[\s\S]{0,200}?[。；]",
    r"(?:进入|宣告|裁定)[^。；\n]{0,20}破产[\s\S]{0,300}?[。；]",
    r"[^。；\n]{0,30}破产[\s\S]{0,300}?(?:终结|移送|受理|清算|重整)[\s\S]{0,150}?[。；]",
    r"参与分配[\s\S]{0,300}?[。；]",
    r"(?:达成)?执行和解[\s\S]{0,300}?[。；]",
    r"撤回执行(?:申请)?[\s\S]{0,200}?[。；]",
    r"裁定不予执行[\s\S]{0,200}?[。；]",
    r"中止执行[\s\S]{0,200}?[。；]",
    r"(?:发放|出具)[^。；\n]{0,10}债权凭证[\s\S]{0,150}?[。；]",
    r"以物抵债[\s\S]{0,200}?[。；]",
)


def extract_special_execution_blurb(pdf_text: str, max_chars: int = 400) -> str:
    """从 OCR 全文截取「执行特殊情况」段落。"""
    if not pdf_text:
        return ""
    text = pdf_text.replace("\r", "\n")
    for pat in SPECIAL_EXEC_PATTERNS:
        m = re.search(pat, text)
        if m:
            blurb = _normalize_spaces(m.group(0))
            if len(blurb) > 8:
                return blurb[:max_chars]
    for name, markers in OUTCOME_TYPE_RULES:
        if name not in SPECIAL_OUTCOME_TYPES:
            continue
        for kw in markers:
            idx = text.find(kw)
            if idx >= 0:
                return _normalize_spaces(text[idx : idx + max_chars])
    return ""


def _compress_exec_sentence(exec_blurb: str, max_len: int = 85) -> str:
    """兼容旧调用：压缩后走实务格式化。"""
    return format_execution_for_practice(exec_blurb, max_len=max_len)


def _set_outcome(fields: dict, text: str) -> dict:
    fields["结案小结"] = text
    fields["审（办）结果"] = text
    fields["审办结果"] = text
    return fields


def _text_covers_outcome_type(text: str, outcome_type: str) -> bool:
    """判断现有表述是否已覆盖该执行结果类型。"""
    if not text or not outcome_type:
        return False
    detected = classify_execution_outcome(text)
    if detected == outcome_type:
        return True
    if outcome_type == "bankruptcy" and "破产" in text:
        return True
    if outcome_type == "settlement" and "和解" in text:
        return True
    if outcome_type == "withdraw" and "撤回" in text:
        return True
    return False


def _ensure_special_execution(m: dict, pdf_text: str) -> dict:
    """执行特殊情况兜底：破产/和解/撤回等须写入，且优先于「无财产终本」。"""
    if not pdf_text:
        return m

    pdf_type = classify_execution_outcome(pdf_text)
    if pdf_type not in SPECIAL_OUTCOME_TYPES:
        return m

    text = pick_best_outcome_text(m) or ""
    if _text_covers_outcome_type(text, pdf_type):
        return m

    blurb = extract_special_execution_blurb(pdf_text)
    if not blurb:
        return m

    j_part, e_part = _split_judgment_execution(text)
    j_part = _polish_judgment_clause(j_part) if j_part else ""
    special_clause = format_execution_for_practice(blurb, pdf_type)

    if j_part and e_part and not _text_covers_outcome_type(e_part, pdf_type):
        # 已有常规执行段但缺特殊事由：用「其后，」补写
        e_body = _strip_exec_prefix(special_clause).rstrip("。；，")
        connector = "其后，" if "执行" in e_part or _has_enforcement_measures(e_part) else "执行过程中，"
        merged = f"{j_part}。{e_part.rstrip('。；，')}。{connector}{e_body}。"
    elif j_part:
        merged = synthesize_outcome_narrative(j_part, special_clause)
    else:
        merged = special_clause

    merged = merged.replace("。。", "。").replace("，。", "。")
    merged = truncate_chinese(merged, CASE_OUTCOME_MAX_LEN)
    return _set_outcome(m, merged)


def _ensure_general_execution(m: dict, pdf_text: str) -> dict:
    """常规终本兜底（仅在没有特殊终结事由时使用）。"""
    text = pick_best_outcome_text(m)
    if not text:
        return m
    if _outcome_exec_score(text) >= 2:
        return m
    if not pdf_text:
        return m

    pdf_type = classify_execution_outcome(pdf_text)
    # 全文含破产/和解等特殊事由时，不用「无财产终本」兜底，避免写错终结原因
    if pdf_type in SPECIAL_OUTCOME_TYPES:
        return m
    if "执行裁定" not in pdf_text and "终结本次" not in pdf_text and "执" not in pdf_text:
        return m

    exec_blurb = extract_execution_blurb(pdf_text)
    if not exec_blurb:
        return m

    j_part, _ = _split_judgment_execution(text)
    j_part = _polish_judgment_clause(j_part) if j_part else text.rstrip("。；，")
    exec_clause = format_execution_for_practice(exec_blurb, classify_execution_outcome(exec_blurb))
    merged = synthesize_outcome_narrative(j_part, exec_clause)
    if not merged:
        return m
    return _set_outcome(m, merged)


def polish_outcome_for_practice(fields: dict, pdf_text: str = "") -> dict:
    """终稿润色：规范判决起句、按执行结果类型改写表述、重新合成。"""
    if not fields:
        return fields
    m = dict(fields)
    text = pick_best_outcome_text(m)
    if not text:
        return m

    j_part, e_part = _split_judgment_execution(text)
    j_part = _polish_judgment_clause(j_part)

    pdf_type = classify_execution_outcome(pdf_text) if pdf_text else ""
    if not e_part and pdf_text and pdf_type not in ("", "generic"):
        if not _text_covers_outcome_type(text, pdf_type):
            blurb = extract_special_execution_blurb(pdf_text) or extract_execution_blurb(pdf_text)
            if blurb:
                e_part = format_execution_for_practice(blurb, pdf_type)

    if j_part and e_part:
        e_type = classify_execution_outcome(e_part)
        if _text_covers_outcome_type(e_part, e_type):
            j = j_part if j_part.endswith("。") else j_part + "。"
            e_clean = e_part.rstrip("。；，") + "。"
            merged = truncate_chinese(j + e_clean)
        else:
            merged = synthesize_outcome_narrative(j_part, e_part)
    elif j_part:
        merged = truncate_chinese(j_part + "。")
    elif e_part:
        merged = truncate_chinese(format_execution_for_practice(e_part))
    else:
        merged = truncate_chinese(text)

    return _set_outcome(m, merged)


def ensure_outcome_covers_execution(fields: dict, pdf_text: str = "") -> dict:
    """
    1. 特殊终结事由优先补写（破产/和解/撤回等）
    2. 无特殊事由时再补常规终本
    3. 终稿按法律实务润色合成
    """
    if not fields:
        return fields
    m = dict(fields)
    m = _ensure_special_execution(m, pdf_text)
    m = _ensure_general_execution(m, pdf_text)
    m = polish_outcome_for_practice(m, pdf_text)
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
