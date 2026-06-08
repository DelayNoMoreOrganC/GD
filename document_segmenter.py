#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 文本按文书类型分段"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DOC_TYPE_JUDGMENT = "judgment"
DOC_TYPE_EXECUTION = "execution"
DOC_TYPE_CONTRACT = "contract"
DOC_TYPE_COMPLAINT = "complaint"
DOC_TYPE_OTHER = "other"
DOC_TYPE_DEFAULT = "default"

DOC_TYPE_LABELS = {
    DOC_TYPE_DEFAULT: "默认（综合文档）",
    DOC_TYPE_JUDGMENT: "民事判决书",
    DOC_TYPE_EXECUTION: "执行裁定书",
    DOC_TYPE_CONTRACT: "委托代理合同",
    DOC_TYPE_COMPLAINT: "起诉状",
    DOC_TYPE_OTHER: "其他",
}

ANCHORS = {
    DOC_TYPE_JUDGMENT: (
        "民事判决书",
        "判决书",
        "民事裁定书",
    ),
    DOC_TYPE_EXECUTION: (
        "执行裁定书",
        "终结本次执行程序",
        "恢复执行",
    ),
    DOC_TYPE_CONTRACT: (
        "委托代理合同",
        "法律服务合同",
        "代理合同",
    ),
    DOC_TYPE_COMPLAINT: (
        "民事起诉状",
        "起诉状",
    ),
}

FILENAME_HINTS = {
    DOC_TYPE_JUDGMENT: ("判决", "judgment"),
    DOC_TYPE_EXECUTION: ("执行", "裁定", "终本", "execution"),
    DOC_TYPE_CONTRACT: ("合同", "委托", "contract"),
    DOC_TYPE_COMPLAINT: ("起诉", "complaint"),
}


@dataclass
class DocumentSource:
    path: str
    doc_type: str = DOC_TYPE_DEFAULT
    pages: Optional[int] = None


@dataclass
class SegmentedText:
    segments: Dict[str, str] = field(default_factory=dict)
    full_text: str = ""

    def get(self, doc_type: str) -> str:
        return self.segments.get(doc_type, "")

    def combined_for_normalize(self) -> str:
        if self.full_text:
            return self.full_text
        parts = []
        for key in (
            DOC_TYPE_DEFAULT,
            DOC_TYPE_JUDGMENT,
            DOC_TYPE_EXECUTION,
            DOC_TYPE_CONTRACT,
            DOC_TYPE_COMPLAINT,
            DOC_TYPE_OTHER,
        ):
            text = self.segments.get(key, "")
            if text:
                parts.append(text)
        return "\n\n".join(parts)


def guess_doc_type_from_filename(path: str) -> str:
    name = (path or "").lower()
    for doc_type, hints in FILENAME_HINTS.items():
        if any(h in name for h in hints):
            return doc_type
    return DOC_TYPE_OTHER


def _find_anchor_positions(text: str) -> List[tuple]:
    positions = []
    for doc_type, anchors in ANCHORS.items():
        for anchor in anchors:
            for m in re.finditer(re.escape(anchor), text):
                positions.append((m.start(), doc_type, anchor))
    positions.sort(key=lambda x: x[0])
    return positions


def segment_single_pdf_text(pdf_text: str, buffer: int = 500) -> SegmentedText:
    """单卷 PDF：按标题锚点切分文书段落"""
    if not pdf_text or len(pdf_text.strip()) < 50:
        return SegmentedText(full_text=pdf_text or "")

    positions = _find_anchor_positions(pdf_text)
    if not positions:
        return SegmentedText(full_text=pdf_text)

    segments: Dict[str, List[str]] = {}
    for i, (start, doc_type, _anchor) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(pdf_text)
        chunk_start = max(0, start - buffer)
        chunk = pdf_text[chunk_start:end].strip()
        if chunk:
            segments.setdefault(doc_type, []).append(chunk)

    merged = {}
    for doc_type, chunks in segments.items():
        merged[doc_type] = "\n\n".join(chunks)

    return SegmentedText(segments=merged, full_text=pdf_text)


def segment_from_sources(source_texts: Dict[str, str]) -> SegmentedText:
    """多文件模式：按 doc_type 直接映射；default 视为综合全文"""
    segments = {k: v for k, v in (source_texts or {}).items() if v and v.strip()}
    default_text = segments.pop(DOC_TYPE_DEFAULT, "")
    if default_text:
        segments.setdefault(DOC_TYPE_OTHER, "")
        segments[DOC_TYPE_OTHER] = (
            (segments[DOC_TYPE_OTHER] + "\n\n" + default_text).strip()
            if segments[DOC_TYPE_OTHER]
            else default_text
        )
    full = "\n\n".join(segments.values())
    return SegmentedText(segments=segments, full_text=full)


def build_segmented_text(
    pdf_text: str = "",
    sources: Optional[List[DocumentSource]] = None,
    source_texts: Optional[Dict[str, str]] = None,
) -> SegmentedText:
    """统一入口：多文件 source_texts 优先，否则单 PDF 切分。"""
    if source_texts:
        return segment_from_sources(source_texts)
    return segment_single_pdf_text(pdf_text)


def validate_sources_for_archive(sources: List[DocumentSource]) -> Optional[str]:
    """校验多文件输入；返回错误信息或 None"""
    if not sources:
        return "未选择任何 PDF 文件"
    types = {s.doc_type for s in sources}
    only_default = types <= {DOC_TYPE_DEFAULT}
    if not only_default and DOC_TYPE_JUDGMENT not in types and DOC_TYPE_EXECUTION not in types:
        return "至少需要一份「判决书」或「执行裁定书」（或使用「默认（综合文档）」）"
    for s in sources:
        if not s.path:
            return "存在空文件路径"
    return None
