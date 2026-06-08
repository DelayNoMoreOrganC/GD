# 案件档案一键归档 — EXE 分发说明

## 适用环境

- **Windows 10/11**
- 已安装 **Microsoft Word**（用于填充 `.doc` 模板并导出 PDF）
- 可访问互联网（百度 OCR + DeepSeek API）

## 目录结构（拷贝到其他电脑）

```
案件档案归档/
├── 案件档案归档.exe      # 主程序
├── config.json           # API 配置（首次从 example 复制后填写）
├── config.json.example
├── templates/
│   └── bundled/          # 5 份律所 Word 模板（.doc）
│       ├── 立案审批表.doc
│       ├── 送达材料清单.doc
│       ├── 档案卷宗.doc
│       ├── 结案报告表.doc
│       └── 质量监督卡.doc
└── outputs/              # 运行后自动创建，归档结果在此
```

## 首次使用

1. 将 `config.json.example` 复制为 `config.json`。
2. 填写：
   - `deepseek.api_key` — DeepSeek API
   - `baidu_ocr.app_id` / `api_key` / `secret_key` — 百度文字识别（建议 `mode: basic`）
3. 双击 `案件档案归档.exe`，选择案件 PDF，点击「开始归档」。

## 界面说明

- macOS 风格简洁界面：大标题、卡片式表单、蓝色主按钮
- 运行日志默认折叠，需要时点击「运行日志」展开
- 命令行模式（测试/批处理）：`案件档案归档.exe "案件.pdf" 25`

## 输出内容

每次处理在 `outputs\案件名_时间戳\` 下生成：

- 5 份已填写的 `.docx`（保留原始表格版式）
- `extracted_fields.json` — 提取字段
- `案件名_归档资料.zip`
- `案件名_归档资料.pdf` — 五份文书合并（需 Word）

## 在本机重新打包 EXE

```bat
cd F:\GD
build_exe.bat
```

打包结果在 `dist\案件档案归档\`。

## 常见问题

| 现象 | 处理 |
|------|------|
| 提示配置不完整 | 检查 `config.json` 密钥是否填写 |
| PDF 文本提取失败 | 百度 OCR 额度/密钥；或增大 OCR 页数 |
| 合并 PDF 失败 | 确认已安装 Word，且未被占用 |
| 模板未生成 | 确认 `templates\bundled` 下 5 个 `.doc` 齐全 |

## 开发模式（未打包）

```bat
py legal_archive_gui.py
py run_archive.py "D:\path\to\case.pdf" 30
```
