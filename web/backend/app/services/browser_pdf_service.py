"""Render the five editable browser forms to PDF without Microsoft Word."""
from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import fitz

from ..config import get_settings
from .analysis_snapshot import SYSTEM_TEMPLATE_NAMES
from .preview_fields import (
    build_preview,
    sanitize_preview_custom_values,
    sanitize_preview_styles,
)


def _cell(**kwargs):
    return kwargs


def _row(height: float, *cells):
    return {"height": height, "cells": list(cells)}


def _table(columns, rows, class_name=""):
    return {"type": "table", "columns": columns, "rows": rows, "className": class_name}


APPROVAL_TABLE = _table(
    [18.9, 20.8, 11.3, 13.2, 35.8],
    [
        _row(8.2, _cell(text="案件类别", align="center"), _cell(field="案件类别", align="center"), _cell(text="合同号", align="center"), _cell(field="合同号", colspan=2)),
        _row(8.2, _cell(text="委 托 人", align="center"), _cell(field="委托人", colspan=2), _cell(text="当事人", align="center"), _cell(field="当事人")),
        _row(8.2, _cell(text="委托人电话", align="center"), _cell(field="委托人电话", colspan=2), _cell(text="传 真", align="center"), _cell(text="")),
        _row(8, _cell(text="收费标准", align="center"), _cell(field="收费标准"), _cell(text="地 址", align="center"), _cell(field="地址", colspan=2)),
        _row(8.5, _cell(text="对方当事人", align="center"), _cell(field="对方当事人", colspan=4)),
        _row(25, _cell(prefix="案情简介：", field="案情简介", colspan=5, multiline=True, className="top-cell")),
        _row(35, _cell(text="承办律师意见：", colspan=5, align="left", className="top-cell", allowCustomInput=True)),
        _row(35, _cell(text="主任审批意见：", colspan=5, align="left", className="top-cell", allowCustomInput=True)),
        _row(9, _cell(prefix="立案日期：", field="收案日期", colspan=5)),
        _row(12, _cell(text="备  注：", colspan=5, align="left", className="top-cell", allowCustomInput=True)),
    ],
)

ARCHIVE_TABLE = _table(
    [18.7, 20.8, 12.1, 16.1, 3.8, 28.5],
    [
        _row(8, _cell(text="案件类别", align="center"), _cell(field="案件类别", align="center"), _cell(text="合同号", align="center"), _cell(field="合同号", colspan=3)),
        _row(8, _cell(text="承办律师", align="center"), _cell(field="承办律师", colspan=5)),
        _row(8, _cell(text="委 托 人", align="center"), _cell(field="委托人", colspan=5)),
        _row(8, _cell(text="当 事 人", align="center"), _cell(field="当事人", colspan=5)),
        _row(8, _cell(text="对方当事人", align="center"), _cell(field="对方当事人", colspan=5)),
        _row(15, _cell(text="案   由", align="center"), _cell(field="案由", colspan=5, multiline=True)),
        _row(10.8, _cell(text="收案日期", align="center"), _cell(field="收案日期", colspan=2, align="center"), _cell(text="结案日期", align="center"), _cell(field="结案日期", colspan=2, align="center")),
        _row(14.6, _cell(text="审理法院", align="center"), _cell(field="审理法院", colspan=2, multiline=True), _cell(text="审 级", align="center"), _cell(field="审级", colspan=2, align="center")),
        _row(19, _cell(text="法院收案号", align="center"), _cell(field="法院收案号", colspan=5, multiline=True)),
        _row(23, _cell(text="审（办）结果", align="center"), _cell(field="结案小结", colspan=5, multiline=True)),
        _row(9, _cell(text="归档日期", align="center"), _cell(field="归档日期", colspan=5, align="center")),
        _row(10, _cell(text="立 卷 人", align="center"), _cell(field="立卷人", colspan=2, align="center"), _cell(text="卷内页数", colspan=2, align="center"), _cell(text="页", align="right")),
        _row(10, _cell(text="档 案 号", align="center"), _cell(text="", colspan=2), _cell(text="保存年限", colspan=2, align="center"), _cell(text="")),
        _row(11, _cell(text="备    注", align="center"), _cell(text="", colspan=5)),
    ],
)

CLOSE_REPORT_TABLE = _table(
    [11.2, 7.3, 6.8, 29.3, 7.8, 10.3, 0.8, 26.8],
    [
        _row(12, _cell(text="案  件  类  别", colspan=3, align="center"), _cell(field="案件类别", colspan=5, align="center")),
        _row(12, _cell(text="委 托 人 名 称", colspan=3, align="center"), _cell(field="委托人", colspan=5)),
        _row(12, _cell(text="案件或项目名称", colspan=3, align="center"), _cell(field="案件或项目名称", colspan=5, multiline=True)),
        _row(43.4, _cell(text="结\n案\n小\n结", align="center"), _cell(field="结案小结", colspan=7, multiline=True, className="top-cell")),
        _row(44, _cell(text="委\n托\n人\n对\n服\n务\n质\n量\n意\n见", align="center", className="vertical-label"), _cell(text="委托人对承办律师服务质量表示满意。", colspan=7, className="top-cell")),
        _row(12, _cell(text="应收业务费", colspan=2, align="center"), _cell(field="应收业务费", colspan=2, align="center"), _cell(text="已收业务费", colspan=3, align="center"), _cell(field="已收业务费", align="center")),
        _row(12, _cell(text="尚欠业务费", colspan=2, align="center"), _cell(field="尚欠业务费", colspan=2, align="center"), _cell(text="应退业务费", colspan=3, align="center"), _cell(field="应退业务费", align="center")),
        _row(20.7, _cell(text="承办律师\n意    见", colspan=2, align="center"), _cell(text="", colspan=6)),
        _row(22, _cell(text="主    任\n审批意见", colspan=2, align="center"), _cell(text="", colspan=6)),
        _row(12, _cell(text="结案日期", colspan=2, align="center"), _cell(field="结案日期", colspan=3, align="center"), _cell(text="备注", align="center"), _cell(text="", colspan=2)),
    ],
)

QUALITY_TABLE = _table(
    [13.3, 6.7, 20, 4.4, 17.8, 37.8],
    [
        _row(8.1, _cell(text="律师事务所", colspan=2, align="center"), _cell(organizationName=True, colspan=4, align="center")),
        _row(8.2, _cell(text="案号", align="center"), _cell(field="法院收案号", colspan=3), _cell(text="承办律师", align="center"), _cell(field="承办律师")),
        _row(8, _cell(text="委托人联系地址及电话", colspan=3, align="center"), _cell(field="委托人联系地址及电话", colspan=3)),
    ],
)

DELIVERY_ROWS = [
    _row(20, _cell(text="序号", align="center"), _cell(text="材料名称", align="center"), _cell(text="页数", align="center"), _cell(text="送达\n时间", align="center"), _cell(text="送达人", align="center"), _cell(text="接收人", align="center"), _cell(text="备注", align="center")),
    _row(12.5, _cell(text="1", align="center"), _cell(text="委托代理合同", align="center"), _cell(text=""), _cell(text=""), _cell(text=""), _cell(text=""), _cell(text="")),
    _row(13, _cell(text="2", align="center"), _cell(text="委托人须知", align="center"), _cell(text="1", align="center"), _cell(text=""), _cell(text=""), _cell(text=""), _cell(text="")),
    _row(13, _cell(text="3", align="center"), _cell(text="律师所收款发票", align="center"), _cell(text="1", align="center"), _cell(text=""), _cell(text=""), _cell(text=""), _cell(text="")),
    _row(12.5, _cell(text="4", align="center"), _cell(text="质量监督卡", align="center"), _cell(text="1", align="center"), _cell(text=""), _cell(text=""), _cell(text=""), _cell(text="")),
]
for index in range(5):
    DELIVERY_ROWS.append(_row(13, _cell(text=str(index + 5), align="center"), _cell(linesField="法院文件清单", lineIndex=index, multiline=True), *[_cell(text="") for _ in range(5)]))
DELIVERY_ROWS.append(_row(12.5, *[_cell(text="") for _ in range(7)]))
DELIVERY_TABLE = _table([6.9, 28.3, 6.6, 16.6, 12.9, 12.9, 10.2], DELIVERY_ROWS)

QUALITY_QUESTIONS = [
    "是否由律师事务所与委托人签订委托代理合同",
    "是否由律师事务所向委托人收取律师费并如实出具发票",
    "接受委托后承办律师是否在律师费外收取了其他额外报酬或财物",
    "接受委托前承办律师是否向委托人作过虚假承诺",
    "接受委托后承办律师是否有无正当理由而不按时出庭参加诉讼、仲裁或有其他拒绝辩护、代理现象",
    "接受委托后承办律师是否有敷衍推诿、不尽职尽责的现象",
    "在委托代理合同中约定代收有关法律文书的，承办律师是否及时向委托人送达判决书、调解书、裁定书等法律文书",
    "承办律师与委托人是否办妥本案有关证据资料的交接手续",
]

CLIENT_NOTICE = [
    "为了保障委托人、律师事务所及律师各方的合法权益，根据《中华人民共和国律师法》及《律师执业行为规范》等有关规定，律师接受委托的，应当告知委托人如下事项：",
    "一、委托人要求律师办理的事项应当合法，不得要求律师通过不正当手段与办案机关、政府部门及其工作人员进行沟通，不得要求承办律师对委托事项的办理结果作出承诺。",
    "二、委托人应当按照委托合同的约定，按时、足额支付律师费。以下情况律师事务所不予退费：（1）委托人同时委托他人的；（2）律师完成委托事项后，无正当理由委托人认为结果不理想，或者认为律师事务所收费过高的；（3）非因受托人原因，委托人终止委托合同的；（4）委托合同约定的其他情形。",
    "三、委托人的委托的诉讼或非诉讼事项均具有不同程度的法律风险，律师承办的业务受到办案机关、政府部门和相关当事方的制约，委托人的主张及律师的法律意见有部分或全部不被采纳的可能。",
    "四、委托人有权向承办律师了解委托事项的办理情况。",
    "五、律师执业必须遵守宪法和法律，恪守律师职业道德和执业纪律。律师执业必须以事实为根据，以法律为准绳。",
    "六、律师不得以诋毁其他律师事务所、律师，支付介绍费，向当事人明示或者暗示与办案机关、政府部门及其工作人员有特殊关系等不正当手段承揽业务，不得以不实宣传等方式承揽业务。",
    "七、律师承办业务，须由律师事务所与委托人签订书面委托合同，按有关规定收取律师费，并向委托人统一开具发票。律师不得私自接受委托，私自向委托人收取费用或财物。",
    "八、律师不得以非律师身份从事法律服务。",
    "九、委托人发现承办律师在履行委托合同过程中执业有违规行为的，可以向承办律师所在律师所、律师协会及司法行政部门投诉。",
    "委托人确认，委托人已知晓上述内容。",
]

FORM_LAYOUTS = {
    "立案审批表": [{"title": "立 案 审 批 表", "subtitleFromOrganization": True, "blocks": [APPROVAL_TABLE]}],
    "档案卷宗": [{"title": "律师业务档案卷宗（诉讼类）", "subtitleFromOrganization": True, "titleClass": "archive-title", "blocks": [ARCHIVE_TABLE]}],
    "结案报告表": [{"title": "结 案 报 告 表", "subtitleFromOrganization": True, "blocks": [CLOSE_REPORT_TABLE]}],
    "送达材料清单": [{
        "title": "律师所送达材料清单",
        "blocks": [
            {"type": "paragraph", "className": "delivery-meta case-number", "runs": [{"text": "案号："}, {"field": "法院收案号"}]},
            {"type": "paragraph", "className": "delivery-meta", "runs": [{"text": "委托方："}, {"field": "委托人"}]},
            {"type": "paragraph", "className": "delivery-meta", "runs": [{"text": "承办律师："}, {"field": "承办律师"}]},
            {"type": "text", "className": "delivery-note", "text": "律师在接办案件中填写，若送达给当事人的内容多，律师可视情况在空白栏目添加。"},
            DELIVERY_TABLE,
        ],
    }],
    "质量监督卡": [
        {"title": "律 师 办 案 质 量 监 督 卡", "blocks": [
            QUALITY_TABLE,
            {"type": "questions", "questions": QUALITY_QUESTIONS},
            {"type": "text", "className": "quality-evaluation", "text": "9、对承办律师办理本案总的评价　　好□　较好□　一般□　较差□　差□"},
            {"type": "text", "className": "quality-suggestion", "text": "10、对律师办理本案的意见和建议（内容较多可另附页）"},
            {"type": "text", "className": "quality-signature", "text": "委托人（签章）：　　　　　　　　　年　　月　　日"},
            {"type": "text", "className": "quality-note", "text": "说明：此卡由律师事务所在办理委托手续时，与背面的《委托人须知》一起发给委托人，由委托人签收。案件办结后，请委托人填写此卡并及时交回律师事务所；如有不便，也可直接将此卡交该律师事务所的主管司法局或市律师协会。"},
        ]},
        {"title": "委 托 人 须 知", "subtitle": "（2004年11月5日广东省律师协会第七届理事会第五次会议通过，2018年2月8日广东省律师协会第十一届常务理事会第八次会议修订）", "titleClass": "notice-title", "blocks": [
            *[{"type": "text", "className": "notice-paragraph", "text": text} for text in CLIENT_NOTICE],
            {"type": "text", "className": "notice-signature", "text": "委托人（签章）：　　　　　　　　　年　　月　　日"},
            {"type": "text", "className": "complaint-phones", "text": "投诉电话：\n佛山市司法局：83331692　　佛山市律师协会：83321801\n禅城区司法局：66611111--4　南海区司法局：81210925\n顺德区司法局：22830122　　三水区司法局：87731873\n高明区司法局：88882966"},
        ]},
    ],
}


CSS = r"""
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; color: #000; }
.form-page { position: relative; width: 210mm; min-height: 297mm; padding: 17mm 20mm 16mm; break-after: page; font-family: SimSun, "Songti SC", "Noto Serif CJK SC", serif; font-size: 10.5pt; }
.form-page:last-child { break-after: auto; }
h1 { margin: 0 0 7mm; text-align: center; font-size: 20pt; font-weight: 500; letter-spacing: .42em; line-height: 1.25; }
h1.archive-title { font-size: 18pt; letter-spacing: .16em; }
h1.notice-title { margin-bottom: 2mm; font-size: 18pt; }
.page-subtitle { margin: -4mm 0 3mm; text-align: right; font-size: 9pt; white-space: pre-line; }
.quality-card .page-subtitle { margin: 0 8mm 6mm; text-align: center; line-height: 1.5; }
table { width: 100%; table-layout: fixed; border-collapse: collapse; border: 1.2px solid #000; break-inside: auto; }
tr { break-inside: avoid; }
td { position: relative; padding: 0; border: 1px solid #000; vertical-align: middle; white-space: pre-line; overflow-wrap: anywhere; }
td.top-cell { vertical-align: top; }
.cell-value, .fixed-text { display: block; min-height: 7mm; padding: 1.1mm 1.5mm; line-height: 1.35; white-space: pre-wrap; word-break: break-word; }
.vertical-label .fixed-text { line-height: 1.05; }
.prefix-field { display: flex; min-height: 7mm; align-items: stretch; }
.cell-prefix { flex: none; padding: 1.3mm 0 1.3mm 1.5mm; line-height: 1.35; white-space: nowrap; }
.prefix-field .cell-value { flex: 1; padding-left: .5mm; }
.custom-prompt { padding-bottom: .5mm; }
.custom-value { min-height: 5mm; padding-top: 0; }
.delivery-meta { display: flex; align-items: baseline; width: 55%; margin: 0 0 1.5mm; line-height: 7mm; }
.delivery-meta.case-number { margin-top: -2mm; }
.line-value { display: inline-block; flex: 1; min-height: 7mm; padding: 0 1mm; border-bottom: .3px solid #777; white-space: pre-wrap; }
.delivery-note { margin: 0 0 3mm; text-align: right; font-size: 8.5pt; }
.quality-questions { margin: 4mm 0 0; padding-left: 6mm; font-size: 10pt; line-height: 1.45; }
.quality-questions li { position: relative; min-height: 8mm; padding: 0 26mm 0 1mm; }
.checkboxes { position: absolute; top: 0; right: 0; white-space: nowrap; }
.quality-evaluation, .quality-suggestion, .quality-signature, .quality-note { white-space: pre-line; font-size: 9.5pt; line-height: 1.45; }
.quality-evaluation { margin: 2mm 0 3mm; } .quality-suggestion { min-height: 22mm; margin: 0; }
.quality-signature { margin: 0 0 4mm; text-align: right; } .quality-note { margin: 0; text-indent: 2em; }
.notice-paragraph { margin: 0 0 2.2mm; text-align: justify; text-indent: 2em; font-size: 10.5pt; line-height: 1.55; }
.notice-signature { margin: 6mm 0 7mm; text-align: right; white-space: pre; }
.complaint-phones { margin: 0; line-height: 1.7; white-space: pre-line; }
.page-number { position: absolute; right: 0; bottom: 8mm; left: 0; text-align: center; font-size: 9pt; }
"""


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _style_text(style: dict[str, str]) -> str:
    names = {
        "fontFamily": "font-family", "fontSize": "font-size", "fontWeight": "font-weight",
        "fontStyle": "font-style", "textDecoration": "text-decoration",
        "textAlign": "text-align", "color": "color",
    }
    return ";".join(f"{names[key]}:{_escape(value)}" for key, value in style.items() if key in names)


def _line_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item or "") for item in value]
    text = str(value or "")
    return text.splitlines() if "\n" in text or "\r" in text else [part.strip() for part in re.split(r"[、，,；;]+", text)]


def _render_cell(cell: dict, value_map: dict[str, Any], styles: dict, custom_values: dict, key: str) -> str:
    align = cell.get("align", "left")
    classes = cell.get("className", "")
    attrs = [f'colspan="{int(cell.get("colspan", 1))}"', f'class="{_escape(classes)}"', f'style="text-align:{align}"']
    field = cell.get("field")
    lines_field = cell.get("linesField")
    style_key = ""
    if lines_field:
        style_key = f"line:{lines_field}:{int(cell.get('lineIndex', 0))}"
        lines = _line_values(value_map.get(lines_field, ""))
        index = int(cell.get("lineIndex", 0))
        value = lines[index] if index < len(lines) else ""
    elif field:
        style_key = f"field:{field}"
        value = value_map.get(field, "")
    else:
        value = ""
    style = _style_text(styles.get(style_key, {})) if style_key else ""
    value_html = f'<span class="cell-value" style="{style}">{_escape(value)}</span>'

    if cell.get("prefix"):
        content = f'<div class="prefix-field"><span class="cell-prefix">{_escape(cell["prefix"])}</span>{value_html}</div>'
    elif field or lines_field:
        content = value_html
    elif cell.get("organizationName"):
        content = f'<span class="fixed-text">{_escape(value_map.get("__organization__", ""))}</span>'
    else:
        fixed = _escape(cell.get("text", ""))
        custom = custom_values.get(key, "")
        if custom:
            custom_style = _style_text(styles.get(f"custom:{key}", {}))
            content = f'<span class="fixed-text custom-prompt">{fixed}</span><span class="cell-value custom-value" style="{custom_style}">{_escape(custom)}</span>'
        else:
            content = f'<span class="fixed-text">{fixed}</span>'
    return f"<td {' '.join(attrs)}>{content}</td>"


def _render_block(block: dict, page_index: int, block_index: int, value_map: dict, styles: dict, custom_values: dict) -> str:
    kind = block["type"]
    if kind == "table":
        cols = "".join(f'<col style="width:{float(width)}%">' for width in block["columns"])
        rows = []
        for row_index, row in enumerate(block["rows"]):
            cells = "".join(
                _render_cell(cell, value_map, styles, custom_values, f"p{page_index}-b{block_index}-r{row_index}-c{cell_index}")
                for cell_index, cell in enumerate(row["cells"])
            )
            rows.append(f'<tr style="height:{float(row["height"])}mm">{cells}</tr>')
        return f'<table class="{_escape(block.get("className", ""))}"><colgroup>{cols}</colgroup><tbody>{"".join(rows)}</tbody></table>'
    if kind == "paragraph":
        runs = []
        for run in block["runs"]:
            if run.get("field"):
                field = run["field"]
                runs.append(f'<span class="line-value" style="{_style_text(styles.get(f"field:{field}", {}))}">{_escape(value_map.get(field, ""))}</span>')
            else:
                runs.append(_escape(run.get("text", "")))
        return f'<p class="{_escape(block.get("className", ""))}">{"".join(runs)}</p>'
    if kind == "questions":
        items = "".join(f'<li><span>{_escape(question)}</span><span class="checkboxes">是□　　否□</span></li>' for question in block["questions"])
        return f'<ol class="quality-questions">{items}</ol>'
    return f'<p class="{_escape(block.get("className", ""))}">{_escape(block.get("text", ""))}</p>'


def render_form_html(template_name: str, fields: dict[str, Any] | None, organization_name: str = "") -> str:
    if template_name not in FORM_LAYOUTS:
        raise ValueError(f"unknown template: {template_name}")
    source = dict(fields or {})
    preview = build_preview(template_name, source)
    value_map = {item["key"]: item["value"] for item in preview["fields"]}
    value_map["__organization__"] = organization_name
    styles_by_template = source.get("_preview_styles") or {}
    custom_by_template = source.get("_preview_custom_values") or {}
    styles = sanitize_preview_styles(template_name, styles_by_template.get(template_name) or {})
    custom_values = sanitize_preview_custom_values(template_name, custom_by_template.get(template_name) or {})

    pages = []
    layout_pages = FORM_LAYOUTS[template_name]
    for page_index, page in enumerate(layout_pages):
        title = f'<h1 class="{_escape(page.get("titleClass", ""))}">{_escape(page.get("title", ""))}</h1>' if page.get("title") else ""
        subtitle_text = f"{organization_name or '律师事务所'}制" if page.get("subtitleFromOrganization") else page.get("subtitle", "")
        subtitle = f'<div class="page-subtitle">{_escape(subtitle_text)}</div>' if subtitle_text else ""
        blocks = "".join(_render_block(block, page_index, block_index, value_map, styles, custom_values) for block_index, block in enumerate(page["blocks"]))
        number = f'<div class="page-number">{page_index + 1}</div>' if len(layout_pages) > 1 else ""
        quality_class = " quality-card" if template_name == "质量监督卡" else ""
        pages.append(f'<section class="form-page{quality_class}">{title}{subtitle}{blocks}{number}</section>')

    return "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><style>" + CSS + "</style></head><body>" + "".join(pages) + "</body></html>"


def browser_pdf_dir(work_dir: str) -> str:
    return os.path.join(work_dir, "browser_pdf")


def render_form_pdf(template_name: str, fields: dict[str, Any] | None, organization_name: str, output_pdf: str, log=print) -> str:
    chromium = get_settings().chromium_executable
    if not chromium:
        raise RuntimeError("未找到 Chrome/Chromium；请安装浏览器或配置 V5_CHROMIUM_PATH")
    output = Path(output_pdf).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    html_path = output.with_suffix(".html")
    html_path.write_text(render_form_html(template_name, fields, organization_name), encoding="utf-8")
    profile_dir = tempfile.mkdtemp(prefix="gd_chrome_")
    temp_pdf = output.with_suffix(".tmp.pdf")
    temp_pdf.unlink(missing_ok=True)
    command = [
        chromium,
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-sync",
        "--metrics-recording-only",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-pdf-header-footer",
        "--allow-file-access-from-files",
        f"--user-data-dir={profile_dir}",
        f"--print-to-pdf={temp_pdf}",
        html_path.as_uri(),
    ]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        command.insert(1, "--no-sandbox")
    process = None
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        valid_pdf = False
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if temp_pdf.is_file() and temp_pdf.stat().st_size > 1000:
                try:
                    with fitz.open(temp_pdf) as document:
                        if document.page_count > 0 and all(
                            abs(page.rect.width - 595.28) <= 3
                            and abs(page.rect.height - 841.89) <= 3
                            for page in document
                        ):
                            valid_pdf = True
                            break
                except (RuntimeError, ValueError):
                    pass
            if process.poll() is not None:
                break
            time.sleep(0.2)
        if not valid_pdf:
            detail = ""
            if process.poll() is not None and process.stderr:
                detail = process.stderr.read().strip()[-1000:]
            raise RuntimeError(f"浏览器生成 PDF 失败: {detail or '等待有效 A4 PDF 超时'}")
        os.replace(temp_pdf, output)
        log(f"       浏览器 PDF: {template_name}")
        return str(output)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        try:
            temp_pdf.unlink(missing_ok=True)
        except OSError:
            pass
        shutil.rmtree(profile_dir, ignore_errors=True)


def render_system_form_pdfs(fields: dict[str, Any] | None, organization_name: str, work_dir: str, log=print) -> dict[str, str]:
    output_dir = browser_pdf_dir(work_dir)
    os.makedirs(output_dir, exist_ok=True)
    rendered: dict[str, str] = {}
    for template_name in SYSTEM_TEMPLATE_NAMES:
        rendered[template_name] = render_form_pdf(
            template_name,
            fields,
            organization_name,
            os.path.join(output_dir, f"{template_name}.pdf"),
            log=log,
        )
    return rendered
