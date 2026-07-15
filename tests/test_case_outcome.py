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


def test_extract_judgment_operative_strips_appeal():
    text = (
        "民事判决书\n判决如下：\n"
        "一、被告向原告偿还借款本金100万元及利息；\n"
        "二、案件受理费由被告负担。\n"
        "如不服本判决，可以在判决书送达之日起十五日内上诉。\n"
        "审判员 张三"
    )
    out = co.extract_judgment_operative(text)
    assert "借款" in out
    assert "如不服" not in out
    assert out.startswith("法院判决")


def test_extract_judgment_operative_mediation():
    text = (
        "民事调解书\n调解协议内容如下：\n"
        "被告分期偿还原告货款50万元。\n"
        "本调解书经双方当事人签收后生效。"
    )
    out = co.extract_judgment_operative(text)
    assert "货款" in out or "偿还" in out


def test_no_forced_zhiben_without_execution_units():
    fields = {"结案小结": "法院判决被告偿还借款。", "审（办）结果": "法院判决被告偿还借款。"}
    pdf_text = "民事判决书……判决被告偿还借款。执行裁定书……终结本次执行程序。"
    units = []
    out = co.ensure_outcome_covers_execution(fields, pdf_text, units=units)
    assert "终结本次" not in out["结案小结"], out["结案小结"]


def test_detect_outcome_warning_fake_zhiben():
    fields = {"结案小结": "法院判决偿还借款。执行过程中，无财产可供执行，终结本次执行程序。"}
    warnings = co.detect_outcome_warnings(fields, units=[], pdf_text="")
    assert any("seq15" in w or "执行文书" in w for w in warnings)


def test_build_outcome_from_units_judgment_only():
    class _U:
        def __init__(self, seq, path="a.pdf", sp=0, ep=0):
            self.catalog_seq = seq
            self.source_path = path
            self.start_page = sp
            self.end_page = ep

    j_text = "民事判决书\n判决如下：\n被告向原告支付货款30万元。\n如不服本判决"
    pages = {"a.pdf": [j_text]}
    units = [_U(14)]
    fields = co.build_outcome_from_units(
        {"结案小结": "错误归纳"},
        units,
        {"a.pdf": [j_text]},
    )
    assert "货款" in fields.get("结案小结", "")
    assert "终结本次" not in fields.get("结案小结", "")


def test_build_outcome_from_units_with_execution():
    class _U:
        def __init__(self, seq, path="a.pdf", sp=0, ep=0):
            self.catalog_seq = seq
            self.source_path = path
            self.start_page = sp
            self.end_page = ep

    j_text = "民事判决书\n判决如下：\n被告向原告偿还借款。\n如不服"
    e_text = "执行裁定书……无其他可供执行财产，终结本次执行程序。"
    units = [_U(14, sp=0, ep=0), _U(15, sp=1, ep=1)]
    page_texts = {"a.pdf": [j_text, e_text]}
    fields = co.build_outcome_from_units({}, units, page_texts)
    out = fields.get("结案小结", "")
    assert "偿还" in out
    assert "终结本次" in out or "执行" in out


def test_apply_outcome_type_none_strips_execution():
    fields = {
        "结案小结": "法院判决被告偿还借款。执行过程中，无财产可供执行，终结本次执行程序。",
    }
    out = co.apply_outcome_type_override(fields, "none")
    assert "终结本次" not in out["结案小结"]
    assert "偿还" in out["结案小结"]


def test_apply_outcome_type_withdraw():
    fields = {"结案小结": "法院判决被告支付货款。"}
    out = co.apply_outcome_type_override(fields, "withdraw")
    assert "撤回" in out["结案小结"]


def test_execution_not_completed_when_text_says_not_fully_performed():
    text = (
        "被执行人未履行完毕生效法律文书确定的义务，法院采取预查封、冻结措施，"
        "未发现其他可供执行财产，裁定终结本次执行程序。"
    )
    assert co.classify_execution_outcome(text) == "zhiben"


def test_long_judgment_reserves_space_for_real_execution_measures():
    judgment = (
        "被告聂彦龙应于本判决发生法律效力之日起十日内向原告某银行偿还"
        "借款本金44496.97元、利息2717.31元、罚息1952.19元及复利270.42元。"
    )
    execution = (
        "执行过程中，法院预查封被执行人共有房产份额，冻结网络支付账户，"
        "通过网络查控未发现其他可供执行财产，并采取限制消费措施，"
        "裁定终结本次执行程序。"
    )
    out = co.synthesize_outcome_narrative(judgment, execution)
    assert out.startswith("法院判决")
    assert "预查封" in out and "冻结" in out and "网络查控" in out
    assert "终结本次执行" in out
    assert "拍卖" not in out
    assert len(out) <= co.CASE_OUTCOME_MAX_LEN
