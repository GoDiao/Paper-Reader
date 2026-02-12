# Paper Reader Agent

<div align="center">
  <img src="assets/banner.png" alt="Paper Reader Agent Banner" width="30%" />

  <br />
  
  [![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![DeepSeek](https://img.shields.io/badge/DeepSeek-Powered-blue)](https://www.deepseek.com/)
  [![OpenAI](https://img.shields.io/badge/OpenAI-Compatible-412991)](https://openai.com/)

  **基于层级化多 Agent 架构的学术论文深度解析系统**
  
  [English](README.md) | 中文文档
</div>

<br />

## 📖 简介

**Paper Reader Agent** 是一个先进的 AI 系统，旨在像人类研究员一样深度阅读、分析并综合学术论文。

<details>
<summary><b>📸 点击查看功能截图 (Showcase)</b></summary>

| **现代化双语 Web 界面** | **实时 Agent 协作进度** |
|:---:|:---:|
| <img src="assets/webui_zh.png" alt="中文界面" width="100%"/> | <img src="assets/progress_view.png" alt="分析进度" width="100%"/> |
| *支持中英文一键切换* | *可视化 1+3+1 Agent 团队工作流* |

| **出版级分析报告** | **专家深度分析 (新功能)** |
|:---:|:---:|
| <img src="assets/report_preview.png" alt="最终报告" width="100%"/> | <img src="assets/specialist.png" alt="专家报告" width="100%"/> |
| *自动嵌入公式与插图* | *查看特定领域的深度洞察* |

</details>
<br>

**Paper Reader Agent** 与普通的摘要工具不同...

与普通的摘要工具不同，它采用 **层级化多 Agent 架构 (1+3+1)** 来模拟专业的研究团队：

1. **架构师 (Architect)**：解构论文并规划阅读策略。
2. **专家团队 (Specialist Team)**：并行专家分别分析背景、数学推导和数据实验。
3. **主编 (Editor)**：综合生成出版级质量的报告，并自动嵌入相关图表。

> **核心特性**：系统能够检测、提取并真正“看见”论文中的插图，将其直接嵌入到分析报告的相关讨论中，保留完整的视觉上下文。

---

## 🏗️ 架构设计

系统采用由中心规划者编排的“分而治之”策略。

<div align="center">
  <img src="assets/archv1.png" alt="架构图" width="80%" />
</div>

---

## ✨ 核心功能

### 🧠 层级化智能

- **架构师 (Architect)**：战略性规划阅读重点和方向。
- **背景猎人 (Context Hunter)**：挖掘“真正”的研究动机和隐含假设。
- **数学专家 (Math Specialist)**：推导公式并解释数学背后的物理直觉。
- **数据审计员 (Data Auditor)**：批判性审查基线、方差和实验公平性。

### 👁️ 视觉理解

- **智能提取**：基于 PyMuPDF 的自定义 PDF 解析管线，精确分割文本和图像。
- **上下文保留**：图片与其相关文本保持关联。
- **自动嵌入**：AI 会在讨具体内容时自动将图片插入到报告中。

### 💻 现代化交互

- **Web 界面**：简洁响应式的 UI，支持实时分析进度展示。
- **双模式**：
  - `Simple`：快速架构师 + 数学检查。
  - `Hierarchical`：全功能 5-Agent 深度分析。
- **双语支持**：同时生成原生质量的中文和英文报告。

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- API 密钥 (DeepSeek 或 OpenAI)
- (可选) CUDA GPU 用于加速布局分析

### 安装

```bash
git clone https://github.com/GoDiao/Paper-Reader.git
cd paper_reader
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=sk-your-key
# 或
OPENAI_API_KEY=sk-your-key
```

### 使用方法

#### 1. Web 界面 (推荐)

启动服务器以获得完整的交互体验。

```bash
python web_server.py
```

在浏览器中打开 **<http://localhost:8000>**。

> **说明（Web 模式下的解析后端）**  
> Web 服务当前默认使用 `auto` 策略：  
> - 如果本地已安装 MinerU（`pip install mineru`），会优先尝试 **MinerU** 解析。  
> - 如果 MinerU 未安装或解析失败，则自动回退到 **PyMuPDF** 后端。

#### 2. 命令行 (CLI)

```bash
# 全层级深度分析（默认，自动选择解析后端）
python main.py papers/attention_is_all_you_need.pdf

# 强制使用快速的 PyMuPDF 解析后端
python main.py paper.pdf --parser pymupdf

# 强制使用高保真的 MinerU 解析后端（需要先安装：pip install mineru）
python main.py paper.pdf --parser mineru

# 保存所有 Agent 的中间输出
python main.py paper.pdf --verbose

# 使用 OpenAI 替代 DeepSeek
python main.py paper.pdf --provider openai --model gpt-4o
```

### PDF 解析器：PyMuPDF vs MinerU

- **PyMuPDF（默认，速度快）**  
  - 只依赖 `pymupdf`，无需额外安装大型模型。  
  - 解析速度快，对大部分普通论文已经足够。  
  - 在本项目中进行了增强：支持表格提取、数学区域启发式识别、更智能的图像检测与标题匹配。

- **MinerU（可选，高保真）**  
  - 通过 `pip install mineru` 安装（并按 MinerU 官方文档配置 GPU / 驱动等环境）。  
  - 更擅长保留复杂版式、多栏结构、表格以及公式密集的页面。  
  - 本项目会将 MinerU 产出的 Markdown + 图片规范化为统一的 `ParsedDocument` 结构，下游 Agent 和前端 UI 在不同解析后端之间无缝复用。

> **仓库说明**  
> Git 仓库中只包含 **集成代码**（例如 `parsers/pdf_parser.py`），不会包含 MinerU 的大模型 / 权重文件。  
> MinerU 的模型与检查点会缓存在 `MinerU/ckpt/` 目录下，并已在 `.gitignore` 中忽略，避免误把大文件推送到远端仓库。

---

## 📂 输出结构

系统将输出组织得井井有条：

```text
outputs/
└── {论文标题}_{时间戳}/
    ├── paper_analysis.md       # 🇬🇧 英文最终报告
    ├── paper_analysis_zh.md    # 🇨🇳 中文最终报告
    ├── images/                 # 🖼️ 所有提取的插图
    │   ├── Figure_1.png
    │   └── ...
    ├── specialists/            # 🕵️ 中间专家报告
    │   ├── 01_context_hunter.md
    │   ├── 02_math_specialist.md
    │   └── 03_data_auditor.md
    └── figure_index.json       # 元数据
```

---

## 🛠️ 项目结构

```text
paper_reader/
├── agents/                 # 🤖 大脑
│   ├── hierarchical_orchestrator.py
│   ├── hierarchical_prompts.py
│   └── ...
├── parsers/                # 👁️ 眼睛
│   └── pdf_parser.py       # 自定义布局分析
├── generators/             # 📝 记录员
│   └── report_generator.py # 报告组装
├── backend/                # 🔌 API 服务端
└── frontend/               # 🖥️ Web 前端
```

---

## 🚀 更新日志

### v1.3.0 - MinerU 解析升级

- **🧠 MinerU 解析后端**: 集成 MinerU（Magic-PDF 2.x pipeline）作为高保真 PDF 解析器，更好保留复杂论文的版式结构、表格与数学区域。
- **⚙️ 可切换解析后端**: 支持在命令行通过 `--parser auto|pymupdf|mineru` 以及 Web 模式中选择解析策略，可在更快的 PyMuPDF 与更高质量的 MinerU 之间自由切换，或使用 `auto` 先尝试 MinerU 失败后自动回退到 PyMuPDF。
- **📂 统一输出管线**: 将 MinerU 的输出规整为统一的 `ParsedDocument` + 图像索引格式，下游 LLM Agent、报告生成和前端 UI 在不同解析后端之间无缝复用。

### v1.2.0 - 架构与性能优化

- **🔧 统一 LLM 客户端工厂**: 集中管理所有 Agent 的 LLM 配置、重试/退避和超时处理。新增可选的全局并发限流，防止 API 速率限制。
- **📊 细粒度进度事件**: 为每个 Agent（架构师、背景猎人、数学专家、数据审计员、编辑）提供实时进度更新，在 LLM 调用和重试期间显示详细状态信息。
- **⚡ 并发优化**: 消除嵌套线程池，统一执行器管理，改进资源利用，提升并发负载下的性能。
- **📄 PDF 解析器增强**: 改进的 PyMuPDF 实现，支持表格提取（Markdown 格式）、数学公式区域识别、更好的文本结构保留，以及更智能的图像标题检测（上下搜索）。
- **🔧 配置选项**: 新增环境变量（`LLM_TIMEOUT_S`、`LLM_MAX_RETRIES`、`LLM_MAX_CONCURRENCY`）用于微调 API 行为。
- **📡 实时流式传输**: 为专家 Agent（数学、数据、背景）实现了流式响应，允许用户逐字查看生成过程中的分析报告。
- **📐 数学公式修复**: 解决了流式传输中 LaTeX 公式渲染问题，通过保护定界符（`\[...\]`, `\(...\)`）防止 Markdown 转义错误。
- **🏗️ 架构师报告**: 新增独立的“架构师”标签页，在规划阶段完成后立即展示阅读计划和 Agent 任务分配。
- **🖥️ UI UX 改进**: 将专家报告版块移至主分析视图以提高可见性，并添加了跟随活跃 Agent 的自动聚焦逻辑。

### v1.1.0 - UI 升级与智能对话

- **✨ 全新 UI**: 引入“深空”毛玻璃主题，提供沉浸式阅读体验。
- **🤖 智能对话**: 聊天功能新增上下文总结记忆，支持更长、更连贯的论文探讨。
- **📊 专家报告**: 新增独立标签页展示背景调查、数学分析和数据审计报告。
- **🌐 双语支持**: 完整支持中英文界面一键切换。
- **🐛 问题修复**: 修复了表格渲染问题，优化了聊天界面的滚动交互。

## 🤝 贡献

欢迎提交 PR！无论是新的专家 Agent、更好的解析逻辑，还是 UI 改进。

1. Fork 本项目
2. 创建您的特性分支
3. 提交您的更改
4. 推送到分支
5. 开启 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源。详见 `LICENSE` 文件。

---

<div align="center">
  <b>如果这个项目对您的研究有帮助，请给个 Star ⭐！</b>
</div>
