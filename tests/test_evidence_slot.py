# -*- coding: utf-8 -*-
"""证据材料槽业务规则测试（无 OCR 依赖）。

规则：
- 「证据材料清单」即证据材料段的起始页 → 切到 evidence 槽。
- 无法辨别具体类型的文书一律归入「证据材料」槽。
"""

import archive_catalog as ac
import document_segmenter as ds
from pdf_doc_locator import segment_by_catalog, _evidence_seq


def _evidence_seq_for(case="civil"):
    return _evidence_seq(ac.get_catalog(case))


def test_evidence_list_starts_evidence_section():
    ev = _evidence_seq_for()
    pages = [
        "委托代理合同\n甲方：张三  乙方：某律师事务所\n服务内容……",
        "证据材料清单\n序号 名称 页数\n1 银行流水 3\n2 借条 1",
        "银行流水明细\n2019-01-01 转账 100000 元……",
        "借条\n今借到张三人民币壹拾万元整……",
    ]
    units = segment_by_catalog(pages, "civil", log=lambda *a, **k: None)
    # 「证据材料清单」所在页应为 evidence 段起始
    ev_units = [u for u in units if u.catalog_seq == ev]
    assert ev_units, "应存在 evidence 槽单元"
    start = min(u.start_page for u in ev_units)
    assert start == 1, f"证据材料段起始页应为「证据材料清单」页(1)，实际 {start}"
    # 清单之后无法辨别的页（银行流水/借条）应折叠进 evidence 槽
    covered = set()
    for u in ev_units:
        covered.update(range(u.start_page, u.end_page + 1))
    assert {1, 2, 3}.issubset(covered), f"证据页应归入 evidence 槽，实际覆盖 {covered}"


def test_unidentifiable_unit_falls_into_evidence():
    ev = _evidence_seq_for()
    pages = [
        "某说明材料\n关于本案的一些情况说明……",   # 无明确文书类型
        "（续）补充说明若干……",
    ]
    units = segment_by_catalog(pages, "civil", log=lambda *a, **k: None)
    assert units, "应至少切出一个单元"
    for u in units:
        assert u.catalog_seq == ev, (
            f"无法辨别类型应归入 evidence 槽 seq{ev}，实际 seq{u.catalog_seq}"
        )
        assert u.doc_type == ds.DOC_TYPE_EVIDENCE
