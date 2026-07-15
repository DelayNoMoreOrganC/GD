# 案件归档系统 V6

V6 是面向律师事务所的案件归档 Web 系统。它将 OCR、文书切分、字段提取、系统表核对和归档输出串成一套流程，并在生成最终成果前保留人工核对闸门。

## 当前能力

- macOS / Linux：默认使用浏览器预览模式，不生成 DOCX、不依赖 Microsoft Word；五份系统表按原表格版式编辑，并通过无头 Chrome/Chromium 生成 PDF 后合并完整案卷。
- Windows：可使用 Word COM 生成 DOCX，并继续合并完整归档 PDF。
- 多账号：案件数据按组织隔离；LLM Key、模型地址和 OCR Token 按登录账号独立保存。
- 表格核对：支持单元格内容、字体、字号、对齐和自定义文本框；长内容自动增高。
- 审办结果：同时分析诉讼和执行材料，案卷存在执行证据时综合表述执行措施与结果。

## 快速启动（macOS / Linux）

```bash
cd web/frontend
npm ci
npm run build

cd ../backend
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
../.venv/bin/python run.py
```

浏览器打开 <http://127.0.0.1:8000>。局域网测试时，在 `web/.env` 设置 `V5_HOST=0.0.0.0`，重启后访问 `http://本机局域网IP:8000`。

`V5_` 环境变量前缀为兼容既有部署而保留，不代表当前产品版本。

首次启动会创建管理员账号，默认值为 `admin / admin123`。投入使用前请修改默认密码和 `V5_SECRET_KEY`。

## 目录

```text
web/backend/        FastAPI API、任务与账号隔离
web/frontend/       Vue 3 浏览器界面和系统表编辑器
templates/          Word 模板、单元格 manifest 与参考索引
prompts/            案件字段提取提示词
tests/              核心归档逻辑回归测试
docs/               当前业务与部署文档
```

## 验证

```bash
# 核心逻辑
web/.venv312/bin/python -m pytest tests/ -q

# Web 后端
cd web/backend
../.venv312/bin/python -m pytest tests/ -q

# Web 前端
cd ../frontend
npm run build
```

## 当前文档

- [V6 版本说明](docs/V6_RELEASE.md)
- [Web 开发与运行](web/README.md)
- [部署说明](web/deploy/DEPLOY_README.md)
- [归档生成标准](docs/归档生成标准.md)
- [归档排序规则](docs/ARCHIVE_ORDER.md)
- [模板参考资料整理](docs/模板参考资料整理.md)

旧的 V4 循环计划、0619 开发记录和 V5 汇报稿已移除；这些材料描述的阶段状态与当前 V6 实现不一致。
