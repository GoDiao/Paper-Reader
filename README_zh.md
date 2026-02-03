# Paper Reader Agent

📚 一个自动化学术论文解读的AI Agent，支持：

- PDF版面分析与LaTeX公式提取
- 结构化分析（背景 → 问题 → 方法 → 实验 → 结论）
- 详细的公式推导
- 自动提取Figure并嵌入报告
- 生成格式严谨的Markdown报告

## 快速开始

### 1. 安装依赖

```bash
cd paper_reader
pip install -r requirements.txt
```

> ⚠️ **注意**: MinerU (magic-pdf) 需要CUDA环境才能发挥最佳性能。如果没有GPU，也可以使用CPU模式（较慢）。

### 2. 配置API密钥

复制环境变量模板并填入你的API密钥：

```bash
cp .env.example .env
# 编辑 .env 文件，填入 DEEPSEEK_API_KEY 或 OPENAI_API_KEY
```

或者设置环境变量：

```bash
# Windows
set DEEPSEEK_API_KEY=your_api_key

# Linux/Mac
export DEEPSEEK_API_KEY=your_api_key
```

### 3. 运行分析

#### 命令行模式

```bash
# 基本用法（使用DeepSeek）
python main.py path/to/paper.pdf

# 指定输出目录
python main.py paper.pdf -o ./my_analysis

# 使用OpenAI
python main.py paper.pdf --provider openai --model gpt-4o

# 详细模式（保存中间结果）
python main.py paper.pdf -v
```

#### 🌐 Web 界面模式 (新!)

```bash
# 启动 Web 服务器
python web_server.py

# 然后访问 http://localhost:8000
```

Web 界面支持：

- 📤 拖拽上传 PDF
- ⚡ 实时显示分析进度 (WebSocket)
- 🌍 中英文双语报告
- 💬 与 AI 讨论论文内容
- 📥 导出 PDF/DOCX/Markdown
- 📚 历史记录管理

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `pdf_path` | PDF文件路径 | (必需) |
| `-o, --output` | 输出目录 | `./output` |
| `--provider` | API提供商 (`openai`/`deepseek`) | `deepseek` |
| `--model` | 模型名称 | 自动选择 |
| `--api-key` | API密钥 | 环境变量 |
| `--no-gpu` | 禁用GPU加速 | False |
| `--no-images` | 跳过图片提取 | False |
| `-v, --verbose` | 详细输出 | False |

## 输出结构

```
output/
├── paper_analysis.md    # 主报告
├── images/              # 提取的图片
│   ├── figure_1.png
│   ├── figure_2.png
│   └── ...
├── parsed/              # 解析中间结果
└── (raw_*.md)           # 原始LLM输出 (verbose模式)
```

## 项目结构

```
paper_reader/
├── main.py              # 主入口
├── config.py            # 配置管理
├── parsers/
│   └── pdf_parser.py    # PDF解析 (MinerU)
├── agents/
│   ├── prompts.py       # Prompt模板
│   └── reasoning_agent.py # LLM推理Agent
├── generators/
│   └── report_generator.py # 报告生成
└── utils/
    └── image_utils.py   # 图片工具
```

## 技术栈

- **PDF解析**: MinerU (magic-pdf) - 学术论文解析SOTA
- **LLM**: DeepSeek / OpenAI API
- **推理策略**: 双角色设计（架构师 + 数学专家）
- **输出格式**: Markdown + LaTeX

## License

MIT
