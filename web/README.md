# 案件归档系统 V5 (Web 版)

## 架构
- 后端：FastAPI + SQLite(WAL) + 异步任务
- 前端：Vue3 + Element Plus + Vite
- OCR：MinerU API（云端）
- LLM：DeepSeek API
- 模板填充：Windows Server + Word (win32com)
- 复用 V4 全部核心算法（通过 sys.path 桥接，不改动 V4 代码）

## 目录结构
```
web/
  backend/    FastAPI 后端
  frontend/   Vue3 SPA
  data/       运行时数据（数据库、案件文件）—— gitignore
  deploy/     nginx 配置 + Windows 服务安装
```

## 开发启动

### 单命令启动（前后端一体）
```powershell
cd F:\GD\webackend
python run.py
```
后端启动后，浏览器直接打开 http://127.0.0.1:8000 即可使用。
首次启动自动创建默认律所 + admin 账号（admin / admin123，可在 .env 改）。案件归档系统 V5 (Web 版)

## 架构
- 后端：FastAPI + SQLite(WAL) + 异步任务
- 前端：Vue3 + Element Plus + Vite
- OCR：MinerU API（云端）
- LLM：DeepSeek API
- 模板填充：Windows Server + Word (win32com)
- 复用 V4 全部核心算法（通过 sys.path 桥接，不改动 V4 代码）

## 目录结构
```
web/
  backend/    FastAPI 后端
  frontend/   Vue3 SPA
  data/       运行时数据（数据库、案件文件）—— gitignore
  deploy/     nginx 配置 + Windows 服务安装
```

## 开发启动

### 后端
```powershell
cd F:\GD\web\backend
& 'C:\Python\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
首次启动自动创建默认律所 + admin 账号（admin / admin123，可在 .env 改）。

### 前端（开发模式）
```powershell
cd F:\GD\web\frontend
npm install
npm run dev   # http://localhost:5173，自动代理 /api 到后端
```

## 生产部署
1. 构建前端：`cd frontend && npm run build`（产物到 frontend/dist）
2. 后端读取 frontend/dist 自动托管 SPA
3. 启动后端：`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1`
4. nginx 反向代理 HTTPS（见 deploy/nginx.conf.example）
5. 注册 Windows 服务（见 deploy/install_service.bat，需 NSSM）

## 配置
- 系统设置在管理后台「系统设置」页配置（DeepSeek Key、MinerU Token、排序模式）
- 环境变量（.env）：V5_SECRET_KEY、V5_HOST、V5_PORT、V5_BOOTSTRAP_ADMIN_*

## 与 V4 的关系
- V4 代码（F:\GD 根目录）零改动，V5 通过 `app/core/v4_bridge.py` 注入 sys.path 复用
- V5 所有新代码在 `web/` 下，不污染 V4
- V4 的 .doc 模板（templates/bundled）和提示词（prompts）通过 V4 自身路径解析复用

## 限制
- uvicorn 必须 `--workers 1`（Word COM 进程级单例）
- 同一时刻只允许一个归档任务在模板填充阶段（Semaphore 串行）
- 服务器需安装 Microsoft Word
