# 案件归档 V2 — MinerU 本地高精度 OCR

V2 使用 [MinerU](https://github.com/opendatalab/MinerU) 在本地 GPU 解析 PDF，**不消耗百度 OCR 额度**。文书填充、DeepSeek 抽字段与 V1.3 相同。

## 推荐硬件（已按此调优）

| 项目 | 建议 |
|------|------|
| CPU | i9-14900KF（多核有利于 PDF 渲染线程） |
| 内存 | 64 GB |
| GPU | RTX 3080 20GB（`hybrid-auto-engine` 默认后端） |
| 磁盘 | SSD，模型缓存约 10–20 GB |

## 一、安装 MinerU（一次性）

在 **PowerShell** 中执行（建议使用独立虚拟环境）：

```powershell
cd F:\GD
py -m venv .venv-mineru
.\.venv-mineru\Scripts\Activate.ps1
py -m pip install -U pip
```

### 1. CUDA 版 PyTorch（与 3080 驱动匹配）

到 [PyTorch 官网](https://pytorch.org/get-started/locally/) 选择 **CUDA 12.x + Windows + pip**，例如：

```powershell
py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

### 2. 安装 MinerU（完整能力）

```powershell
py -m pip install -U "mineru[all]"
```

验证：

```powershell
mineru --version
```

首次运行会自动下载模型，请保持网络畅通。

## 二、配置文件

### 目标机已安装 MinerU（Python 3.13 / 用户 PC）

若 MinerU 位于：

`C:\Users\PC\AppData\Local\Programs\Python\Python313\Scripts\mineru.exe`（版本 3.1.12）

可直接复制项目中的 **`config.target-pc.example.json`** 为 EXE 旁的 `config.json`，仅改 `deepseek.api_key`。

或在 GUI 选 **MinerU（本地）** 后点 **浏览** 选中上述 `mineru.exe`。  
`cli_path` 留空时，程序也会自动扫描 `%LOCALAPPDATA%\Programs\Python\Python3*\Scripts\mineru.exe`。

### 通用步骤

1. 复制 `config.json.v2.example` 或 `config.target-pc.example.json` 为 EXE 同目录下的 `config.json`。
2. 填写 `deepseek.api_key`。
3. 确认：

```json
"ocr": { "engine": "mineru" },
"mineru": {
  "quality": "ultra",
  "backend": "hybrid-auto-engine",
  "method": "ocr",
  "lang": "ch",
  "force_ocr": true,
  "gpu_device": "0",
  "render_threads": 8,
  "timeout_seconds": 7200
}
```

### 精细度说明（`quality`）

| 值 | 说明 |
|----|------|
| **ultra**（默认） | `hybrid-auto-engine` + 强制 `ocr`，表格/公式开启，适合律所扫描卷宗 |
| high | 混合引擎 + `auto` 方法，电子版略快 |
| fast | 仅 `pipeline` + OCR，显存占用更低 |

## 三、运行（与 V1 同一程序）

### 图形界面

```powershell
py legal_archive_gui.py
```

在界面 **OCR 方案** 中点选 **MinerU（本地）**，可浏览填写 `mineru.exe` 路径。  
`legal_archive_gui_v2.py` 仅为兼容入口，已跳转到上述主程序。

### 命令行

```powershell
py run_archive_v2.py "D:\卷宗\案件.pdf" 0
```

`0` 表示解析全部页；数字 N 表示只解析前 N 页（调试时可减小）。

## 四、加速：常驻 MinerU API（可选）

每次归档若都冷启动模型较慢。可先开一个终端常驻服务：

```powershell
$env:CUDA_VISIBLE_DEVICES="0"
mineru-api --host 127.0.0.1 --port 8000
```

在 `config.json` 中设置：

```json
"mineru": {
  "api_url": "http://127.0.0.1:8000"
}
```

后续 GUI 会通过 `--api-url` 连接该服务，避免重复加载模型。

## 五、环境自检

```powershell
py tools\check_mineru_env.py
```

## 六、与 V1 并存

| 版本 | OCR | 入口 |
|------|-----|------|
| V1.3.x | 百度 OCR | `legal_archive_gui.py` / `案件档案归档.exe` |
| V2.0 | MinerU 本地 | `legal_archive_gui_v2.py` / `案件档案归档V2.exe` |

同一 `config.json` 可通过 `"ocr": { "engine": "baidu" }` 或 `"mineru"` 切换（V1 EXE 仍默认百度）。

## 七、常见问题

**Q: 提示未找到 mineru**  
A: 激活安装了 MinerU 的 venv，或将 `mineru.cli_path` 设为完整路径，例如 `F:\GD\.venv-mineru\Scripts\mineru.exe`。

**Q: CUDA out of memory**  
A: 将 `quality` 改为 `fast`，或关闭其他占 GPU 程序。

**Q: 解析很慢**  
A: 首包模型下载；之后使用 `api_url` 常驻；适当减小 `local_ocr.max_pages` 做试跑。

**Q: 仍想用百度 OCR**  
A: V2 配置中设 `"fallback_baidu": true` 并填写 `baidu_ocr` 密钥，MinerU 失败时自动回退。
