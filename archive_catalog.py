#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""案卷目录数据 — 五类标准案卷目录"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CatalogItem:
    """目录项"""
    seq: int
    name: str
    source: str  # system | pdf | manual | mixed
    templates: Tuple[str, ...] = field(default_factory=tuple)
    doc_types: Tuple[str, ...] = field(default_factory=tuple)
    manual_key: str = ""


# 五类案件类型标签
CASE_TYPE_LABELS = {
    "civil": "民事",
    "criminal": "刑事",
    "admin": "行政",
    "nonlit": "非诉",
    "counsel": "顾问",
}


# 民事目录（seq0 封面 + seq1~18 正文，共 19 项）— 对齐人工成果金标准
_CIVIL_CATALOG = [
    CatalogItem(0, "档案卷宗（封面）", "system", templates=("档案卷宗",)),
    CatalogItem(1, "立案审批表", "system", templates=("立案审批表",)),
    CatalogItem(2, "发票回执等收费凭证", "manual", manual_key="invoice"),
    CatalogItem(3, "委托代理合同", "pdf", doc_types=("contract",)),
    CatalogItem(4, "授权委托书", "pdf", doc_types=("poa",)),
    CatalogItem(5, "起诉状、上诉状或答辩状", "pdf", doc_types=("complaint", "appeal")),
    CatalogItem(6, "阅卷笔录、会见当事人谈话笔录", "manual", manual_key="review_record"),
    CatalogItem(7, "证据材料", "manual", manual_key="evidence"),
    CatalogItem(8, "诉讼保全/证据保全/先行给付申请书 + 案件相关法院裁判书", "mixed", doc_types=(), manual_key="preservation"),
    CatalogItem(9, "承办律师代理意见", "manual", manual_key="agent_opinion"),
    CatalogItem(10, "集体讨论记录", "manual", manual_key="group_discussion"),
    CatalogItem(11, "代理词或辩护词", "manual", manual_key="plea"),
    CatalogItem(12, "出庭通知书", "pdf", doc_types=("summons",)),
    CatalogItem(13, "庭审笔录", "pdf", doc_types=("court_record",)),
    # 金标准（人工成果）将「审判文书」与「执行文书」分列为 seq14 / seq15。
    CatalogItem(14, "裁定书、判决书、调解书", "pdf", doc_types=("judgment", "ruling", "mediation")),
    CatalogItem(15, "执行申请书、执行相关法院文书", "pdf", doc_types=("execution",)),
    CatalogItem(16, "委托人须知、质量监督卡", "system", templates=("质量监督卡",)),
    CatalogItem(17, "律师所送达材料清单", "system", templates=("送达材料清单",)),
    CatalogItem(18, "结案报告", "system", templates=("结案报告表",)),
]


# 刑事目录（19项，含 seq0）
_CRIMINAL_CATALOG = [
    CatalogItem(0, "档案卷宗（封面）", "system", templates=("档案卷宗",)),
    CatalogItem(1, "立案审批表", "system", templates=("立案审批表",)),
    CatalogItem(2, "发票回执等收费凭证", "manual", manual_key="invoice"),
    CatalogItem(3, "委托辩护或代理合同、委托书或指定书", "pdf", doc_types=("contract",)),
    CatalogItem(4, "授权委托书", "pdf", doc_types=("poa",)),
    CatalogItem(5, "起诉书、抗诉书", "pdf", doc_types=("indictment",)),
    CatalogItem(6, "阅卷笔录", "manual", manual_key="review_record"),
    CatalogItem(7, "会见犯罪嫌疑人、被告人、证人等笔录", "manual", manual_key="meeting_record"),
    CatalogItem(8, "调查材料", "manual", manual_key="investigation"),
    CatalogItem(9, "证据材料", "manual", manual_key="evidence"),
    CatalogItem(10, "承办律师的辩护意见或代理意见", "manual", manual_key="agent_opinion"),
    CatalogItem(11, "集体讨论记录", "manual", manual_key="group_discussion"),
    CatalogItem(12, "辩护词或代理词", "manual", manual_key="plea"),
    CatalogItem(13, "出庭通知书", "pdf", doc_types=("summons",)),
    CatalogItem(14, "裁定书、判决书", "pdf", doc_types=("judgment", "ruling", "execution")),
    CatalogItem(15, "上诉书、抗诉书", "pdf", doc_types=("appeal",)),
    CatalogItem(16, "委托人须知、质量监督卡", "system", templates=("质量监督卡",)),
    CatalogItem(17, "律师所送达材料清单", "system", templates=("送达材料清单",)),
    CatalogItem(18, "结案报告", "system", templates=("结案报告表",)),
]


# 行政目录（18项，含 seq0）— 与民事相同
_ADMIN_CATALOG = _CIVIL_CATALOG


# 非诉目录（11项，含 seq0）
_NONLIT_CATALOG = [
    CatalogItem(0, "档案卷宗（封面）", "system", templates=("档案卷宗",)),
    CatalogItem(1, "立案审批表", "system", templates=("立案审批表",)),
    CatalogItem(2, "非诉讼法律事务委托合同", "pdf", doc_types=("contract",)),
    CatalogItem(3, "发票回执等收费凭证", "manual", manual_key="invoice"),
    CatalogItem(4, "与委托人谈话记录", "manual", manual_key="client_talk"),
    CatalogItem(5, "委托人提供的证据材料", "manual", manual_key="evidence"),
    CatalogItem(6, "调查材料", "manual", manual_key="investigation"),
    CatalogItem(7, "律师出具的法律意见、草拟的法律文书、办理具体法律事务活动的记录", "manual", manual_key="legal_work"),
    CatalogItem(8, "委托人须知、质量监督卡", "system", templates=("质量监督卡",)),
    CatalogItem(9, "律师所送达材料清单", "system", templates=("送达材料清单",)),
    CatalogItem(10, "结案报告", "system", templates=("结案报告表",)),
]


# 顾问目录（10项，含 seq0）
_COUNSEL_CATALOG = [
    CatalogItem(0, "档案卷宗（封面）", "system", templates=("档案卷宗",)),
    CatalogItem(1, "立案审批表", "system", templates=("立案审批表",)),
    CatalogItem(2, "委托代理合同", "pdf", doc_types=("contract",)),
    CatalogItem(3, "聘方基本情况介绍材料", "manual", manual_key="client_intro"),
    CatalogItem(4, "发票回执等收费凭证", "manual", manual_key="invoice"),
    CatalogItem(5, "办理各类法律事务的记录和有关材料", "manual", manual_key="work_record"),
    CatalogItem(6, "协议存续、中止、终止的情况", "manual", manual_key="agreement_status"),
    CatalogItem(7, "委托人须知、质量监督卡", "system", templates=("质量监督卡",)),
    CatalogItem(8, "律师所送达材料清单", "system", templates=("送达材料清单",)),
    CatalogItem(9, "结案报告", "system", templates=("结案报告表",)),
]


# 目录数据映射
_CATALOGS: Dict[str, List[CatalogItem]] = {
    "civil": _CIVIL_CATALOG,
    "criminal": _CRIMINAL_CATALOG,
    "admin": _ADMIN_CATALOG,
    "nonlit": _NONLIT_CATALOG,
    "counsel": _COUNSEL_CATALOG,
}


# manual_key → 可 OCR 识别的 doc_type 映射（D4 手动材料识别）
# V5 增强版：新增OCR锚点支持更多manual类型自动识别
MANUAL_KEY_DOC_TYPES = {
    "invoice": "invoice",
    "evidence": "evidence",
    "plea": "plea",
    "agent_opinion": "agent_opinion",
    # V5 新增：以下 manual_key 现在有标准锚点，可以自动识别
    "review_record": "review_record",
    "group_discussion": "group_discussion",
    "preservation": "preservation",
    "investigation": "investigation",
    "client_talk": "client_talk",
    # 以下 manual_key 仍无标准锚点，返回 None 表示只能用户补充
    "legal_work": None,
    "client_intro": None,
    "work_record": None,
    "agreement_status": None,
    "meeting_record": None,
}


BACK_SYSTEM_INSERT_ORDER: Dict[str, Tuple[int, ...]] = {
    # V6/G2：金标准卷末为质量监督卡(16)→结案报告(18)，无 seq17 送达页
    "civil": (16, 18),
    "admin": (16, 18),
    "criminal": (16, 18),
    "nonlit": (8, 9, 10),
    "counsel": (7, 8, 9),
}

# 五类卷内目录 Word 模板（templates/bundled 下，仅填页码格）
CATALOG_TEMPLATE_FILES: Dict[str, str] = {
    "civil": "卷内目录_民事.doc",
    "criminal": "卷内目录_刑事.doc",
    "admin": "卷内目录_行政.doc",
    "nonlit": "卷内目录_非诉.doc",
    "counsel": "卷内目录_顾问.doc",
}


def get_catalog_template_filename(case_type: str) -> str:
    fn = CATALOG_TEMPLATE_FILES.get(case_type)
    if not fn:
        raise ValueError(f"Unknown case_type: {case_type}")
    return fn


def get_back_system_seqs(case_type: str) -> Tuple[int, ...]:
    """卷末系统模板按业务顺序返回 seq 列表"""
    order = BACK_SYSTEM_INSERT_ORDER.get(case_type)
    if order is None:
        raise ValueError(f"Unknown case_type: {case_type}")
    return order


# V6：无执行材料时可从目录/卷内目录省略的 seq
OPTIONAL_CATALOG_SEQS: Dict[str, Tuple[int, ...]] = {
    "civil": (15,),
    "admin": (15,),
    "criminal": (15,),
}

# 金标准：送达清单(seq17)不作为卷内目录正文行展示
TOC_EXCLUDE_SEQS: Dict[str, Tuple[int, ...]] = {
    "civil": (17,),
    "admin": (17,),
    "criminal": (17,),
}


def get_effective_catalog(
    case_type: str,
    found_seqs: Optional[set] = None,
    *,
    for_toc: bool = False,
) -> List[CatalogItem]:
    """按 found_seqs 裁剪可选目录项；卷内目录可排除 seq17。"""
    catalog = get_catalog(case_type)
    optional = set(OPTIONAL_CATALOG_SEQS.get(case_type, ()))
    exclude = set(TOC_EXCLUDE_SEQS.get(case_type, ())) if for_toc else set()
    if found_seqs is not None:
        found = set(found_seqs)
        catalog = [
            item for item in catalog
            if item.seq not in optional or item.seq in found
        ]
    if exclude:
        catalog = [item for item in catalog if item.seq not in exclude]
    return catalog


def get_catalog(case_type: str) -> List[CatalogItem]:
    """获取指定案件类型的目录

    Args:
        case_type: 案件类型代码 (civil/criminal/admin/nonlit/counsel)

    Returns:
        目录项列表，按 seq 升序排列
    """
    catalog = _CATALOGS.get(case_type)
    if catalog is None:
        raise ValueError(f"Unknown case_type: {case_type}. Valid: {list(_CATALOGS.keys())}")
    return list(catalog)  # 返回副本


def catalog_item_for_doc_type(case_type: str, doc_type: str) -> Optional[CatalogItem]:
    """查找指定 doc_type 对应的目录项

    优先返回 source='pdf' 的项，若存在多个则返回 seq 最小的。
    若仅 source='mixed' 中存在，则返回 mixed 项。

    Args:
        case_type: 案件类型代码
        doc_type: 文书类型代码

    Returns:
        匹配的 CatalogItem，若未找到则返回 None
    """
    pdf_match = None
    mixed_match = None

    for item in get_catalog(case_type):
        if doc_type in item.doc_types:
            if item.source == "pdf":
                if pdf_match is None or item.seq < pdf_match.seq:
                    pdf_match = item
            elif item.source == "mixed" and mixed_match is None:
                mixed_match = item

    return pdf_match or mixed_match


def catalog_item_for_template(case_type: str, template_name: str) -> Optional[CatalogItem]:
    """查找指定模板名称对应的目录项

    Args:
        case_type: 案件类型代码
        template_name: 模板名称

    Returns:
        匹配的 CatalogItem，若未找到则返回 None
    """
    for item in get_catalog(case_type):
        if template_name in item.templates:
            return item
    return None


def catalog_item_for_manual_key(case_type: str, manual_key: str) -> Optional[CatalogItem]:
    """查找指定 manual_key 对应的目录项

    Args:
        case_type: 案件类型代码
        manual_key: 手动材料键名

    Returns:
        匹配的 CatalogItem，若未找到则返回 None
    """
    for item in get_catalog(case_type):
        if item.manual_key == manual_key:
            return item
    return None
