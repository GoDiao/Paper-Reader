# Paper Reader Agent

<div align="center">
  <img src="assets/banner.png" alt="Paper Reader Agent Banner" width="30%" height="30%" />

  <br />
  
  [![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
  [![DeepSeek](https://img.shields.io/badge/DeepSeek-Powered-blue)](https://www.deepseek.com/)
  [![OpenAI](https://img.shields.io/badge/OpenAI-Compatible-412991)](https://openai.com/)

  **Hierarchical Multi-Agent System for Academic Paper Deep Analysis**
  
  [中文文档](README_zh.md) | English
</div>

<br />

## 📖 Introduction

**Paper Reader Agent** is an advanced AI system designed to read, analyze, and synthesize academic papers with a depth that matches human researchers.

<details>
<summary><b>📸 Click to see Screenshots (UI & Features)</b></summary>

| **Modern Web UI (Bilingual)** | **Real-time Progress Tracking** |
|:---:|:---:|
| <img src="assets/webui_en.png" alt="English UI" width="100%"/> | <img src="assets/progress_view.png" alt="Analysis Progress" width="100%"/> |
| *Clean interface with EN/ZH switching* | *Visualize the 5-agent team in action* |

| **Publication-Quality Reports** | **Specialist Deep Dives** |
|:---:|:---:|
| <img src="assets/report_preview.png" alt="Final Report" width="100%"/> | <img src="assets/specialist.png" alt="Specialist Reports" width="100%"/> |
| *Auto-embedded figures & formulas* | *Rich details from specific domains* |

</details>
<br>

**Paper Reader Agent** goes beyond simple summarization...

Unlike standard summary tools, it employs a **Hierarchical Multi-Agent Architecture (1+3+1)** to mimic a professional research team:

1. **Architect**: Deconstructs the paper and plans the reading strategy.
2. **Specialist Team**: Parallel experts analyze Context, Math, and Data.
3. **Editor**: Synthesizes a publication-quality report with embedded figures.

> **Key Feature**: The system detects, extracts, and literally *sees* figures, embedding them directly into the analysis where they are discussed, maintaining full visual context.

---

## 🏗️ Architecture

The system operates using a "Divide and Conquer" strategy orchestrated by a central planner.

<div align="center">
  <img src="assets/archv1.png" alt="Architecture Diagram" width="80%" />
</div>

---

## ✨ Key Features

### 🧠 Hierarchical Intelligence

- **Architect Agent**: Strategic planning of what to read and where to focus.
- **Context Hunter**: Digs for the "real" motivation and hidden assumptions.
- **Math Specialist**: Derives equations and explains physical intuition behind formulas.
- **Data Auditor**: Critically checks baselines, variance, and experimental fairness.

### 👁️ Visual Understanding

- **Smart Extraction**: Custom PDF parsing pipeline (based on PyMuPDF) that segments text and images.
- **Context Preservation**: Figures are kept with their relevant text.
- **Auto-Embedding**: The AI inserts figures into the report exactly when discussing them.

### 💻 Modern Interaction

- **Web Interface**: Clean, responsive UI with real-time analysis progress.
- **Dual-Mode**:
  - `Simple`: Quick architect + math check.
  - `Hierarchical`: Full 5-agent deep dive.
- **Bilingual**: Generates native-quality English and Chinese reports simultaneously.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- API Key (DeepSeek or OpenAI)
- (Optional) CUDA GPU for faster layout analysis

### Installation

```bash
git clone https://github.com/GoDiao/Paper-Reader.git
cd paper_reader
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
DEEPSEEK_API_KEY=sk-your-key
# OR
OPENAI_API_KEY=sk-your-key
```

### Usage

#### 1. Web Interface (Recommended)

Start the server to enjoy the full interactive experience.

```bash
python web_server.py
```

Open **<http://localhost:8000>** in your browser.

#### 2. Command Line

```bash
# Full hierarchical analysis (Default)
python main.py papers/attention_is_all_you_need.pdf

# Save intermediate agent outputs
python main.py paper.pdf --verbose

# Use OpenAI instead of DeepSeek
python main.py paper.pdf --provider openai --model gpt-4o
```

---

## 📂 Output Structure

The system organizes outputs to keep your research clean:

```text
outputs/
└── {Paper_Title}_{Timestamp}/
    ├── paper_analysis.md       # 🇬🇧 Final English Report
    ├── paper_analysis_zh.md    # 🇨🇳 Final Chinese Report
    ├── images/                 # 🖼️ All extracted figures
    │   ├── Figure_1.png
    │   └── ...
    ├── specialists/            # 🕵️ Intermediate Specialist Reports
    │   ├── 01_context_hunter.md
    │   ├── 02_math_specialist.md
    │   └── 03_data_auditor.md
    └── figure_index.json       # Metadata
```

---

## 🛠️ Project Structure

```text
paper_reader/
├── agents/                 # 🤖 The Brains
│   ├── hierarchical_orchestrator.py
│   ├── hierarchical_prompts.py
│   └── ...
├── parsers/                # 👁️ The Eyes
│   └── pdf_parser.py       # Custom Layout Analysis
├── generators/             # 📝 The Scribe
│   └── report_generator.py # Report Assembly
├── backend/                # 🔌 API Server
└── frontend/               # 🖥️ Web UI
```

---

## 🚀 Changelog

### v1.2.0 - Architecture & Performance Improvements

- **🔧 Unified LLM Client Factory**: Centralized LLM configuration, retry/backoff, and timeout handling across all agents. Added optional global concurrency limiting to prevent API rate limits.
- **📊 Fine-grained Progress Events**: Real-time progress updates for each agent (Architect, Context Hunter, Math Specialist, Data Auditor, Editors) with detailed status messages during LLM calls and retries.
- **⚡ Concurrency Optimization**: Eliminated nested thread pools, unified executor management, and improved resource utilization for better performance under concurrent loads.
- **📄 Enhanced PDF Parser**: Improved PyMuPDF implementation with table extraction (Markdown format), mathematical formula region detection, better text structure preservation, and smarter image caption detection (searches above/below images).
- **🔧 Configuration**: New environment variables (`LLM_TIMEOUT_S`, `LLM_MAX_RETRIES`, `LLM_MAX_CONCURRENCY`) for fine-tuning API behavior.
- **📡 Real-time Streaming**: Implemented streaming responses for expert agents (Math, Data, Context), allowing users to see reports generating token-by-token.
- **📐 Math Formula Fix**: Solved critical rendering issues for streamed LaTeX formulas by protecting delimiters (`\[...\]`, `\(...\)`) from Markdown processing.
- **🏗️ Architect Report**: Added a new dedicated "Architect" tab to visualize the reading plan and agent assignments immediately after the planning phase.
- **🖥️ UI UX Improvements**: Moved Specialist Reports to the main view for better visibility and added auto-focus logic to follow the active agent.

### v1.1.0 - Premium UI & Chat Upgrade

- **✨ New UI**: Introduced a "Deep Space" glassmorphism theme for a premium reading experience.
- **🤖 Smart Chat**: Added context summarization to the Chat AI, allowing for longer, more coherent discussions about the paper.
- **📊 Specialist Reports**: View detailed analysis from specific agents (Context Hunter, Math Specialist, Data Auditor) in dedicated tabs.
- **🌐 Bilingual**: Added full English/Chinese language switching.
- **🐛 Fixes**: Resolved table rendering issues and improved chat interface scrolling.

## 🤝 Contributing

Contributions are welcome! Whether it's a new specialist agent, better parsing logic, or UI improvements.

1. Fork the Project
2. Create your Feature Branch
3. Commit your Changes
4. Push to the Branch
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  <b>Star ⭐ this repo if it helped your research!</b>
</div>
