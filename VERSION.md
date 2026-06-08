# 版本记录

## V3（2026-06-05）

| 能力 | 说明 |
|------|------|
| 输出 | 仅 **全选** / **自选** 5 份 docx，移除合并 PDF 选项 |
| 批量上传 | 列表展示全部 PDF，每项可 **移除**；多次选择可追加 |
| UI | 圆角卡片、彩色主题、窗口随内容自适应 |
| 打包 | `案件档案归档V3.exe`（`app_version.V3_VERSION`） |

---

## V1（基线，2026-06-04）

**状态：** 表格版式稳定、归档流水线可用，已冻结为基线。

| 能力 | 说明 |
|------|------|
| 路线 A | PDF → OCR → DeepSeek 抽字段 → 5 份 Word → ZIP + 合并 PDF |
| 模板 | `templates/bundled/*.doc`，Word COM 按单元格替换【占位符】 |
| 分发 | `dist/案件档案归档/案件档案归档.exe` |
| UI | macOS 风格初版（tkinter） |

**已知限制（V1）：** 结案小结/审办结果未强制综合判决书+终本裁定；输出可能含红色说明字；UI 较简。

---

## V1.1（当前，2026-06-04）

1. **结案小结 / 审（办）结果**：提示词 + `case_outcome.py` 统一综合「民事判决书 + 执行终本裁定书」，≤200 字（参考律所范例表述）  
2. **输出黑色**：填充后 Word COM 仅将 Run 字体设为黑色，不改动表格结构  
3. **UI**：Apple 风格 + Emoji（📁📄🔍✨📂⚙️ 等），标题显示 V1.1  

**运行：** `py legal_archive_gui.py` 或 `dist/案件档案归档/案件档案归档.exe`

---

## V1.1.1（2026-06-04）

1. **法院收案号**：剥离「参考格式」等提示文字，用正则从 PDF 文本提取真实案号  
2. **黑色字体**：填充后立即 `_blacken_range`，并全文再刷黑（Characters + Runs）  
3. **送达材料清单**：法院文书按表格行逐份填入，不再每行重复整串清单  

---

## V1.1.2（2026-06-04）

1. **送达材料清单专用填充**（`delivery_list_filler.py`）：案号/委托方/承办律师仅在表格外段落填写；表头行恢复「序号|材料名称|…」  
2. **修复表头列错位**：`enumerate(..., 2)` 误把第 2 列写成「序号」的问题已修正  
3. **承办律师**：写入段落时若 Range 与表格重叠，仅写入 `Range.Start` 至表格起点，避免污染表格  
4. **黑色字体**：Find 扩展多种红色 ColorIndex / RGB 后统一改黑  
5. **EXE**：`legal_archive.spec` 增加 `delivery_list_filler` 等 hiddenimports  

**验证输出（无需重跑 OCR）：** 用已有 `extracted_fields.json` 重新生成文书见 `outputs/2019-佛山金百纳贸易有限公司_fix/`  

---

## V1.1.3（2026-06-04）

1. **档案卷宗·法院收案号**：填充后自动删除单元格内模板附带的「参考格式：示例案号」  
2. **案号识别**：支持半角括号 `(2019)`，并统一为中文括号 `（2019）`  

---

## V1.1.4（2026-06-04）

1. **法院收案号白名单**：仅保留判决书「民初/民终/民再」+ 执行裁定书「执」案号；排除执保、民函、另案等  
2. **多执行案号**：优先与本案判决同法院、出自「终结本次执行」裁定书段落的一条  
3. **提示词**：明确禁止输出保全/另案/律所函号等无关案号  

---

## V1.1.5（2026-06-04）

1. **表格单页优化**（`table_layout_optimizer.py`）：禁止行跨页断开、整表「段中不分页」  
2. **长单元格**：按模板应用宋体 + 固定行距 20 磅（结案/卷宗等长表用 9–11pt 紧凑字号）  
3. **表头衔接**：标题段落与表格尽量同页  

---

## V1.2（2026-06-05）

**表格保版式 · 单元格映射表**

1. **映射表**（`templates/manifests/*.json`）：标明每格 `fill` / `fixed` / `seq_fill` / `header`，程序只写可填格  
2. **保格式填充**（`word_placeholder_fill.py`）：单元格内 Find 替换【占位符】，不再整格 `Range.Text` 覆盖  
3. **版式优化收紧**：`table_layout_optimizer` 仅禁止跨页断行，不再全表改字号  
4. **工具**：`tools/generate_template_manifest.py` 从模板生成映射初稿；`tools/verify_template_layout.py` 校验固定格  
5. **模板变更**：改 `.doc` 后重新生成并校对对应 JSON  

### 仓库整理（2026-06-05）

- 删除失效测试脚本、旧 Flask 入口、重复修复脚本；`dist/` 仅保留 `案件档案归档V1.3.6/`、`案件档案归档V2/`
- 打包：`legal_archive_v1.spec`（V1.3.6）、`legal_archive.spec`（V2）

### V2.0.3（2026-06-05）

- **表格保形**：可填格文本框隔离填充（`textbox_fill.py`，`fill.mode: textbox`）；填充前后行高快照/恢复；填后自动版式校验（`layout_verify.py`）
- **分文书识别**：`document_segmenter.py` + 分路 prompt（判决书/执行裁定书/委托代理合同）+ `field_merger.py`（`extraction.mode: segmented`）
- **上传升级**：GUI 支持单 PDF / 分类多 PDF / 批量多案件；`batch_processor.py`、`process_archive_sources()`；CLI `--batch` / `--sources`
- manifest v3：43 个可填格增加 `textbox.shape_name`；工具 `tools/patch_manifest_textbox.py`、`tools/convert_fill_cells_to_textbox.py`

### V2.0.1（2026-06-05）

- MinerU 默认后端改为 `pipeline`；启动前检测 torch，缺依赖时给出目标机 pip 安装命令
- 新增 `scripts/fix_mineru_target_pc.ps1` 修复「requires local pipeline dependencies」

### V2.0.0（2026-06-05）

- **版本号 V2.0.0**；打包产物 `案件档案归档V2.exe`
- **仅输出 5 份 docx**（`output.docx_only: true` 默认），不生成 zip、合并 pdf、`extracted_fields.json`
- 主界面 **百度 OCR / MinerU** 切换；目标机 MinerU 路径模板 `config.target-pc.example.json`
- 部署说明：`DEPLOY_V2.md`

### V1.4.0（2026-06-05）

- 主界面 **百度 OCR / MinerU** 分段切换，写入 `ocr.engine`
- MinerU 支持填写 `mineru.exe` 路径；详细设置对话框
- 说明：`OCR_PACKAGING.md`（为何不将 MinerU 打入 EXE）

### V1.3.6（2026-06-05）

- 结案/审办值格：按表头「结案小结」「审（办）结果」定位，左对齐+首行缩进 2 字
- 其余可填格：整格全部段落水平居中 + 单元格垂直居中（修正误将 sheet1 长键判为结案类）

### V1.3.5（2026-06-05）

- 结案小结/审（办）结果：左对齐 + 首行缩进 2 字符
- 其余可填格：水平居中、首行不缩进（字号不变）

### V1.3.4（2026-06-05）

- 可填格统一：楷体_GB2312、左对齐、首行缩进 2 字符、单元格垂直居中
- 结案小结 / 审（办）结果：≤150 字、四号（14pt）楷体

### V1.3.3（2026-06-05）

- 立案审批表案情简介：同格先填内容后清格式说明，避免 `元】` 被破坏为 `元内】`
- 填后修复：「案情简介：」后若仍有模板 XXX，整段替换为提取的案情

### V1.3.2（2026-06-05）

- 同格多占位符从后往前替换，避免偏移错位留下 `】`
- 填后清除孤立【、】；案情简介格式说明整段删除
- 质量监督卡：律师事务所去掉「（固定）」并变黑

### V1.3.1（2026-06-05）

- 填后清理：去除可填格【】残留、参考格式等说明片段；可填区 scoped 变黑
- LLM 字段值去除【】与参考格式残留（`sanitize_field_value`）
- OCR：`max_pages=0` 默认 OCR 全部页；选 PDF 后 GUI 自动填入文档页数

### V1.3.0（2026-06-05）

- **原子填充**：仅替换【】字符跨度（`word_atomic_fill.py`），禁止整格 `Range.Text` 回退
- 长文仅在填入值子 Range 阶梯缩字；填后不再整格压字号/强制行高
- manifest 增加 `offset` 预计算；移除 `AutoFitBehavior` 避免列宽漂移

### V1.2.2（2026-06-05）

- 表格跨页：填充前快照行高，填充后仅压缩已填格并恢复固定行高
- 字段替换逻辑保持 V1.2.1（Find 校验 + 文本回退）

### V1.2.1（2026-06-05）

1. **修复未替换字段**：Word `Find.Execute` 在表格 .doc 中常返回成功但未替换；改为校验后自动回退 `Range.Text.replace`  
