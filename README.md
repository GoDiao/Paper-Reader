# Paper Reader Agent

📚 **An AI-powered academic paper analysis system with hierarchical multi-agent architecture and interactive web interface.**

[中文文档](README_zh.md) | English

## ✨ Key Features

### 🤖 Hierarchical Multi-Agent System

- **Architect Agent**: Plans analysis structure and coordinates specialist agents
- **Specialist Agents**:
  - *Context Hunter*: Explores research background and related work
  - *Math Specialist*: Deep-dives into mathematical formulations and derivations
  - *Data Auditor*: Critically examines experimental results and statistical validity
- **Editor Agent**: Synthesizes specialist insights into coherent, publication-quality reports

### 🌐 Modern Web Interface

- **Real-time Progress Tracking**: WebSocket-powered live updates during analysis
- **Interactive Rendering**: Perfect LaTeX formula rendering with KaTeX
- **Bilingual Reports**: Automatic generation of English and Chinese analysis
- **AI Chat**: Multi-turn Q&A about paper content
- **History Management**: Persistent storage and retrieval of all analyses

### 📄 Advanced PDF Processing

- **Academic-grade Parsing**: Powered by MinerU (magic-pdf) for superior layout analysis
- **Formula Extraction**: Preserves LaTeX equations with high fidelity
- **Figure Extraction**: Automatically extracts and embeds figures in reports
- **Table Recognition**: Structured extraction of tabular data

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- CUDA-compatible GPU (recommended for faster PDF parsing)
- API key from DeepSeek or OpenAI

### Installation

```bash
git clone https://github.com/your-username/paper_reader.git
cd paper_reader
pip install -r requirements.txt
```

> ⚠️ **Note**: MinerU requires GPU acceleration for optimal performance. CPU mode is supported but significantly slower.

### Configuration

Create a `.env` file in the project root:

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here
```

Alternatively, use environment variables:

```bash
# Windows
set DEEPSEEK_API_KEY=your_api_key

# Linux/Mac
export DEEPSEEK_API_KEY=your_api_key
```

### Running the Application

#### 🌐 Web Interface (Recommended)

Launch the web server:

```bash
python web_server.py
```

Then navigate to `http://localhost:8000` in your browser.

**Web Features:**

- 📤 Drag-and-drop PDF upload
- ⚡ Real-time analysis progress visualization
- 🌍 Side-by-side English/Chinese reports
- 💬 Interactive AI discussion
- 📥 Export to Markdown/PDF/DOCX
- 📚 Searchable analysis history

#### 💻 Command Line Interface

```bash
# Basic usage with DeepSeek
python main.py path/to/paper.pdf

# Specify output directory
python main.py paper.pdf -o ./my_analysis

# Use OpenAI GPT-4
python main.py paper.pdf --provider openai --model gpt-4o

# Verbose mode (saves intermediate outputs)
python main.py paper.pdf -v
```

## 📋 CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `pdf_path` | Path to PDF file | (required) |
| `-o, --output` | Output directory | `./output` |
| `--provider` | LLM provider (`openai`/`deepseek`) | `deepseek` |
| `--model` | Model name | Auto-selected |
| `--api-key` | API key | From environment |
| `--no-gpu` | Disable GPU acceleration | `False` |
| `--no-images` | Skip image extraction | `False` |
| `-v, --verbose` | Save intermediate outputs | `False` |

## 📁 Output Structure

```
outputs/
└── {paper_name}_{timestamp}/
    ├── paper_analysis.md       # English report
    ├── paper_analysis_zh.md    # Chinese report
    ├── figure_index.json       # Figure metadata
    ├── images/                 # Extracted figures
    │   ├── Figure_1.png
    │   ├── Figure_2.png
    │   └── ...
    └── specialists/            # Specialist agent reports
        ├── 01_context_hunter.md
        ├── 02_math_specialist.md
        └── 03_data_auditor.md
```

## 🏗️ Project Structure

```
paper_reader/
├── backend/                # FastAPI backend & WebSocket manager
│   ├── app.py             # Main API endpoints
│   ├── websocket_manager.py
│   └── report_store.py    # Report persistence
├── frontend/              # Vanilla JS/CSS web interface
│   ├── index.html
│   └── static/
│       ├── scripts.js
│       └── styles.css
├── agents/                # Multi-agent system
│   ├── orchestrator.py    # Hierarchical orchestration
│   ├── architect.py       # Planning agent
│   ├── specialists/       # Domain-specific agents
│   └── editor.py          # Report synthesis
├── parsers/               # PDF processing
│   └── pdf_parser.py      # MinerU integration
├── generators/            # Report generation
│   └── report_generator.py
├── main.py                # CLI entry point
└── web_server.py          # Web server entry point
```

## 🔧 Technical Stack

- **Backend**: FastAPI, WebSocket, asyncio
- **Frontend**: Vanilla JavaScript, Showdown.js (Markdown), KaTeX (LaTeX)
- **PDF Parsing**: MinerU (magic-pdf) - State-of-the-art academic PDF parser
- **LLM Integration**: DeepSeek API / OpenAI API
- **Agent Architecture**: Hierarchical multi-agent with role specialization
- **Storage**: JSON-based persistence for simplicity and portability

## 🎯 Use Cases

- **Researchers**: Quickly understand new papers in your field
- **Students**: Deep comprehension of complex academic materials
- **Literature Review**: Systematic analysis of multiple papers
- **Paper Writing**: Learn from methodology and experimental design

## 🐛 Known Issues & Limitations

- PDF parsing quality depends on the original document structure
- GPU recommended for reasonable parsing speed (CPU mode is slow)
- LLM API costs can accumulate with large papers
- Image extraction may miss figures embedded in complex layouts

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- [MinerU](https://github.com/opendatalab/MinerU) for excellent PDF parsing
- [DeepSeek](https://www.deepseek.com/) for powerful and affordable LLM API
- All contributors and users of this project

---

**Star ⭐ this repo if you find it useful!**
