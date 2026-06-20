# -*- coding: utf-8 -*-
"""模板字段槽位映射：原被告拆分、占位符不串格。"""

from field_mapping import expand_fields_for_template
from field_sanitize import enrich_party_fields, parse_litigation_parties
from lian_approval_fill import expand_lian_fields


def test_parse_litigation_parties_labeled():
    pl, df = parse_litigation_parties("原告：兴泰贸易有限公司，被告：张三")
    assert pl == "兴泰贸易有限公司"
    assert df == "张三"


def test_parse_litigation_parties_su_format():
    pl, df = parse_litigation_parties("兴泰贸易有限公司诉张三借款合同纠纷一案")
    assert pl == "兴泰贸易有限公司"
    assert "张三" in df


def test_enrich_splits_combined_party():
    raw = {
        "委托人": "兴泰贸易有限公司",
        "当事人": "原告：兴泰贸易有限公司，被告：张三",
        "承办律师": "张鑫莹",
        "判决书上代理律师": "张鑫莹",
    }
    m = enrich_party_fields(raw)
    assert m["委托人"] == "兴泰贸易有限公司"
    assert m["判决书中的原告"] == "兴泰贸易有限公司"
    assert m["判决书中的被告"] == "张三"
    assert m["判决书上代理律师"] == "张鑫莹"


def test_archive_template_no_cross_slot_fallback():
    m = enrich_party_fields({
        "委托人": "甲公司",
        "当事人": "原告：甲公司，被告：乙公司",
        "判决书中的原告": "甲公司",
        "判决书中的被告": "乙公司",
        "承办律师": "李律师",
        "判决书上代理律师": "李律师",
        "案由": "借款合同纠纷",
        "审理法院": "广东省佛山市中级人民法院",
        "案件类别": "民事",
    })
    mapped = expand_fields_for_template("档案卷宗", m)
    assert mapped["委托代理合同中委托人"] == "甲公司"
    assert mapped["判决书中的原告"] == "甲公司"
    assert mapped["判决书中的被告"] == "乙公司"
    assert mapped["判决书原告的委托诉讼代理人"] == "李律师"


def test_delivery_list_plaintiff_not_blob():
    m = enrich_party_fields({
        "当事人": "原告：甲公司，被告：乙公司",
        "判决书上代理律师": "王律师",
    })
    mapped = expand_fields_for_template("送达材料清单", m)
    assert mapped["判决书上的原告"] == "甲公司"
    assert mapped["判决书上代理律师"] == "王律师"


def test_bank_plaintiff_fallback_from_client():
    m = enrich_party_fields({
        "委托人": "东莞银行股份有限公司佛山分行",
        "对方当事人": "潘超，男，1985年12月1日出生",
        "判决书上代理律师": "招伟松",
    })
    assert m["判决书中的原告"] == "东莞银行股份有限公司佛山分行"
    assert m["判决书中的被告"] == "潘超"


def test_lian_party_and_client_separate():
    m = enrich_party_fields({
        "委托人": "甲公司",
        "当事人": "原告：甲公司，被告：乙公司、丙公司",
        "判决书中的被告": "乙公司、丙公司",
        "判决书中的原告": "甲公司",
    })
    lian = expand_lian_fields(m)
    assert lian["3"] == "甲公司"
    assert lian["4"] == "甲公司"
    assert "乙公司" in lian["8"]
