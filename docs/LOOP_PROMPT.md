# V4 Phase E~I Loop（WF1~WF5）

> **推荐：每完成 1 个任务 → 清上下文 → 新会话发「恢复语」**。进度靠本文件 `[x]` + 代码，不靠对话记忆。

## 当前进度
- Phase A+B+C+D：完成
- **Phase E（WF1 统一 OCR）**：T-501~504 ✅
- **Phase F（WF2+3 切分与映射）**：T-601~605 ✅
- **Phase G（WF4 隔离）**：T-701~702 ✅
- **Phase H（WF5+人工闸门）**：T-801~805 ✅
- **Phase I（路径 B + 性能）**：T-901~902 ✅
- **Phase J（排序与识别准确度）**：T-1001~1005 ✅
- **Phase K（归档顺序配置化 catalog/original）**：T-1101~1104 ✅
- **Phase L（GUI 体验）**：T-1201~1204 ✅
- **Phase M（CLI 完善）**：T-1301~1302 ✅
- **Phase N（pytest + CI + 文档收尾）**：T-1401~1403 ✅
- **Phase E~N `<loop-done>`** ✅
- 性能基线：`py scripts/perf_wf5_baseline.py` → `outputs/wf5_baseline.json`
- 排序/顺序/CLI 回归：`verify_doc_order.py` / `verify_order_mode.py` / `verify_cli_supplement.py`
- 纯逻辑单测：`py -m pytest tests/ -q`

## 工作目录
`f:\GD` · 禁止 git commit

## Phase E 任务表

| 任务 | 要点 | verify |
|------|------|--------|
| T-501 | `ocr_engine_calls` 仅计重型 OCR | `OcrDocumentResult.rapidocr_fallback_pages` 独立 |
| T-502 | `build_units_from_sources` 禁止 `get_page_texts` | 源码无 `po.get_page_texts` |
| T-503 | `locate_doc_spans` 改 `ingest_pdf` | 源码审查 `_wf1_ingest` |
| T-504 | perf 基线 + 文档同步 | `py scripts/perf_wf_baseline.py` → `ocr_engine_calls` ≤ 1 |

## Phase F 任务表（WF2+3 切分与映射）

| 任务 | 要点 | verify |
|------|------|--------|
| T-601 [x] | 切分质量基线脚本 | `py scripts/verify_wf2_units.py` → 80/80 页覆盖 ✅ |
| T-602 [x] | 文书类型识别精度优化 | `_validate_document_type` 二次校验 ✅ |
| T-603 [x] | 目录映射准确率优化 | catalog_seq 匹配率 100% ✅ |
| T-604 [x] | 文书边界切分准确性 | 碎片化减少，execution 71-79 从 5→3 份 ✅ |
| T-605 [x] | WF2+3 性能基线 | `py scripts/perf_wf_baseline.py` → units_count=10 ✅ |

## Phase D 任务表（已完成）

| 任务 | 要点 |
|------|------|
| T-401~408 | 个案双路径接线 |

## Phase G 任务表（WF4 隔离）

| 任务 | 要点 | verify |
|------|------|--------|
| T-701 [x] | WF4与WF2/3隔离 | analyze_archive在WF4失败时仍返回doc_spans+missing_items ✅ |
| T-702 [x] | WF4异常保护 | Mock验证：WF4全部失败时doc_spans≥10，不抛异常 ✅ |

## 硬约束
D4/D5/D6/D7/D8/D13/D14/D15/D16（见 AGENTS.md）

---

## 恢复语（清上下文后只发这一句）

```
/pua:pua-loop "新会话。读 f:\GD\docs\LOOP_PROMPT.md。
Phase E~N 全部完成 ✅；0619 迭代 Iteration 0~11 完成（avg 95.6、GT 8/18、pytest 39）。
当前可选：P1 扩 GT / P2 字段质量 / 2019 残余 / 工程卫生。
只输出4行：TASK/VERIFY/NEXT/BLOCK。禁止 commit。"
```

## 每轮结束 Claude 只输出 4 行

```
TASK: T-xxx [x]
VERIFY: pass
NEXT: T-yyy
BLOCK: 无
```

## 完成条件
- Phase E: T-501~504 全 [x] → ✅ 已完成
- Phase F: T-601~605 全 [x] → ✅ 已完成
- Phase G: T-701~702 全 [x] → ✅ 已完成
- Phase H: T-801~805 全 [x] → ✅ 已完成
- Phase I: T-901~902 全 [x] → ✅ 已完成

## 恢复语（清上下文后只发这一句）

```
/pua:pua-loop "新会话。读 f:\GD\docs\LOOP_PROMPT.md。
Phase E~I 全部完成 ✅。可选择进入新 Phase 或总结成果。
只输出4行：TASK/VERIFY/NEXT/BLOCK。禁止 commit。"
```

## Phase H 任务表（WF5 + 人工闸门）

| 任务 | 要点 | verify |
|------|------|--------|
| T-801 [x] | GUI两阶段确认 | analyze + assemble 分离，可独立调用，可脚本验收 ✅ |
| T-802 [x] | 80/80页守恒 | original_pages_included=80/80，源PDF每页恰好纳入一次 ✅ |
| T-803 [x] | 缺失项对话框 | 静态验证函数逻辑完整，人工验收清单已提供 ✅ |
| T-804 [x] | 补充上传功能 | supplements 按 seq 直达，跳过 classify_attachments ✅ |
| T-805 [x] | WF5性能基线 | wf5_seconds=5.89s，端到端87.44s ✅ |

## Phase I 任务表（路径 B + 性能）

| 任务 | 要点 | verify |
|------|------|--------|
| T-901 [x] | 路径B多文件E2E | 多文件 --sources，页守恒179/179 ✅ |
| T-902 [x] | Phase I收尾 | verify_path_b programmatic 179/179；民事目录去重18项 ✅ |
