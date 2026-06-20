#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文书匹配调试工具 — 让匹配过程透明化"""

import json
import sys
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class MatchDebugInfo:
    """文书匹配调试信息"""
    step: str
    timestamp: str
    doc_id: int = None
    doc_type: str = None
    catalog_seq: int = None
    page_range: str = None
    confidence: float = None
    match_method: str = None
    anchor_found: str = None
    fallback_reason: str = None
    raw_ocr_preview: str = None

class DebugMatcher:
    """调试匹配器"""

    def __init__(self, output_file: str = None):
        self.debug_log: List[MatchDebugInfo] = []
        self.output_file = output_file or f"outputs/debug_match_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    def log_page_classification(self, page_idx: int, text: str, result: dict):
        """记录页面分类过程"""
        preview = text[:100] if text else ""
        self.debug_log.append(MatchDebugInfo(
            step="page_classification",
            timestamp=datetime.now().isoformat(),
            doc_id=page_idx,
            match_method=result.get("method"),
            confidence=result.get("confidence"),
            catalog_seq=result.get("catalog_seq"),
            anchor_found=result.get("anchor"),
            raw_ocr_preview=preview
        ))

    def log_document_segment(self, doc_id: int, doc_type: str, start_page: int,
                             end_page: int, confidence: float, catalog_seq: int):
        """记录文书段切分结果"""
        self.debug_log.append(MatchDebugInfo(
            step="document_segment",
            timestamp=datetime.now().isoformat(),
            doc_id=doc_id,
            doc_type=doc_type,
            catalog_seq=catalog_seq,
            page_range=f"{start_page}-{end_page}",
            confidence=confidence
        ))

    def log_missing_analysis(self, catalog_seq: int, item_name: str,
                           searched_types: List[str], reasons: List[str]):
        """记录缺失项分析"""
        self.debug_log.append(MatchDebugInfo(
            step="missing_analysis",
            timestamp=datetime.now().isoformat(),
            catalog_seq=catalog_seq,
            match_method="searched",
            raw_ocr_preview=f"searched_types: {searched_types}, reasons: {reasons}"
        ))

    def save_debug_log(self):
        """保存调试日志"""
        try:
            import os
            os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(log) for log in self.debug_log], f,
                         ensure_ascii=False, indent=2)
            print(f"调试日志已保存: {self.output_file}")
        except Exception as e:
            print(f"保存调试日志失败: {e}")

    def print_summary(self):
        """打印调试摘要"""
        print("\n=== 文书匹配调试摘要 ===")

        steps = {}
        for log in self.debug_log:
            steps[log.step] = steps.get(log.step, 0) + 1

        print(f"总操作数: {len(self.debug_log)}")
        print("操作分类:")
        for step, count in steps.items():
            print(f"  {step}: {count}次")

        if self.output_file:
            print(f"详细日志: {self.output_file}")

# 全局调试器实例
_debug_matcher = None

def get_debug_matcher() -> DebugMatcher:
    """获取全局调试匹配器"""
    global _debug_matcher
    if _debug_matcher is None:
        _debug_matcher = DebugMatcher()
    return _debug_matcher

def enable_debug_mode():
    """启用调试模式"""
    from settings import load_config
    config = load_config()
    debug_enabled = config.get("debug", {}).get("match_details", False)
    return debug_enabled

def log_classification(page_idx: int, text: str, result: dict):
    """便捷函数：记录分类过程"""
    if enable_debug_mode():
        get_debug_matcher().log_page_classification(page_idx, text, result)

def log_segmentation(doc_id: int, doc_type: str, start_page: int, end_page: int,
                     confidence: float, catalog_seq: int):
    """便捷函数：记录切分结果"""
    if enable_debug_mode():
        get_debug_matcher().log_document_segment(
            doc_id, doc_type, start_page, end_page, confidence, catalog_seq
        )