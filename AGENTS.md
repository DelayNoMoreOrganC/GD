# AGENTS.md — 案件归档 V4

## 权威规格
- Loop 触发：`f:\GD\docs\LOOP_PROMPT.md`（**每轮只读此文件，勿粘贴 PRD 全文**）
- 业务工作流：`f:\GD\docs\WORKFLOW.md`（WF1~WF5）
- 完整 PRD：`f:\GD\docs\PRD_V4.md`（按需查阅）

## 当前阶段
- **Phase E**：WF1 统一 OCR（T-501~504）✅
- **Phase F**：WF2+3 文书切分与映射（T-601~605）✅
- **Phase G**：WF4 隔离（T-701~702）✅
- **Phase H**：WF5 + 人工闸门（T-801~805）✅
- **Phase I**：路径 B + 性能（T-901~902）✅
- **Phase J**：排序与识别准确度（T-1001~1005）✅
- **Phase K**：归档顺序配置化 catalog/original（T-1101~1104）✅
- **Phase L**：GUI 体验（进度条/手动调序/版本/多文件补充，T-1201~1204）✅
- **Phase M**：CLI 完善 `--supplement`/`--order-mode`（T-1301~1302）✅
- **Phase N**：pytest 框架 + CI + 文档收尾（T-1401~1403）✅
- DocumentUnit 文书级切分/合并已落地
- V1 打包入口已去除；`dist/` 既有 V1–V3 EXE 保留

## 个案归档两条路径

| 路径 | 输入 | 分析入口 |
|------|------|----------|
| **A 单卷综合** | 1 个 PDF（default 类型） | `segment_by_catalog` 卷内切分 |
| **B 多份分类** | 多个 PDF + 文件名/类型 | `build_units_from_sources`，每文件 1 Unit |

共用：`analyze_archive` → 缺失确认 → `assemble_archive` → 完整归档 PDF

## 运行
- GUI: `py legal_archive_gui.py`（个案区 multi_files 支持路径 A/B）
- CLI 路径 A: `py run_archive.py --catalog civil [--skip-missing] <pdf>`
- CLI 路径 B: `py run_archive.py --catalog civil --sources 卷宗.pdf:default 合同.pdf:contract`
- 依赖检查: `py scripts/verify_deps.py`
- 测试 PDF: `test_sample\2014-兴泰贸易.pdf`

## V4 核心模块
- WF1 OCR: `ocr_pipeline.ingest_pdf` / `archive_pipeline.ingest_archive_sources`
- 切分: `pdf_doc_locator.segment_by_catalog` / `build_units_from_sources`（`segment_documents` 已弃用，仅留锚点 fallback）
- 映射: `pdf_doc_locator.assign_catalog_seq`（按 `(source_path, start_page)` 排序）
- 合并: `pdf_archive_merger.build_full_archive`（`unit.source_path` 多源插入；`order_mode=catalog|original`）

## 归档正文排序模式
- `config.json` → `archive.order_mode`：`catalog`（默认，按标准目录序）/ `original`（保持源 PDF 页序）
- getter：`settings.get_archive_order_mode`；CLI `--order-mode`；GUI「正文排序」单选
- 两模式均满足源 PDF 页守恒（D5）

## 验收口径
- Phase E: 兴泰贸易 WF1 `ocr_engine_calls` ≤ 1，无全卷 `get_page_texts`（AC-E01）
- 路径 A: 兴泰贸易 → **80/80 页守恒**（AC-D01）
- 路径 B: 多文件 → 文件名识别 + 整文件归位（AC-D03/D04）
- 补充上传: supplements 按 seq 直达，不 re-classify（AC-D05）

## 一键回归命令
```bash
# Phase E: WF1 OCR 验证
py scripts/perf_wf_baseline.py

# Phase F: WF2+3 切分质量验证
py scripts/verify_wf2_units.py

# Phase G: WF4 隔离验证
py scripts/verify_wf4_isolation.py

# Phase H: 两阶段流程验证
py scripts/verify_two_phase.py        # T-801
py scripts/verify_page_conservation.py  # T-802
py scripts/verify_missing_dialog.py    # T-803
py scripts/verify_supplements.py        # T-804
py scripts/perf_wf5_baseline.py        # T-805

# Phase I: 路径 B 验证
py scripts/verify_path_b.py           # T-901/902（加 --no-cli 跳过 CLI 重复跑）

# Phase J: 排序与识别准确度
py scripts/verify_doc_order.py        # T-1005 乱序检测 + 兴泰贸易同槽页序

# Phase K: 归档顺序配置化
py scripts/verify_order_mode.py       # T-1104 catalog vs original（免 OCR）

# Phase M: CLI 补充上传
py scripts/verify_cli_supplement.py   # T-1302 --supplement 解析 + 多文件补充（免 OCR）

# Phase N: 纯逻辑单测（免 OCR/Word，CI 同款）
py -m pytest tests/ -q
```

## Loop 协议
1. 每次只做 **一个** Phase D 任务
2. 跑 verify，勾选 `[x]`
3. 不自动 git commit

## 核心约束
- D5: 跳过不插页；**源 PDF 页守恒**（失败则 success=False）
- D6: 完整归档仅个案；批量保持 V3
- D14~D16: DocumentUnit 整份文书；unknown→evidence；同槽多文书按 doc_id
