# 一键归档（路线 A）

## 用法

```bash
cd F:\GD
py run_archive.py "D:\路径\案件卷宗.pdf"
# 可选第二参数：OCR 抽样页数上限，默认 30
py run_archive.py "案件.pdf" 30
```

## 输出

在 `outputs/案件名_时间戳/` 下生成：

| 文件 | 说明 |
|------|------|
| `立案审批表.docx` … 共 5 份 | 按律所原模板填充 |
| `extracted_fields.json` | LLM 提取的字段 |
| `*_归档资料.zip` | 全部打包 |
| `*_归档资料.pdf` | 5 份文书合并（类似参考卷宗首页） |

## Web

上传 PDF 时默认 `mode=archive`，与命令行相同。

## 参考

- 提取提示词：`prompts/extract_prompt.txt`（与桌面「参考提示词.txt」一致）
- 模板：微信目录下 5 份 `.doc` 原文件
