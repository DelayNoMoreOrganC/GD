# OCR 方案与 EXE 打包说明

## 方案选择（界面切换）

| 方案 | 适用场景 | 配置要求 |
|------|----------|----------|
| **百度 OCR（API）** | 无独显、不想装 MinerU、页数较少 | `baidu_ocr` 三套密钥 + DeepSeek |
| **MinerU（本地）** | 已装 MinerU + NVIDIA GPU、卷宗页多、避免百度额度 | `mineru.cli_path`（可选）+ DeepSeek |

主程序 `legal_archive_gui.py`（V1.4+）顶栏 **OCR 方案** 分段按钮切换，选择会写入 `config.json` 的 `ocr.engine`（`baidu` / `mineru`）。

## MinerU 能否内置进 EXE？

**不建议、也基本不可行** 将完整 MinerU 打进同一个 PyInstaller EXE：

| 原因 | 说明 |
|------|------|
| 体积 | PyTorch + 模型缓存通常 **10～20 GB+**，远超常规模块 |
| 启动 | 每次从 EXE 解压模型到临时目录，首启极慢 |
| 授权与更新 | MinerU 独立升级，与归档程序解耦更稳妥 |
| 已有安装 | 目标机 **已安装 MinerU** 时，只需指定路径即可 |

### 推荐部署方式（目标电脑已装 MinerU）

1. 安装 MinerU 到固定目录，例如：  
   `D:\Tools\.venv-mineru\Scripts\mineru.exe`
2. 在 GUI 中选 **MinerU（本地）**，点击 **浏览** 填入 `mineru.exe`；或使用现成模板 `config.target-pc.example.json`：

```json
{
  "ocr": { "engine": "mineru" },
  "mineru": {
    "cli_path": "C:\\Users\\PC\\AppData\\Local\\Programs\\Python\\Python313\\Scripts\\mineru.exe",
    "api_url": "",
    "quality": "ultra"
  }
}
```

（对应 pip 安装：Python 3.13，MinerU 3.1.12。）

3. `cli_path` **留空** 时，程序会按顺序查找：  
   - `config.json` 中的 `mineru.cli_path`  
   - 系统 `PATH` 中的 `mineru`  
   - `%LOCALAPPDATA%\Programs\Python\Python3*\Scripts\mineru.exe`（自动匹配 3.13 等）  
   - 目标机默认路径 `C:\Users\PC\...\Python313\Scripts\mineru.exe`

4. 可选：本机常驻 `mineru-api`，在设置里填 `api_url: http://127.0.0.1:8000`，避免每次冷启动模型。

### EXE 打包内容

`案件档案归档.exe`（`legal_archive.spec`）包含：

- 归档 GUI、Word 填充、DeepSeek 调用逻辑  
- **不包含** MinerU / PyTorch / 模型  

分发时附带：

- `config.json.example`（含 `ocr` / `mineru` 字段）  
- `MINERU_V2_SETUP.md`（仅 MinerU 机需要）  
- 本文件 `OCR_PACKAGING.md`

### 若必须“一键目录”分发

可采用 **绿色包文件夹**（非单文件 EXE）：

```
案件档案归档/
  案件档案归档.exe
  config.json
  templates/
  mineru_portable/          ← 可选：复制已装好的 venv 或官方便携包
    Scripts/mineru.exe
```

在 `config.json` 中用相对路径指向同目录下的 `mineru.exe`（需使用绝对路径或启动脚本先 `cd` 到该目录）。

## 配置文件字段速查

```json
{
  "ocr": { "engine": "baidu" },
  "baidu_ocr": { "app_id": "", "api_key": "", "secret_key": "", "mode": "basic" },
  "mineru": {
    "cli_path": "",
    "api_url": "",
    "quality": "ultra",
    "gpu_device": "0"
  },
  "deepseek": { "api_key": "" },
  "local_ocr": { "max_pages": 0 }
}
```

切换引擎后无需重装 EXE，改 `ocr.engine` 或点界面按钮即可。
