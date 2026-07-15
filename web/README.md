# 案件归档系统 V6（Web）

后端使用 FastAPI + SQLite，前端使用 Vue 3 + Element Plus。macOS / Linux 默认在浏览器中核对原表版式；Windows 可继续使用 Word COM 生成 DOCX 和完整归档 PDF。

## 目录

```text
web/
├── backend/     FastAPI、数据库、任务和账号隔离
├── frontend/    Vue SPA 与五份系统表编辑器
├── data/        运行数据（数据库、上传文件、输出文件；不提交）
└── deploy/      部署说明、Windows 打包和服务脚本
```

## 开发启动

### macOS / Linux

```bash
cd web/frontend
npm ci
npm run build

cd ../backend
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
../.venv/bin/python run.py
```

打开 <http://127.0.0.1:8000>。默认 `preview-only`，不会生成 DOCX，也不依赖 Microsoft Word；服务器使用 Chrome/Chromium 将网页表格生成 PDF 并合并完整归档。

### Windows

```powershell
cd F:\GD\web\frontend
npm install
npm run build

cd ..\backend
python -m pip install -r requirements.txt
python run.py
```

如需 DOCX 与完整归档合并，在 `web/.env` 中设置 `V5_PREVIEW_ONLY=false`，并确保服务器安装 Microsoft Word。

### 前端热更新

```bash
cd web/frontend
npm run dev
```

开发服务器默认位于 <http://localhost:5173>，并将 `/api` 代理到后端。

## 账号与数据隔离

- 注册用户拥有自己的组织空间，案件和文件按组织隔离。
- DeepSeek Key、模型地址和 MinerU Token 按登录账号保存；同组织账号之间也不共享。
- 账号所属律所名称用于立案审批表的制表单位。
- 默认管理员为 `admin / admin123`，生产环境必须修改密码和 `V5_SECRET_KEY`。

## 配置

配置从 `web/.env` 读取。为兼容既有环境，变量仍使用 `V5_` 前缀：

```dotenv
V5_SECRET_KEY=replace-with-a-long-random-secret
V5_HOST=127.0.0.1
V5_PORT=8000
V5_PREVIEW_ONLY=true
V5_CHROMIUM_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
V5_REGISTRATION_ENABLED=true
V5_BOOTSTRAP_ADMIN_USER=admin
V5_BOOTSTRAP_ADMIN_PASSWORD=change-this-password
```

局域网测试将 `V5_HOST` 改为 `0.0.0.0`，然后使用 `http://服务器局域网IP:端口` 访问。公网部署应通过 HTTPS 反向代理，不要直接暴露开发配置。

## V6 核心流程

1. 上传材料并生成任务。
2. OCR、切分、目录映射和字段提取。
3. 任务进入 `awaiting_review`。
4. 在五份系统表中修订文字、字体、字号、对齐和自定义文本框。
5. 确认后生成系统表 PDF，计算目录页码并合并完整归档 PDF。

## 测试

```bash
# 后端
cd web/backend
../.venv312/bin/python -m pytest tests/ -q

# 前端
cd ../frontend
npm run build
```

核心归档逻辑测试位于项目根目录 `tests/`。

## 运行限制

- Word COM 模式使用 `--workers 1`。
- macOS / Linux 的预览模式不提供 DOCX 下载，但可生成并下载最终归档 PDF。
- HTML → PDF 需要 Chrome/Chromium；未自动检测到时配置 `V5_CHROMIUM_PATH`。
- OCR 与 LLM 调用需要各账号自行配置可用的云端 API。
