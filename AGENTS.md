# AGENTS.md — 案件归档 V6

## 权威文档

- 当前版本与能力：`docs/V6_RELEASE.md`
- 业务验收规则：`docs/归档生成标准.md`
- 归档排序规则：`docs/ARCHIVE_ORDER.md`
- Web 开发运行：`web/README.md`
- 部署：`web/deploy/DEPLOY_README.md`
- 模板与浏览器表格：`docs/模板参考资料整理.md`

## 当前架构

- Web 后端：`web/backend/`，FastAPI + SQLite + 异步任务。
- Web 前端：`web/frontend/`，Vue 3 + Element Plus。
- 核心归档算法仍位于项目根目录，由 `web/backend/app/core/v4_bridge.py` 复用；`v4_bridge` 是兼容层名称，不代表当前产品版本。
- macOS / Linux 默认 `preview-only`，不生成 DOCX、不调用 Word；核对后的 HTML 系统表由 Chrome/Chromium 生成 PDF，再进入现有归档合并器。Windows 仍可使用 DOCX/Word COM 流程。
- LLM 与 OCR 配置按账号保存；案件和文件按组织隔离。

## 个案归档路径

| 路径 | 输入 | 分析入口 |
|---|---|---|
| A 单卷综合 | 1 个 PDF（default 类型） | `segment_by_catalog` 卷内切分 |
| B 多份分类 | 多个 PDF + 文件名/类型 | `build_units_from_sources`，每文件 1 Unit |

共用：`analyze_archive` → 缺失确认 → 系统表人工核对 → `assemble_archive`（支持的平台）→ 完整归档 PDF。

## 核心约束

- 源 PDF 页守恒：跳过不插页，页数不守恒时 `success=False`。
- DocumentUnit 表示整份文书；`unknown` 归入 `evidence`；同槽多文书按 `doc_id` 排序。
- `archive.order_mode` 支持 `catalog`（标准目录序）和 `original`（源 PDF 页序）。
- 五份系统表的固定格不可编辑，`fill/clear/seq_fill` 格可编辑。
- 不得让一个账号读取或覆盖另一个账号的 LLM/OCR 密钥。
- 不自动执行 git commit。

## 运行与验证

```bash
# Web 服务（先构建 frontend/dist）
cd web/backend
../.venv312/bin/python run.py

# 核心逻辑
web/.venv312/bin/python -m pytest tests/ -q

# Web 后端
cd web/backend
../.venv312/bin/python -m pytest tests/ -q

# Web 前端
cd web/frontend
npm run build
```

修改应优先运行与改动范围对应的测试；涉及归档流水线、账号隔离或系统表时，提交前运行以上三组验证。
