# 案件档案归档 V2.0.3 — 部署指南（目标电脑 PC）

## 版本说明

| 项目 | V2.0.3 |
|------|--------|
| 程序版本 | V2.0.3 |
| 输出 | **仅 5 份 docx**，不生成 zip、合并 pdf、`extracted_fields.json` |
| OCR | 界面切换 **百度 OCR** / **MinerU 本地** / **MinerU API（线上）** |
| 表格填充 | **文本框隔离填充**（`fill.mode: textbox`），行高锁定 + 版式校验 |
| 字段提取 | **分文书识别**（判决书/执行裁定书/委托代理合同，`extraction.mode: segmented`） |
| 上传 | 单 PDF 卷宗 / 分类多 PDF / 批量多案件 |
| 目标机 MinerU | `C:\Users\PC\AppData\Local\Programs\Python\Python313\Scripts\mineru.exe`（3.1.12） |

五份文书文件名：

1. `立案审批表.docx`
2. `送达材料清单.docx`
3. `档案卷宗.docx`
4. `结案报告表.docx`
5. `质量监督卡.docx`

输出目录示例：`outputs\案件名_20260605_120000\`（该文件夹内**只有**上述 5 个文件）。

---

## 一、开发机打包（只需做一次）

在 `F:\GD` 执行：

```powershell
cd F:\GD
py -m PyInstaller legal_archive.spec -y
```

生成：`dist\案件档案归档.exe`

将以下内容打成部署包文件夹（建议压缩为 zip 发给目标机）：

```
案件档案归档V2.0.2/（EXE：`案件档案归档V2.0.2.exe`，版本号见 `app_version.py`）
├── 案件档案归档.exe          ← 从 dist 复制，可改名为此
├── config.json               ← 由 config.target-pc.example.json 改名并改密钥
├── config.target-pc.example.json
├── MINERU_V2_SETUP.md
├── OCR_PACKAGING.md
├── DEPLOY_V2.md              ← 本文件
├── prompts/
│   └── extract_prompt.txt
└── templates/
    ├── bundled/              ← 5 个 .doc 模板
    │   ├── 立案审批表.doc
    │   ├── 送达材料清单.doc
    │   ├── 档案卷宗.doc
    │   ├── 结案报告表.doc
    │   └── 质量监督卡.doc
    └── manifests/            ← 5 个 .json 映射表
```

---

## 二、目标电脑环境要求

| 组件 | 要求 |
|------|------|
| 系统 | Windows 10/11 64 位 |
| Microsoft Word | 已安装（用于 .doc 模板填充） |
| 网络 | 可访问 DeepSeek API |
| MinerU（推荐） | 已安装，见下方路径 |
| NVIDIA 驱动 | 使用 MinerU 时需 CUDA 可用 |

**MinerU（用户 PC 已具备）：**

```
C:\Users\PC\AppData\Local\Programs\Python\Python313\Scripts\mineru.exe
```

命令行可执行 `mineru --version` 应显示 3.1.12。

**重要：** 仅有 `pip install mineru` 不够，还必须安装 **PyTorch（CUDA）** 与 **`mineru[pipeline]`**，否则会出现 `hybrid-auto-engine requires local pipeline dependencies` 报错。

在目标机 PowerShell 执行（已提供脚本）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fix_mineru_target_pc.ps1
```

或手动：

```powershell
$py = "C:\Users\PC\AppData\Local\Programs\Python\Python313\python.exe"
& $py -m pip install -U pip
& $py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
& $py -m pip install -U "mineru[pipeline]"
```

`config.json` 中建议使用 `"backend": "pipeline"`（程序 V2.0.1 默认 ultra 已改为 pipeline）。

---

## 三、目标电脑安装步骤

### 1. 解压部署包

例如解压到：`D:\案件档案归档V2.0.2\`

### 2. 配置 config.json

复制 `config.target-pc.example.json` 为 `config.json`（若包内已有则直接编辑），至少修改：

```json
{
  "ocr": { "engine": "mineru" },
  "deepseek": {
    "api_key": "你的 DeepSeek API Key"
  },
  "mineru": {
    "cli_path": "C:\\Users\\PC\\AppData\\Local\\Programs\\Python\\Python313\\Scripts\\mineru.exe",
    "quality": "ultra"
  },
  "output": {
    "docx_only": true
  }
}
```

- `cli_path` 可留空（程序会自动查找 Python313 下的 mineru.exe）。
- 若使用百度 OCR：改 `"ocr": { "engine": "baidu" }` 并填写 `baidu_ocr` 三项密钥。

### 3. 首次运行

1. 双击 `案件档案归档.exe`
2. 界面选 **MinerU（本地）**（或百度 OCR）
3. 状态栏显示 **MinerU 就绪** / 百度已配置
4. 可选：**详细设置 → 测试 MinerU**

### 4. 处理案件 PDF

1. **选取** 案件卷宗 PDF
2. **解析页数**：`0` = 全部页
3. 点击 **开始归档**
4. 完成后打开 `outputs\案件名_时间戳\`，确认 **仅有 5 个 docx**

---

## 四、配置项速查

| 配置 | 说明 |
|------|------|
| `output.docx_only` | `true`（默认）：仅 5 份 docx；`false`：额外 zip、合并 pdf、json |
| `ocr.engine` | `mineru` 或 `baidu` |
| `mineru.cli_path` | MinerU 可执行文件全路径 |
| `mineru.quality` | `ultra`（推荐）/ `high` / `fast` |
| `local_ocr.max_pages` | `0` = 解析 PDF 全部页 |

---

## 五、常见问题

**Q：输出里还有 zip 或 json？**  
A：检查 `config.json` 中 `"docx_only": true`。

**Q：MinerU 找不到？**  
A：在 GUI 填 `cli_path`，或把 `Python313\Scripts` 加入系统 PATH。

**Q：只要 docx 但想保留字段 json 调试？**  
A：临时设 `"docx_only": false`，或开发机用 `py legal_archive_gui.py` 跑。

**Q：如何恢复 V1 打包行为（含 zip）？**  
A：`"output": { "docx_only": false }`。

---

## 六、开发机直接运行（不打包）

```powershell
cd F:\GD
py legal_archive_gui.py
```

命令行：

```powershell
py legal_archive_gui.py "D:\test\案件.pdf" 0
```
