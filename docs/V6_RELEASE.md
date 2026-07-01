# V6 版本说明

> **发布标识**：`release(V6)`  
> **定位**：在 V5 Web 平台基础上，增加「预览核对闸门」与浏览器内 Word 编辑，归档合并前可人工校对系统表。

---

## 概述

V6 不改变 V4 核心归档算法，主要增强 **Web 端人机协同**：

1. **分析完成后暂停**：任务进入 `awaiting_review`（待核对），不再直接合并 PDF。
2. **浏览器内编辑 Word**：5 份系统表在页面内预览、修改格式与内容（`@eigenpal/docx-editor-vue`）。
3. **确认后合并**：核对无误后点击「确认合并归档 PDF」，再执行 PDF 拼装。
4. **已完成任务可回看**：案件页「已完成归档」区提供「预览编辑」入口，可再次打开 Word 编辑并保存。

---

## 主要功能

| 功能 | 说明 |
|------|------|
| 预览核对闸门 | 新增任务状态 `awaiting_review`；`run_archive` 在生成系统表后暂停 |
| 分析快照持久化 | `analysis_snapshot.py` 保存字段、目录、docx 路径，支持恢复与增量保存 |
| 流程拆分 | `run_archive`（分析 + 填表）与 `run_assemble`（合并 PDF）分离 |
| 浏览器 Word 编辑 | `DocxReviewEditor.vue` 组件，A4 纸面布局、自适应缩放 |
| 文档 API | `GET/PUT /api/tasks/{id}/docx/{template}` 读写单份系统表 |
| 合并 API | `POST /api/tasks/{id}/assemble` 确认后触发 PDF 合并 |
| 案件页快捷入口 | 已完成归档任务可一键进入预览编辑页 |
| 结案小结提示词 | 补充「结案通知书、调解文书」等来源说明 |

---

## 技术变更

### 后端（`web/backend/`）

- `models.py`：`TaskStatus.awaiting_review`
- `services/analysis_snapshot.py`：快照读写、docx 目录管理
- `services/archive_service.py`：拆分分析/合并；`regenerate_templates`、`save_template_docx`
- `routers/tasks.py`：fields 补丁、regenerate、assemble、docx 读写
- `archive_pipeline.py`：`generate_system_templates(..., work_dir=)` 支持指定工作目录

### 前端（`web/frontend/`）

- `components/DocxReviewEditor.vue`：Word 编辑器封装
- `views/TaskProgress.vue`：待核对 / 已完成任务的编辑 UI
- `views/CaseDetail.vue`：「预览编辑」按钮
- `views/Dashboard.vue`：「待核对」状态标签
- 依赖：`@eigenpal/docx-editor-vue`

### 测试

- `tests/test_v6_analysis_snapshot.py`

---

## 使用流程（V6）

1. 登录 → 新建案件 → 上传 PDF → 一键生成
2. OCR / 切分 / 字段提取完成后，任务变为 **待核对**
3. 在核对页切换 5 张系统表 tab，浏览器内直接编辑 Word
4. **保存当前表格** / **保存全部表格**
5. 点击 **确认无误，合并归档 PDF** → 任务完成，可下载 PDF / DOCX / ZIP
6. 日后在案件页「已完成归档」→ **预览编辑**，可再次修改 Word 文书

---

## 与 V5 的关系

- V5：Web 壳 + V4 引擎，一键生成后直接出 PDF
- V6：在 V5 基础上增加 **合并前人工闸门** 与 **在线 Word 编辑**，算法层仍复用 V4

---

## 部署说明

与 V5 相同：Windows Server + Word COM + `npm run build` 构建前端。  
构建后需刷新浏览器缓存（Ctrl+F5）。

默认账号：`admin / admin123`
