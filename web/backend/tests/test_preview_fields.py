import pytest

from app.services.preview_fields import (
    build_preview,
    sanitize_preview_custom_values,
    sanitize_preview_styles,
    sanitize_preview_updates,
)


@pytest.mark.parametrize(
    ("case_label", "expected_label"),
    [
        ("刑事", "被告人／犯罪嫌疑人"),
        ("行政", "行政相对人／本所代理方"),
        ("非诉", "项目委托人"),
        ("法律顾问", "顾问单位"),
    ],
)
def test_preview_uses_case_specific_role_labels(case_label, expected_label):
    preview = build_preview("档案卷宗", {"案件类别": case_label, "当事人": "甲"})
    by_key = {item["key"]: item for item in preview["fields"]}
    assert by_key["当事人"]["label"] == expected_label
    assert by_key["当事人"]["value"] == "甲"


def test_preview_update_rejects_fields_outside_selected_form():
    cleaned = sanitize_preview_updates(
        "质量监督卡",
        {"委托人": "不应写入", "法院收案号": "（2024）粤0605号", "承办律师": "李律师"},
    )
    assert cleaned == {"法院收案号": "（2024）粤0605号", "承办律师": "李律师"}


def test_preview_fields_follow_word_template_writable_cells():
    close_report = build_preview("结案报告表", {})
    assert [item["key"] for item in close_report["fields"]] == [
        "案件类别",
        "委托人",
        "案件或项目名称",
        "结案小结",
        "应收业务费",
        "已收业务费",
        "尚欠业务费",
        "应退业务费",
        "结案日期",
    ]

    quality_card = build_preview("质量监督卡", {})
    assert [item["key"] for item in quality_card["fields"]] == [
        "法院收案号",
        "承办律师",
        "委托人联系地址及电话",
    ]


def test_preview_styles_keep_only_supported_cell_formatting():
    cleaned = sanitize_preview_styles(
        "送达材料清单",
        {
            "line:法院文件清单:0": {
                "fontFamily": 'KaiTi, STKaiti, "Noto Serif CJK SC", serif',
                "fontSize": "14pt",
                "fontWeight": "bold",
                "textAlign": "center",
                "color": "#AABBCC",
                "position": "fixed",
            },
            "invalid:key:extra": {"fontSize": "100pt"},
        },
    )
    assert cleaned == {
        "line:法院文件清单:0": {
            "fontFamily": 'KaiTi, STKaiti, "Noto Serif CJK SC", serif',
            "fontSize": "14pt",
            "fontWeight": "bold",
            "textAlign": "center",
            "color": "#aabbcc",
        }
    }


def test_preview_custom_text_boxes_use_stable_layout_keys():
    cleaned = sanitize_preview_custom_values(
        "立案审批表",
        {
            "p0-b0-r6-c0": "承办律师补充意见",
            "../../unsafe": "ignored",
            "p0-b0-r99-c1": "x" * 6000,
        },
    )
    assert cleaned["p0-b0-r6-c0"] == "承办律师补充意见"
    assert len(cleaned["p0-b0-r99-c1"]) == 5000
    assert "../../unsafe" not in cleaned
