# Deep Research - AI-Powered Web Research Tool

## 📋 Overview

**Deep Research** is a powerful AI-driven web research tool integrated into Paper Reader Agent. It leverages **Tavily** and **Valyu** APIs to conduct comprehensive, real-time research on any topic, generating detailed reports with citations from online sources.

### Key Features

- 🌐 **Dual Provider Support**: Choose between Tavily (fast, reliable) and Valyu (comprehensive, multi-tier pricing)
- ⚡ **Real-time Streaming**: Watch research progress live with SSE (Server-Sent Events) streaming technology
- 📚 **Citation Management**: Multiple citation formats (Numbered, APA, MLA, Chicago)
- 💾 **Research History**: Persistent storage with browse, search, and delete capabilities
- 📤 **Export to Notion**: One-click export with full formatting, tables, and LaTeX equations
- 🎨 **Modern UI**: Dedicated `/researcher` page with glassmorphism design and responsive layout

---

## 🚀 Quick Start

### Access Deep Research

1. **Start the server**:
   ```bash
   python web_server.py
   ```

2. **Open Deep Research page**:
   ```
   http://localhost:8000/researcher
   ```

### Configuration

Add the following to your `.env` file:

```env
# Tavily API (required for Deep Research)
TAVILY_API_KEY=tvly-your_api_key_here

# Valyu API (alternative provider for Deep Research)
VALYU_API_KEY=your_valyu_api_key_here

# Notion Export (optional)
NOTION_SECRET=your_notion_secret
NOTION_PARENT_PAGE_ID=your_parent_page_id
IMGBB_API_KEY=your_imgbb_api_key
```

### Install Dependencies

```bash
pip install tavily-python  # For Tavily provider
# OR
pip install valyu  # For Valyu provider
pip install sse-starlette>=2.0.0  # For SSE streaming
```

---

## 🎯 Usage Guide

### Step 1: Enter Research Topic

In the research form panel:
- Enter your research question or topic in the textarea
- Be specific for better results (e.g., "Latest developments in transformer architectures for NLP" vs "AI")

### Step 2: Configure Research Settings

**Provider Selection**:
- **Tavily**: Fast, reliable, with deep research capabilities
  - Models: `mini` (fast), `pro` (comprehensive), `auto` (automatic)
- **Valyu**: Comprehensive, multi-tier pricing
  - Modes: `fast` ($0.10), `standard` ($0.50), `heavy` ($2.50), `max` ($15.00)

**Citation Format**:
- **Numbered**: [1], [2], [3]...
- **APA**: (Author, Year)
- **MLA**: (Author Page)
- **Chicago**: Author-Date format

### Step 3: Start Research

Click **"Start Research"** button:
- Progress bar shows real-time status
- Content streams live as it's generated
- Sources appear progressively

### Step 4: Review & Export

After research completes:
- **View Results**: Full Markdown report with tables and LaTeX equations
- **Check Sources**: List of all referenced sources with favicons
- **Save**: Research is auto-saved to history
- **Export to Notion**: One-click export with full formatting
- **Copy**: Copy entire report to clipboard
- **Manage History**: View, search, or delete past researches

---

## 🏗️ Architecture

### Backend Components

```
backend/
├── app.py                      # Main FastAPI application
├── research_store.py           # Research persistence layer
├── deep_research_utils.py      # Polling and progress utilities
└── websocket_manager.py        # WebSocket progress manager

services/
├── tavily_service.py           # Tavily API wrapper
├── valyu_service.py            # Valyu API wrapper
└── deep_research_errors.py     # Structured error handling
```

### Frontend Components

```
frontend/
├── researcher.html             # Independent Deep Research page
├── static/
│   ├── styles.css              # Global styles (glassmorphism theme)
│   └── scripts.js              # Shared utilities
```

### Data Flow

```
User Input → WebSocket/SSE → Backend → Tavily/Valyu API
                ↓
        Real-time Progress
                ↓
        Markdown Rendering
                ↓
        Auto-save to research_store
                ↓
        History Management
```

---

## 📊 API Endpoints

### Research Execution

**POST** `/api/deep-research`
```json
{
  "query": "Research topic",
  "provider": "tavily",
  "model": "auto",
  "citation_format": "numbered"
}
```
Response: Progress via WebSocket

**GET** `/api/deep-research/stream`
```
?query=Research+topic&model=auto&citation_format=numbered
```
Response: SSE stream with progress events

### Research Management

**GET** `/api/research?limit=50`
- List research history (most recent first)
- Returns summary without full content

**GET** `/api/research/{research_id}`
- Get full research record
- Includes content, sources, metadata

**POST** `/api/research/save`
```json
{
  "title": "Research title",
  "query": "Original query",
  "content": "Markdown content",
  "sources": [...],
  "model": "auto",
  "citation_format": "numbered"
}
```

**DELETE** `/api/research/{research_id}`
- Delete research from history

**POST** `/api/research/{research_id}/export/notion`
- Export to Notion with full formatting
- Returns Notion page URL

---

## 💾 Data Structure

### Research Record

```json
{
  "id": "research_xxx",
  "title": "Research title",
  "query": "Original research question",
  "content": "Full Markdown report",
  "sources": [
    {
      "title": "Source title",
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

### Storage Location

```
data/
└── researches.json  # Independent from reports.json
```

---

## 🎨 Features Detail

### Real-time Streaming (SSE)

Deep Research uses **Server-Sent Events (SSE)** for content streaming:

**Advantages**:
- ✅ Simple, HTTP-compatible protocol
- ✅ Automatic reconnection
- ✅ Low latency, real-time updates
- ✅ Single persistent connection

**Stream Events**:
- `started`: Research initiated
- `progress`: Content chunks (streamed Markdown)
- `completed`: Research finished
- `error`: Error occurred

### Markdown Rendering

Full Markdown support with enhancements:
- **Tables**: Native Markdown tables
- **LaTeX Equations**: `$...$` (inline), `$$...$$` (block)
- **Code Blocks**: Syntax highlighting with highlight.js
- **Lists**: Nested lists with proper indentation

### Export to Notion

One-click export with:
- **Native Tables**: Notion Table Blocks (not images)
- **LaTeX Rendering**: Perfect equation rendering
- **Nested Lists**: Correct indentation
- **Images**: Uploaded to ImgBB and embedded

---

## 🔧 Provider Comparison

| Feature | Tavily | Valyu |
|---------|--------|-------|
| **Speed** | Fast | Variable by mode |
| **Pricing** | Pay-per-use | Tiered ($0.10-$15) |
| **Models** | mini, pro, auto | fast, standard, heavy, max |
| **Best For** | General research | Budget control |
| **Streaming** | ✅ Native SSE | ✅ Polling-based |

---

## ⚠️ Troubleshooting

### Common Issues

**1. Missing API Key**
```
Error: TAVILY_API_KEY not set
```
**Solution**: Add to `.env` and restart server

**2. Research Timeout**
```
Error: Research timeout (600s)
```
**Solution**: Try simpler query or upgrade model tier

**3. Export to Notion Fails**
```
Error: NOTION_SECRET not configured
```
**Solution**: Add Notion credentials to `.env`

**4. Streaming Not Working**
```
Browser console: EventSource connection failed
```
**Solution**: Check server logs, ensure `sse-starlette` installed

---

## 📚 Documentation

For more detailed information:

- **[Tavily API Docs](deep_research/tavily/)**: Tavily provider usage guide
- **[Valyu API Docs](deep_research/valyu/)**: Valyu provider usage guide
- **[Streaming Implementation](DEEP_RESEARCH_STREAMING.md)**: Technical details on SSE streaming
- **[Independent Page Design](deep_research/DEEP_RESEARCH_IMPLEMENTATION.md)**: Architecture documentation

---

## 🎯 Best Practices

### Writing Good Research Queries

✅ **Good**:
- "Latest advancements in quantum computing error correction (2024-2025)"
- "Comparison of LoRA vs QLoRA for LLM fine-tuning"
- "Impact of climate change on coral reef ecosystems"

❌ **Too Vague**:
- "Quantum computing"
- "AI"
- "Climate"

### Choosing the Right Model

**Tavily**:
- `mini`: Quick overview, simple topics
- `pro`: Comprehensive analysis, complex topics
- `auto**: Let Tavily decide (recommended)

**Valyu**:
- `fast` ($0.10): Quick facts, simple queries
- `standard` ($0.50): Balanced research (recommended)
- `heavy` ($2.50): Deep analysis, academic topics
- `max` ($15.00): Maximum comprehensiveness

---

## 🔮 Future Enhancements

Planned features:
1. **Research Comparison**: Side-by-side comparison of multiple researches
2. **Research Templates**: Save common research configurations
3. **Batch Research**: Execute multiple researches in parallel
4. **Tagging & Categories**: Organize research history
5. **Full-text Search**: Search within research content
6. **PDF/DOCX Export**: Additional export formats
7. **Research Sharing**: Generate shareable links
8. **CLI Support**: Command-line interface for Deep Research

---

## ✅ Summary

Deep Research provides a complete, AI-powered web research workflow:

- ✅ **Dual Provider Support**: Tavily and Valyu for different needs
- ✅ **Real-time Streaming**: Live progress with SSE technology
- ✅ **Rich Rendering**: Markdown, tables, LaTeX equations
- ✅ **Persistent History**: Independent storage with CRUD operations
- ✅ **Notion Export**: One-click with full formatting
- ✅ **Modern UI**: Dedicated page with glassmorphism design

Whether you're exploring a new research topic, gathering background information, or conducting comprehensive literature reviews, Deep Research provides the tools you need for efficient, AI-powered web research. 🎉
