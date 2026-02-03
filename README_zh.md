# Paper Reader Agent

**一个基于层级化多 Agent 架构的 AI 学术论文深度解析系统，配备交互式 Web 界面。**

[English](README.md) | 中文文档

## 为什么选择 Paper Reader Agent？

**解决关键痛点**：与其他只能分析文本的研究 Agent 不同，Paper Reader Agent **能够自动提取并嵌入学术论文中的图片**到生成的报告中。这解决了现有方案的一个重大局限——视觉内容在分析过程中丢失，导致无法完整理解那些严重依赖图表、实验结果可视化的论文。

**核心优势**：我们的自研 PDF 解析算法能够智能检测、提取并引用所有图片，确保您的分析报告包含完整的视觉上下文，这对于全面理解论文至关重要。

## 核心特性

### 层级化多 Agent 系统

- **架构师 Agent**：规划分析结构并协调专家 Agent
- **专家 Agent**：
  - *Context Hunter*：探索研究背景与相关工作
  - *Math Specialist*：深入数学公式推导
  - *Data Auditor*：严格审查实验结果与统计有效性
- **编辑 Agent**：将专家见解综合为连贯的高质量报告

### 现代化 Web 界面

- **实时进度追踪**：基于 WebSocket 的实时更新
- **交互式渲染**：完美的 KaTeX 公式渲染
- **双语报告**：自动生成中英文对照分析
- **AI 对话**：针对论文内容的多轮问答
- **历史管理**：所有分析结果的持久化存储与检索

### 高级 PDF 处理

- **自研解析算法**：基于 PyMuPDF 构建的智能布局分析引擎，专为学术论文优化
- **公式提取**：高保真保留 LaTeX 公式
- **智能图片检测**：基于区域的智能图片提取与合并
- **表格识别**：结构化提取表格数据

## 快速开始

### 环境要求

- Python 3.8+
- CUDA 兼容 GPU（推荐，用于加速 PDF 解析）
- DeepSeek 或 OpenAI 的 API 密钥

### 安装

```bash
git clone https://github.com/your-username/paper_reader.git
cd paper_reader
pip install -r requirements.txt
```

> **注意**：建议使用 GPU 加速以获得最佳 PDF 解析性能。支持 CPU 模式但速度较慢。

### 配置

在项目根目录创建 `.env` 文件：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
# 或
OPENAI_API_KEY=your_openai_api_key_here
```

或设置环境变量：

```bash
# Windows
set DEEPSEEK_API_KEY=your_api_key

# Linux/Mac
export DEEPSEEK_API_KEY=your_api_key
```

### 运行应用

#### Web 界面（推荐）

启动 Web 服务器：

```bash
python web_server.py
```

然后在浏览器中访问 `http://localhost:8000`

**Web 功能：**

- 拖拽上传 PDF
- 实时分析进度可视化
- 中英文对照报告
- 交互式 AI 讨论
- 导出为 Markdown/PDF/DOCX
- 可搜索的分析历史

#### 命令行界面

```bash
# 基本用法（使用 DeepSeek）
python main.py path/to/paper.pdf

# 指定输出目录
python main.py paper.pdf -o ./my_analysis

# 使用 OpenAI GPT-4
python main.py paper.pdf --provider openai --model gpt-4o

# 详细模式（保存中间输出）
python main.py paper.pdf -v
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `pdf_path` | PDF 文件路径 | (必需) |
| `-o, --output` | 输出目录 | `./output` |
| `--provider` | LLM 提供商 (`openai`/`deepseek`) | `deepseek` |
| `--model` | 模型名称 | 自动选择 |
| `--api-key` | API 密钥 | 从环境变量读取 |
| `--no-gpu` | 禁用 GPU 加速 | `False` |
| `--no-images` | 跳过图片提取 | `False` |
| `-v, --verbose` | 保存中间输出 | `False` |

## 输出结构

```
outputs/
└── {论文名称}_{时间戳}/
    ├── paper_analysis.md       # 英文报告
    ├── paper_analysis_zh.md    # 中文报告
    ├── figure_index.json       # 图片元数据
    ├── images/                 # 提取的图片
    │   ├── Figure_1.png
    │   ├── Figure_2.png
    │   └── ...
    └── specialists/            # 专家 Agent 报告
        ├── 01_context_hunter.md
        ├── 02_math_specialist.md
        └── 03_data_auditor.md
```

## 项目结构

```
paper_reader/
├── backend/                # FastAPI 后端与 WebSocket 管理
│   ├── app.py             # 主 API 端点
│   ├── websocket_manager.py
│   └── report_store.py    # 报告持久化
├── frontend/              # 原生 JS/CSS Web 界面
│   ├── index.html
│   └── static/
│       ├── scripts.js
│       └── styles.css
├── agents/                # 多 Agent 系统
│   ├── orchestrator.py    # 层级化编排
│   ├── architect.py       # 规划 Agent
│   ├── specialists/       # 领域专家 Agent
│   └── editor.py          # 报告综合
├── parsers/               # PDF 处理
│   └── pdf_parser.py      # 自研解析算法
├── generators/            # 报告生成
│   └── report_generator.py
├── main.py                # CLI 入口
└── web_server.py          # Web 服务器入口
```

## 技术栈

- **后端**：FastAPI、WebSocket、asyncio
- **前端**：原生 JavaScript、Showdown.js（Markdown）、KaTeX（LaTeX）
- **PDF 解析**：基于 PyMuPDF 的自研智能布局分析算法
- **LLM 集成**：DeepSeek API / OpenAI API
- **Agent 架构**：层级化多 Agent 与角色专业化
- **存储**：基于 JSON 的持久化，简单且可移植

## 使用场景

- **研究人员**：快速理解领域内的新论文
- **学生**：深入理解复杂的学术材料
- **文献综述**：系统化分析多篇论文
- **论文写作**：学习方法论和实验设计

## 已知问题与限制

- PDF 解析质量取决于原始文档结构
- 建议使用 GPU 以获得合理的解析速度（CPU 模式较慢）
- 大型论文的 LLM API 成本可能累积
- 图片提取可能遗漏复杂布局中的嵌入图片

## 贡献

欢迎贡献！请随时提交 Pull Request。

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 致谢

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) 提供强大的 PDF 处理能力
- [DeepSeek](https://www.deepseek.com/) 提供强大且经济的 LLM API
- 所有本项目的贡献者和用户

---

**如果觉得有用，请给本项目点个 Star！**
