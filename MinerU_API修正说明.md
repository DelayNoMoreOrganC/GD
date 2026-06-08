# MinerU API修正说明

## 修正时间
2026-06-03

## 修正原因
根据MinerU官方文档 https://mineru.net/apiManage/docs 的要求，MinerU Precision Extract API需要使用文件上传+轮询查询的三步流程，而不是直接POST文件。

## 修正内容

### 修正前的错误实现
```python
# 错误的方式：直接POST文件到API
response = requests.post(
    config['minerU']['api_url'],
    files={'file': f},
    headers=headers,
    timeout=60
)
```

### 修正后的正确实现
```python
# 第一步：获取上传URL
response = requests.post(
    'https://mineru.net/api/v4/file-urls/batch',
    headers=headers_get,
    json=upload_request,
    timeout=30
)

# 第二步：PUT上传文件
upload_response = requests.put(
    upload_url,
    data=f,
    timeout=120
)

# 第三步：轮询查询结果
result_response = requests.get(
    f'https://mineru.net/api/v4/extract-results/batch/{batch_id}',
    headers=headers_get,
    timeout=30
)
```

## 技术细节

### 1. 获取上传URL
- 端点：`POST https://mineru.net/api/v4/file-urls/batch`
- 请求体：包含文件名和文件大小
- 响应：返回batch_id和signed上传URL

### 2. PUT上传文件
- 使用返回的signed URL进行PUT上传
- 上传实际的PDF文件内容
- 超时时间设置为120秒

### 3. 轮询查询结果
- 端点：`GET https://mineru.net/api/v4/extract-results/batch/{batch_id}`
- 轮询状态：pending → processing → succeeded/failed
- 最多等待2分钟（60次×2秒）

## 配置更新

### 移除的配置项
- `minerU.api_url`（不再需要，使用官方固定端点）

### 保留的配置项
- `minerU.enabled`（启用/禁用MinerU OCR）
- `minerU.token`（MinerU访问令牌）

## 测试连接更新

### 修正前的测试
```python
response = requests.get(config['minerU']['api_url'], headers=headers)
```

### 修正后的测试
```python
response = requests.get(
    'https://mineru.net/api/v4/files',
    headers=headers,
    timeout=10
)
```

## 降级方案
如果MinerU API调用失败，系统会自动降级到本地PDF解析方法：
1. PyPDF2
2. pdfplumber
3. PyMuPDF（新增）

## 影响范围
- `app_chinese.py` 中的 `extract_pdf_text()` 函数
- `app_chinese.py` 中的 `test_connection()` 函数
- `app_chinese.py` 中的 `load_config()` 函数

## 向后兼容性
- 现有配置文件中的`api_url`字段会被忽略
- Token配置保持不变
- 用户体验无影响，只是API调用方式更符合官方规范

## 测试建议
1. 上传一个小的PDF文件测试MinerU OCR
2. 检查控制台输出的三步流程日志
3. 如果MinerU失败，验证降级方案是否正常工作
4. 在系统配置页面测试Token连接

---

**修正完成！系统已重启并运行在 http://localhost:5000**
