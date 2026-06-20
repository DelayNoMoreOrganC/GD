# -*- coding: utf-8 -*-
"""结案小结/审办结果 — 法律实务表述测试"""

import case_outcome as co


def test_bankruptcy_blurb_extracted():
    text = (
        "执行裁定书……本院于2021年裁定受理被执行人某公司破产清算，"
        "本案移送破产审查，终结对被执行人的本次执行程序。"
    )
    blurb = co.extract_special_execution_blurb(text)
    assert "破产" in blurb


def test_outcome_appends_bankruptcy_when_missing():
    fields = {
        "结案小结": "法院判决被告偿还本金及利息。执行过程中查封拍卖部分财产。",
        "审（办）结果": "法院判决被告偿还本金及利息。执行过程中查封拍卖部分财产。",
    }
    pdf_text = (
        "民事判决书……判决被告偿还本金及利息。"
        "执行裁定书……执行过程中查封、拍卖部分财产，"
        "后裁定受理被执行人破产清算，本案移送破产审查，终结本次执行程序。"
    )
    out = co.ensure_outcome_covers_execution(fields, pdf_text)
    assert "破产" in out["结案小结"], out["结案小结"]
    assert "移送破产" in out["结案小结"]
    assert out["结案小结"] == out["审（办）结果"] == out["审办结果"]
    assert len(out["结案小结"]) <= co.CASE_OUTCOME_MAX_LEN


def test_no_duplicate_when_already_has_special():
    fields = {
        "结案小结": "法院判决偿还借款。执行中被执行人破产清算，移送破产审查后终结执行。",
        "审（办）结果": "法院判决偿还借款。执行中被执行人破产清算，移送破产审查后终结执行。",
    }
    pdf_text = "……破产清算……移送破产审查……"
    out = co.ensure_outcome_covers_execution(fields, pdf_text)
    assert out["结案小结"] == fields["结案小结"]


def test_settlement_and_withdraw_markers_scored():
    assert co._outcome_exec_score("双方达成执行和解，申请执行人撤回执行申请") >= 2


def test_judgment_polish_strips_execution():
    raw = "被告应偿还借款。执行过程中查封财产，终结本次执行程序。"
    polished = co._polish_judgment_clause(raw)
    assert "执行" not in polished
    assert polished.startswith("法院判决")


def test_synthesize_bankruptcy_practice_form():
    j = "法院判决被告向原告偿还借款本金及利息。"
    e = "裁定受理被执行人破产清算，本案移送破产审查，终结本次执行程序。"
    merged = co.synthesize_outcome_narrative(j, e)
    assert "破产" in merged
    assert "移送破产" in merged
    assert merged.startswith("法院判决")


def test_withdraw_no_exec_prefix():
    j = "法院判决被告向原告支付货款。"
    e = "申请执行人申请撤回执行申请，本院裁定准许。"
    merged = co.synthesize_outcome_narrative(j, e)
    assert "撤回" in merged
    assert "执行过程中，申请执行人" not in merged


def test_general_skipped_when_bankruptcy_in_pdf():
    """全文含破产时，不应仅用「无财产终本」兜底而漏写破产。"""
    fields = {"结案小结": "法院判决被告偿还借款。", "审（办）结果": "法院判决被告偿还借款。"}
    pdf_text = (
        "民事判决书……判决被告偿还借款。"
        "执行裁定书……因被执行人无其他可供执行财产，终结本次执行程序。"
        "后裁定受理被执行人破产清算，本案移送破产审查。"
    )
    out = co.ensure_outcome_covers_execution(fields, pdf_text)
    assert "破产" in out["结案小结"], out["结案小结"]


def test_zhiben_practice_template():
    blurb = "执行裁定书……查封、拍卖部分财产……无其他可供执行财产……终结本次执行程序。"
    clause = co.format_execution_for_practice(blurb, "zhiben")
    assert "终结本次执行" in clause
    assert "查封" in clause or "拍卖" in clause
