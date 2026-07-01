# 案件归档系统 V5 — 目标机部署说明

## 前置要求（目标 Windows 电脑）

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 / Server 2016+ |
| Python | 3.12 或 3.14（安装时勾选 **Add to PATH**） |
| Microsoft Word | 2007 或更高（模板填充必需） |
| 网络 | 可访问 DeepSeek API、MinerU API（云端 OCR） |
| 磁盘 | 建议 ≥ 2 GB 可用空间 |

## 一、在开发机打包

1. 打开 `F:\GD\web\deploy\pack_for_windows.bat`
2. 等待前端构建 + 打包完成
3. 获得部署包：`%TEMP%\v5_deploy.zip`

## 二、在目标机安装

1. 将 `v5_deploy.zip` 复制到目标电脑
2. 解压到任意目录，例如 `D:\ArchiveV5\`
3. **首次**：双击 `install.bat`（安装依赖并启动）
4. **日常**：双击 `start_server.bat`

解压后目录结构：

```
D:\ArchiveV5\
  install.bat          ← 首次安装
  start_server.bat     ← 日常启动
  install_service.bat  ← 可选：注册 Windows 服务
  部署说明.md
  app\
    web\backend\       ← FastAPI 后端
    web\frontend\dist\ ← 前端静态页（由后端托管）
    templates\         ← Word 模板与映射表
    prompts\           ← LLM 提示词
    *.py               ← V4 核心算法
```

## 三、访问与账号

- 本机：http://127.0.0.1:8000
- 局域网：http://目标机IP:8000

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | admin123 | 管理员（可删案件、管用户、系统设置） |
| zgls | zgls123 | 律师 |

首次启动后请在 **系统设置** 配置：
- DeepSeek API Key
- MinerU API Token

可在 `app\web\.env` 修改端口、管理员密码等（修改后重启服务）。

## 四、防火墙（局域网访问）

以管理员身份运行 PowerShell：

```powershell
New-NetFirewallRule -DisplayName "V5-Archive" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

## 五、注册为 Windows 服务（可选）

1. 下载 [NSSM](https://nssm.cc/download)，将 `nssm.exe` 加入 PATH
2. 双击 `install_service.bat`
3. 服务名：`ArchiveV5`，开机自启

## 六、数据与备份

运行时数据位于：

```
app\web\data\
  archive.db      ← SQLite 数据库
  orgs\           ← 上传的案件文件与归档结果
```

迁移或备份时，复制整个 `app\web\data\` 目录即可保留全部案件数据。

## 七、常见问题

**pip 安装慢或失败**  
使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

**模板填充报错**  
确认已安装 Microsoft Word，且当前 Windows 用户有 Word 使用权限。

**OCR 失败**  
检查系统设置中的 MinerU Token 是否有效，目标机能否访问外网。

**端口被占用**  
修改 `app\web\.env` 中 `V5_PORT=8000` 为其他端口后重启。

## 八、与 V4 的关系

- V4 算法以 `app\*.py` + `app\templates\` 形式随包分发，无需单独安装 V4
- `uvicorn` 必须使用 `--workers 1`（Word COM 单进程限制）
