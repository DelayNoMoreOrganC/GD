#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容层：委托 V1.3 原子替换（禁止整格回退）"""

from word_atomic_fill import (
    content_range,
    replace_placeholders_atomic,
    replace_plain_atomic,
)


def replace_placeholders_in_range(rng, patch: dict, blacken_fn=None) -> int:
    """在 rng 内原子替换【key】；需能取得 Document"""
    if not patch or rng is None:
        return 0
    try:
        doc = rng.Document
    except Exception:
        return 0
    return replace_placeholders_atomic(
        doc, rng, patch, blacken_fn=blacken_fn
    )


def replace_plain_in_range(rng, token: str, value: str, blacken_fn=None) -> int:
    try:
        doc = rng.Document
    except Exception:
        return 0
    return replace_plain_atomic(doc, rng, token, value, blacken_fn=blacken_fn)
