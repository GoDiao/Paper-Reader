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

在浏览器中打开 **<http://localhost:8000**。>

#### 2. 命令行 (CLI)

```bash
# 全层级深度分析 (默认)
python main.py papers/attention_is_all_you_need.pdf

# 保存所有 Agent 的中间输出
python main.py paper.pdf --verbose

# 使用 OpenAI 替代 DeepSeek
python main.py paper.pdf --provider openai --model gpt-4o
```

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
