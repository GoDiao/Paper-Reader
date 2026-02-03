# Paper Reader Agent

**An AI-powered academic paper analysis system with hierarchical multi-agent architecture and interactive web interface.**

[中文文档](README_zh.md) | English

## Why Paper Reader Agent?

**Solves a Critical Pain Point**: Unlike other research agents that can only analyze text, Paper Reader Agent **automatically extracts and embeds figures** from academic papers into the generated reports. This addresses a major limitation in existing solutions where visual content is lost during analysis, making it impossible to fully understand papers that rely heavily on diagrams, charts, and experimental results.

**Key Differentiator**: Our custom PDF parsing algorithm intelligently detects, extracts, and references all figures, ensuring your analysis reports include the complete visual context necessary for comprehensive paper understanding.

## Key Features

### Hierarchical Multi-Agent System

- **Architect Agent**: Plans analysis structure and coordinates specialist agents
- **Specialist Agents**:
  - *Context Hunter*: Explores research background and related work
  - *Math Specialist*: Deep-dives into mathematical formulations and derivations
  - *Data Auditor*: Critically examines experimental results and statistical validity
- **Editor Agent**: Synthesizes specialist insights into coherent, publication-quality reports

### Modern Web Interface

- **Real-time Progress Tracking**: WebSocket-powered live updates during analysis
- **Interactive Rendering**: Perfect LaTeX formula rendering with KaTeX
- **Bilingual Reports**: Automatic generation of English and Chinese analysis
- **AI Chat**: Multi-turn Q&A about paper content
- **History Management**: Persistent storage and retrieval of all analyses

### Advanced PDF Processing

- **Custom Parsing Algorithm**: Proprietary layout analysis engine optimized for academic papers
- **Formula Extraction**: Preserves LaTeX equations with high fidelity using PyMuPDF
- **Smart Figure Detection**: Intelligent region-based image extraction and merging
- **Table Recognition**: Structured extraction of tabular data

## Quick Start

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

> **Note**: GPU acceleration is recommended for optimal PDF parsing performance. CPU mode is supported but significantly slower.

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

#### Web Interface (Recommended)

Launch the web server:

```bash
python web_server.py
```

Then navigate to `http://localhost:8000` in your browser.

**Web Features:**

- Drag-and-drop PDF upload
- Real-time analysis progress visualization
- Side-by-side English/Chinese reports
- Interactive AI discussion
- Export to Markdown/PDF/DOCX
- Searchable analysis history

#### Command Line Interface

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

## CLI Arguments

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

## Output Structure

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

## Project Structure

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
│   └── pdf_parser.py      # Custom parsing algorithm
├── generators/            # Report generation
│   └── report_generator.py
├── main.py                # CLI entry point
└── web_server.py          # Web server entry point
```

## Technical Stack

- **Backend**: FastAPI, WebSocket, asyncio
- **Frontend**: Vanilla JavaScript, Showdown.js (Markdown), KaTeX (LaTeX)
- **PDF Parsing**: Custom algorithm built on PyMuPDF with intelligent layout analysis
- **LLM Integration**: DeepSeek API / OpenAI API
- **Agent Architecture**: Hierarchical multi-agent with role specialization
- **Storage**: JSON-based persistence for simplicity and portability

## Use Cases

- **Researchers**: Quickly understand new papers in your field
- **Students**: Deep comprehension of complex academic materials
- **Literature Review**: Systematic analysis of multiple papers
- **Paper Writing**: Learn from methodology and experimental design

## Known Issues & Limitations

- PDF parsing quality depends on the original document structure
- GPU recommended for reasonable parsing speed (CPU mode is slow)
- LLM API costs can accumulate with large papers
- Image extraction may miss figures embedded in complex layouts

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) for details

## Acknowledgments

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for robust PDF processing capabilities
- [DeepSeek](https://www.deepseek.com/) for powerful and affordable LLM API
- All contributors and users of this project

---

**Star this repo if you find it useful!**
