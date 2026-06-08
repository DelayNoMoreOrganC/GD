# 🎯 完整配置系统使用指南

## ✅ 系统已成功启动！

### 访问地址
```
🌐 http://localhost:5000
🌐 http://127.0.0.1:5000
🌐 http://192.168.31.93:5000
```

---

## 🔧 三大核心问题已解决

### 1️⃣ **MinerU OCR集成** ✅

#### 界面位置
- 访问主页 → 点击"Configuration"标签
- 找到"MinerU OCR API"部分

#### 配置步骤
1. **勾选"Enable MinerU OCR API"**
2. **填写MinerU API URL**（你提供的API地址）
3. **填写API Key**（如果需要认证）
4. **点击"Test MinerU Connection"测试连接**

#### 如何使用
```
✅ 如果你有MinerU API：
   - 填写API URL和Key
   - 系统会自动使用MinerU进行PDF OCR处理
   - 确保最准确的文本提取

❌ 如果你没有MinerU API：
   - 不勾选"Enable MinerU OCR API"
   - 系统会使用本地PDF解析方法（PyPDF2/pdfplumber/PyMuPDF）
```

---

### 2️⃣ **LLM配置界面** ✅

#### 支持三种模式

##### **A. OpenAI API（推荐）**
```
LLM Provider: OpenAI API
API URL: https://api.openai.com/v1/chat/completions
API Key: sk-你的OpenAI密钥
Model: gpt-4 或 gpt-3.5-turbo
```

##### **B. Anthropic Claude API**
```
LLM Provider: Anthropic Claude API
API URL: https://api.anthropic.com/v1/messages
API Key: sk-ant-你的Claude密钥
Model: claude-3-sonnet-20240229
```

##### **C. 本地模型（Ollama）**
```
LLM Provider: Local Model (Ollama)
Local Model URL: http://localhost:11434/api/generate
```

#### 配置步骤
1. **选择LLM Provider**（下拉菜单）
2. **填写对应的API信息**
3. **点击"Test LLM Connection"测试连接**
4. **点击"Save Configuration"保存配置**

#### 界面体现
- ✅ 清晰的三个选项卡：Configuration / Process PDF / Download
- ✅ LLM配置部分直接在界面上可见
- ✅ 提供测试连接按钮，验证API是否可用

---

### 3️⃣ **自定义输出位置** ✅

#### 配置位置
```
Configuration标签 → Output Configuration部分
```

#### 设置步骤
1. **填写"Custom Output Path"**
   - 例如：`D:\LegalDocuments\Output`
   - 留空则只保存到默认位置

2. **点击"Save Configuration"**

#### 文件保存位置
```
📁 默认位置：F:\GD\outputs\
📁 自定义位置：你设置的路径（如果配置了）
```

#### 下载方式
- **Process PDF标签**：处理完成后自动显示下载按钮
- **Download标签**：
  - 📥 Download All Files (ZIP) - 打包下载所有文件
  - 📄 Download Individual Files - 单独下载每个文件

---

## 🚀 完整使用流程

### 第一次使用（配置）

1. **访问系统**
   ```
   打开浏览器 → http://localhost:5000
   ```

2. **配置MinerU（如果有）**
   ```
   Configuration标签 → 勾选Enable MinerU → 填写API → Test连接 → 保存
   ```

3. **配置LLM（必须）**
   ```
   Configuration标签 → 选择LLM Provider → 填写API信息 → Test连接 → 保存
   ```

4. **配置输出路径（可选）**
   ```
   Configuration标签 → 填写Custom Output Path → 保存
   ```

### 日常使用（处理PDF）

1. **Process PDF标签**
   ```
   拖拽PDF文件到上传区域
   ```

2. **点击"Upload & Process"**
   ```
   等待1-3分钟（取决于PDF大小和API响应时间）
   ```

3. **自动跳转到Download标签**
   ```
   系统会自动显示生成的5个文件
   ```

4. **下载文件**
   ```
   点击"Download All Files (ZIP)" 或 单独下载每个文件
   ```

---

## 📋 生成的5个文件

| 文件名 | 模板 | 内容 |
|--------|------|------|
| 立案审批表_filled.doc | 立案审批表 | 案件基本信息、律师信息、收费标准 |
| 送达材料清单_filled.doc | 送达材料清单 | 案号、委托方、材料清单列表 |
| 档案卷宗_filled.doc | 档案卷宗 | 详细案件信息、审级、法院收案号 |
| 结案报告表_filled.doc | 结案报告表 | 结案小结、费用情况、律师意见 |
| 质量监督卡_filled.doc | 质量监督卡 | 案号、承办律师、质量调查项 |

---

## 🔥 技术特性

### ✅ 真实API集成
- MinerU OCR API（如果配置）
- OpenAI/Claude API（支持多种LLM）
- 本地模型（Ollama）

### ✅ 配置持久化
- 配置保存在`config.json`文件
- 下次启动自动加载

### ✅ 错误处理
- API连接测试功能
- 详细的错误提示信息
- 降级方案（MinerU失败时使用本地解析）

### ✅ 格式保护
- 宋体四号
- 固定值20磅行距
- 表格结构100%保留

---

## 🛠️ 故障排除

### 问题1：LLM连接测试失败
**解决方案：**
- 检查API Key是否正确
- 检查API URL是否正确
- 确认API账户有余额
- 尝试切换到本地模型

### 问题2：MinerU连接测试失败
**解决方案：**
- 检查API URL是否可访问
- 检查API Key是否正确
- 不使用MinerU，系统会自动降级

### 问题3：PDF处理失败
**解决方案：**
- 检查PDF文件是否损坏
- 尝试使用更小的PDF文件
- 检查LLM API是否正常工作

### 问题4：下载按钮无响应
**解决方案：**
- 刷新页面重新下载
- 检查自定义输出路径是否有写入权限
- 直接到`F:\GD\outputs\`文件夹查看文件

---

## 📞 配置示例

### OpenAI配置示例
```
LLM Provider: OpenAI API
API URL: https://api.openai.com/v1/chat/completions
API Key: sk-proj-xxxxxxxxxxxxx
Model: gpt-4
```

### Claude配置示例
```
LLM Provider: Anthropic Claude API
API URL: https://api.anthropic.com/v1/messages
API Key: sk-ant-xxxxxxxxxxxxx
Model: claude-3-sonnet-20240229
```

### 本地模型配置示例
```
LLM Provider: Local Model (Ollama)
Local Model URL: http://localhost:11434/api/generate
```

---

## 🎉 总结

### ✅ 已解决的问题
1. **MinerU集成**：支持真实API调用，提供配置界面和测试功能
2. **LLM配置**：三种模式可选，界面清晰，测试功能完善
3. **自定义输出**：支持自定义路径，多种下载方式

### 🚀 立即开始
1. 访问 `http://localhost:5000`
2. 进入Configuration标签配置API
3. 进入Process PDF标签上传文件
4. 自动生成5个文件并下载

---

**完整的配置系统已就绪！所有问题都已解决。**

> **阿里人讲究闭环。从配置到处理到下载，全流程可视化，可测试，可验证。这才是结果导向。**
