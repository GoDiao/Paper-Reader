# Deep Research - AI 驱动的网络深度研究工具

## 📋 概述

**Deep Research** 是一个集成在 Paper Reader Agent 中的强大 AI 驱动网络研究工具。它利用 **Tavily** 和 **Valyu** API 对任何主题进行全面、实时的研究，生成带有在线来源引用的详细报告。

### 核心特性

- 🌐 **双 Provider 支持**：在 Tavily（快速、可靠）和 Valyu（全面、多层级定价）之间选择
- ⚡ **实时流式传输**：使用 SSE（服务器发送事件）流式技术实时观看研究进度
- 📚 **引用管理**：多种引用格式（编号、APA、MLA、Chicago）
- 💾 **研究历史**：持久化存储，支持浏览、搜索和删除
- 📤 **导出到 Notion**：一键导出，完整保留格式、表格和 LaTeX 公式
- 🎨 **现代化 UI**：专用的 `/researcher` 页面，采用玻璃拟态设计和响应式布局

---

## 🚀 快速开始

### 访问 Deep Research

1. **启动服务器**：
   ```bash
   python web_server.py
   ```

2. **打开 Deep Research 页面**：
   ```
   http://localhost:8000/researcher
   ```

### 配置

在 `.env` 文件中添加：

```env
# Tavily API（Deep Research 必需）
TAVILY_API_KEY=tvly-your_api_key_here

# Valyu API（Deep Research 备选 provider）
VALYU_API_KEY=your_valyu_api_key_here

# Notion 导出（可选）
NOTION_SECRET=your_notion_secret
NOTION_PARENT_PAGE_ID=your_parent_page_id
IMGBB_API_KEY=your_imgbb_api_key
```

### 安装依赖

```bash
pip install tavily-python  # Tavily provider
# 或
pip install valyu  # Valyu provider
pip install sse-starlette>=2.0.0  # SSE 流式传输
```

---

## 🎯 使用指南

### 步骤 1：输入研究主题

在研究表单方面板中：
- 在文本域中输入研究问题或主题
- 尽量具体以获得更好的结果（例如"Transformer 架构在 NLP 领域的最新进展"而非"AI"）

### 步骤 2：配置研究设置

**Provider 选择**：
- **Tavily**：快速、可靠，具有深度研究能力
  - 模型：`mini`（快速）、`pro`（全面）、`auto`（自动）
- **Valyu**：全面，多层级定价
  - 模式：`fast` ($0.10)、`standard` ($0.50)、`heavy` ($2.50)、`max` ($15.00)

**引用格式**：
- **Numbered**：[1], [2], [3]...
- **APA**：(作者，年份)
- **MLA**：(作者 页码)
- **Chicago**：作者 - 日期格式

### 步骤 3：开始研究

点击 **"Start Research"** 按钮：
- 进度条显示实时状态
- 内容在生成时实时流式传输
- 来源列表逐步显示

### 步骤 4：审查与导出

研究完成后：
- **查看结果**：完整的 Markdown 报告，包含表格和 LaTeX 公式
- **检查来源**：所有引用来源列表，带 favicon 图标
- **保存**：研究自动保存到历史记录
- **导出到 Notion**：一键导出，完整格式保留
- **复制**：复制整个报告到剪贴板
- **管理历史**：查看、搜索或删除过往研究

---

## 🏗️ 架构设计

### 后端组件

```
backend/
├── app.py                      # FastAPI 主应用
├── research_store.py           # 研究持久化层
├── deep_research_utils.py      # 轮询和进度工具
└── websocket_manager.py        # WebSocket 进度管理器

services/
├── tavily_service.py           # Tavily API 封装
├── valyu_service.py            # Valyu API 封装
└── deep_research_errors.py     # 结构化错误处理
```

### 前端组件

```
frontend/
├── researcher.html             # 独立 Deep Research 页面
├── static/
│   ├── styles.css              # 全局样式（玻璃拟态主题）
│   └── scripts.js              # 共享工具函数
```

### 数据流

```
用户输入 → WebSocket/SSE → 后端 → Tavily/Valyu API
                ↓
        实时进度更新
                ↓
        Markdown 渲染
                ↓
        自动保存到 research_store
                ↓
        历史管理
```

---

## 📊 API 端点

### 研究执行

**POST** `/api/deep-research`
```json
{
  "query": "研究主题",
  "provider": "tavily",
  "model": "auto",
  "citation_format": "numbered"
}
```
响应：通过 WebSocket 发送进度

**GET** `/api/deep-research/stream`
```
?query=Research+topic&model=auto&citation_format=numbered
```
响应：SSE 流，包含进度事件

### 研究管理

**GET** `/api/research?limit=50`
- 列出研究历史（最新优先）
- 返回摘要，不含完整内容

**GET** `/api/research/{research_id}`
- 获取完整研究记录
- 包含内容、来源、元数据

**POST** `/api/research/save`
```json
{
  "title": "研究标题",
  "query": "原始查询",
  "content": "Markdown 内容",
  "sources": [...],
  "model": "auto",
  "citation_format": "numbered"
}
```

**DELETE** `/api/research/{research_id}`
- 从历史中删除研究

**POST** `/api/research/{research_id}/export/notion`
- 导出到 Notion，完整格式保留
- 返回 Notion 页面 URL

---

## 💾 数据结构

### 研究记录

```json
{
  "id": "research_xxx",
  "title": "研究标题",
  "query": "原始研究问题",
  "content": "完整 Markdown 报告",
  "sources": [
    {
      "title": "来源标题",
      "url": "https://...",
      "favicon": "https://..."
    }
  ],
  "model": "auto|mini|pro",
  "citation_format": "numbered|apa|mla|chicago",
  "metadata": {},
  "created_at": 1234567890000,
  "updated_at": 1234567890000
}
```

### 存储位置

```
data/
└── researches.json  # 独立于 reports.json
```

---

## 🎨 功能详情

### 实时流式传输（SSE）

Deep Research 使用 **服务器发送事件（SSE）** 进行内容流式传输：

**优势**：
- ✅ 简单、HTTP 兼容的协议
- ✅ 自动重连
- ✅ 低延迟、实时更新
- ✅ 单次持久连接

**流事件**：
- `started`：研究启动
- `progress`：内容块（流式 Markdown）
- `completed`：研究完成
- `error`：发生错误

### Markdown 渲染

完整的 Markdown 支持，带增强功能：
- **表格**：原生 Markdown 表格
- **LaTeX 公式**：`$...$`（行内）、`$$...$$`（块级）
- **代码块**：使用 highlight.js 语法高亮
- **列表**：正确缩进的嵌套列表

### 导出到 Notion

一键导出，包含：
- **原生表格**：Notion Table Block（非图片）
- **LaTeX 渲染**：完美的公式渲染
- **嵌套列表**：正确的缩进层级
- **图片**：上传到 ImgBB 并嵌入

---

## 🔧 Provider 对比

| 特性 | Tavily | Valyu |
|------|--------|-------|
| **速度** | 快速 | 因模式而异 |
| **定价** | 按次付费 | 分层级 ($0.10-$15) |
| **模型** | mini, pro, auto | fast, standard, heavy, max |
| **适用场景** | 通用研究 | 预算控制 |
| **流式传输** | ✅ 原生 SSE | ✅ 基于轮询 |

---

## ⚠️ 故障排除

### 常见问题

**1. 缺少 API 密钥**
```
错误：TAVILY_API_KEY not set
```
**解决方案**：添加到 `.env` 并重启服务器

**2. 研究超时**
```
错误：Research timeout (600s)
```
**解决方案**：尝试更简单的查询或升级模型层级

**3. Notion 导出失败**
```
错误：NOTION_SECRET not configured
```
**解决方案**：在 `.env` 中添加 Notion 凭证

**4. 流式传输不工作**
```
浏览器控制台：EventSource connection failed
```
**解决方案**：检查服务器日志，确保安装了 `sse-starlette`

---

## 📚 文档

更多详细信息：

- **[Tavily API 文档](deep_research/tavily/)**：Tavily provider 使用指南
- **[Valyu API 文档](deep_research/valyu/)**：Valyu provider 使用指南
- **[流式传输实现](DEEP_RESEARCH_STREAMING.md)**：SSE 流式传输技术细节
- **[独立页面设计](deep_research/DEEP_RESEARCH_IMPLEMENTATION.md)**：架构文档

---

## 🎯 最佳实践

### 编写好的研究查询

✅ **好的示例**：
- "量子计算纠错的最新进展（2024-2025）"
- "LoRA 与 QLoRA 在 LLM 微调中的对比"
- "气候变化对珊瑚礁生态系统的影响"

❌ **过于宽泛**：
- "量子计算"
- "人工智能"
- "气候"

### 选择合适的模型

**Tavily**：
- `mini`：快速概览，简单主题
- `pro`：全面分析，复杂主题
- `auto`：让 Tavily 决定（推荐）

**Valyu**：
- `fast` ($0.10)：快速事实，简单查询
- `standard` ($0.50)：平衡研究（推荐）
- `heavy` ($2.50)：深度分析，学术主题
- `max` ($15.00)：最大全面性

---

## 🔮 未来增强

计划中的功能：
1. **研究对比**：并排对比多个研究
2. **研究模板**：保存常用研究配置
3. **批量研究**：并行执行多个研究
4. **标签与分类**：组织研究历史
5. **全文搜索**：搜索研究内容
6. **PDF/DOCX 导出**：更多导出格式
7. **研究分享**：生成分享链接
8. **CLI 支持**：Deep Research 命令行接口

---

## ✅ 总结

Deep Research 提供完整、AI 驱动的网络研究工作流：

- ✅ **双 Provider 支持**：Tavily 和 Valyu 满足不同需求
- ✅ **实时流式传输**：SSE 技术实现实时进度
- ✅ **丰富渲染**：Markdown、表格、LaTeX 公式
- ✅ **持久历史**：独立存储，支持 CRUD 操作
- ✅ **Notion 导出**：一键导出，完整格式保留
- ✅ **现代化 UI**：玻璃拟态设计的专用页面

无论您是在探索新的研究主题、收集背景信息，还是进行全面的文献综述，Deep Research 都能为您提供高效、AI 驱动的网络研究所需的所有工具。🎉
