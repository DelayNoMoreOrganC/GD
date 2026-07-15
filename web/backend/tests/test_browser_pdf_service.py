from __future__ import annotations

import os

import fitz
import pytest

from app.config import get_settings
from app.services.analysis_snapshot import SYSTEM_TEMPLATE_NAMES
from app.services.browser_pdf_service import FORM_LAYOUTS, render_form_html, render_form_pdf


SAMPLE_FIELDS = {
    "案件类别": "民事",
    "委托人": "甲方 <测试>",
    "当事人": "甲方",
    "对方当事人": "乙方",
    "法院收案号": "（2026）粤0604民初1号",
    "结案小结": "判决后进入执行程序，法院采取网络查控和限制消费措施。",
    "法院文件清单": "民事判决书\n执行裁定书",
    "_preview_styles": {"档案卷宗": {"field:结案小结": {"fontSize": "9pt", "textAlign": "justify"}}},
    "_preview_custom_values": {"立案审批表": {"p0-b0-r6-c0": "同意承办。"}},
}


def test_backend_layouts_cover_all_browser_forms():
    assert set(FORM_LAYOUTS) == set(SYSTEM_TEMPLATE_NAMES)


def test_render_form_html_uses_saved_values_styles_and_escapes_input():
    rendered = render_form_html("立案审批表", SAMPLE_FIELDS, "广东至高律师事务所")
    assert "广东至高律师事务所制" in rendered
    assert "甲方 &lt;测试&gt;" in rendered
    assert "同意承办。" in rendered
    assert "<测试>" not in rendered

    archive = render_form_html("档案卷宗", SAMPLE_FIELDS, "广东至高律师事务所")
    assert "font-size:9pt" in archive
    assert "text-align:justify" in archive


@pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_PDF_TESTS") != "1" or not get_settings().chromium_executable,
    reason="set RUN_BROWSER_PDF_TESTS=1 to exercise local Chrome",
)
def test_chromium_generates_a4_pdf(tmp_path):
    output = tmp_path / "质量监督卡.pdf"
    render_form_pdf("质量监督卡", SAMPLE_FIELDS, "广东至高律师事务所", str(output), log=lambda _msg: None)
    with fitz.open(output) as document:
        assert document.page_count == 2
        assert all(abs(page.rect.width - 595.28) <= 3 for page in document)
        assert all(abs(page.rect.height - 841.89) <= 3 for page in document)
    assert output.stat().st_size > 10_000
