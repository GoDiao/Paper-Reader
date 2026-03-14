"""
FastAPI Web Application for Paper Reader

Main server application with WebSocket support for real-time progress.
"""

import os
import sys
import json
import time
import uuid
import logging
import asyncio
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi import File, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, StreamingResponse, StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.websocket_manager import WebSocketManager, ProgressCallback
from backend.report_store import ReportStore
from backend.research_store import ResearchStore
from backend.research_chat_store import ResearchChatStore
from backend.chat import ChatAgent
from backend.export import write_md_to_pdf, write_md_to_word, create_images_zip
from backend.websocket_manager import ProgressCallback
from backend.config_manager import config_manager

from parsers.pdf_parser import PDFParser
from agents.hierarchical_orchestrator import HierarchicalOrchestrator
from generators.report_generator import ReportGenerator
from config import LLMConfig, WebSearchConfig, AppConfig, PerAgentModelConfig
from services.resource_finder import ResourceFinder
from services.tavily_service import TavilyService, TavilyServiceError
from services.valyu_service import ValyuService, ValyuServiceError
from backend.deep_research_utils import poll_research, validate_provider, build_progress_data
from ImageGo.imagego import rewrite_markdown_images_via_imgbb

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

load_dotenv(BASE_DIR / ".env", override=False)
load_dotenv(BASE_DIR / "md2notion" / ".env", override=False)

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Request/Response models
class AnalysisRequest(BaseModel):
    upload_id: str
    mode: str = "hierarchical"  # "simple" or "hierarchical"
    provider: Optional[str] = None
    model: Optional[str] = None
    verbose: bool = False
    parser: str = "auto"  # "auto", "mineru", "pymupdf"
    language: str = "en"  # "en" or "zh"
    enable_web_search: bool = False
    max_iterations: int = 0  # 0 = off, 1-5 = iterative analysis rounds


class ChatRequest(BaseModel):
    report_id: str
    message: str


class ChatResponse(BaseModel):
    role: str
    content: str
    timestamp: int
    metadata: Optional[Dict] = None


class NotionExportRequest(BaseModel):
    lang: str = "en"
    include_specialists: bool = True


class DeepResearchRequest(BaseModel):
    query: str
    session_id: str
    provider: str = "tavily"  # "tavily" or "valyu"
    model: str = "auto"  # Tavily: mini/pro/auto, Valyu: fast/standard/heavy/max
    citation_format: str = "numbered"  # numbered, mla, apa, chicago


# Global instances
ws_manager = WebSocketManager()
report_store = ReportStore(DATA_DIR / "reports.json")
research_store = ResearchStore(DATA_DIR / "researches.json")
research_chat_store = ResearchChatStore(DATA_DIR / "research_chats.json")
tavily_service = TavilyService()
valyu_service = ValyuService()  # Valyu Deep Research service


def _normalize_research_content(raw: Any) -> str:
    """Normalize research output to string (handles Valyu/Tavily string, dict, or SDK object)."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        out = raw.get("markdown") or raw.get("content") or raw.get("text")
        return out if isinstance(out, str) else json.dumps(raw, ensure_ascii=False, indent=2)
    out = getattr(raw, "markdown", None) or getattr(raw, "content", None) or getattr(raw, "text", None)
    return out if isinstance(out, str) else str(raw)


def _strip_first_h1(markdown: str) -> str:
    if not markdown:
        return markdown
    lines = markdown.splitlines()
    if not lines:
        return markdown
    first = lines[0].strip()
    if first.startswith("#"):
        return "\n".join(lines[1:]).lstrip("\n")
    return markdown


def _load_specialist_reports(report: Dict[str, Any]) -> Dict[str, str]:
    specialist_reports = report.get("specialist_reports", {}) or {}
    if specialist_reports:
        return specialist_reports

    upload_id = report.get("metadata", {}).get("upload_id", report.get("id", ""))
    if not upload_id:
        return specialist_reports
    specialists_dir = OUTPUT_DIR / upload_id / "specialists"
    if not specialists_dir.exists():
        return specialist_reports

    specialist_files = {
        "context_hunter": "01_context_hunter.md",
        "math_specialist": "02_math_specialist.md",
        "data_auditor": "03_data_auditor.md"
    }
    for key, filename in specialist_files.items():
        filepath = specialists_dir / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    specialist_reports[key] = f.read()
            except Exception as e:
                logger.warning(f"Failed to read specialist report {filepath}: {e}")
    return specialist_reports


def _import_md2notionpage():
    try:
        from md2notionpage import md2notionpage
        return md2notionpage
    except ModuleNotFoundError:
        sys.path.insert(0, str(BASE_DIR / "md2notion"))
        from md2notionpage import md2notionpage
        return md2notionpage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Paper Reader API starting...")
    logger.info(f"DATA_DIR: {DATA_DIR}")
    logger.info(f"Research DB path: {research_store.db_path}")
    logger.info(f"Research DB exists: {research_store.db_path.exists()}")
    
    # Pre-load research store to verify data
    try:
        await research_store._load()
        logger.info(f"Research store loaded: {len(research_store._cache)} items")
    except Exception as e:
        logger.error(f"Failed to load research store: {e}")

    # Apply user config overrides (data/user_config.json) over .env
    try:
        overrides = await config_manager._load_user_overrides()
        if overrides:
            for k, v in overrides.items():
                os.environ[k] = v
            logger.info(f"Applied {len(overrides)} user config overrides")
    except Exception as e:
        logger.warning(f"Failed to load user config overrides: {e}")
    
    # Mount static directories
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
    
    # Mount outputs for file downloads
    app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
    
    logger.info("Paper Reader API ready")
    yield
    logger.info("Paper Reader API shutting down")


# Create FastAPI app
app = FastAPI(
    title="Paper Reader API",
    description="API for analyzing academic papers with AI agents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Routes ==============

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main frontend HTML page."""
    index_path = FRONTEND_DIR / "index.html"
    
    if not index_path.exists():
        return HTMLResponse(content="<h1>Frontend not found. Please build the frontend first.</h1>")
    
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/researcher", response_class=HTMLResponse)
async def serve_researcher():
    """Serve the Deep Research frontend page."""
    researcher_path = FRONTEND_DIR / "researcher.html"
    
    if not researcher_path.exists():
        return HTMLResponse(content="<h1>Researcher page not found.</h1>")
    
    with open(researcher_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/config", response_class=HTMLResponse)
async def serve_config():
    """Serve the configuration management page."""
    config_path = FRONTEND_DIR / "config.html"
    
    if not config_path.exists():
        return HTMLResponse(content="<h1>Config page not found.</h1>")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": int(time.time() * 1000)}


# ============== Configuration Management ==============

@app.get("/api/config")
async def get_config():
    """Get current configuration (values masked for secrets)."""
    try:
        config = await config_manager.get_current_config()
        return config
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
async def update_config(request: Request):
    """Update configuration values."""
    try:
        data = await request.json()
        updates = data.get("config", {})
        
        if not isinstance(updates, dict):
            raise HTTPException(status_code=400, detail="Invalid config format")
        
        result = await config_manager.update_config(updates)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============== Upload ==============

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file for analysis.
    Returns an upload_id for subsequent analysis requests.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    # Generate upload ID from filename (sanitized) + timestamp
    import re
    base_name = Path(file.filename).stem  # Remove .pdf extension
    # Sanitize filename: keep only alphanumeric, spaces, hyphens, underscores
    sanitized_name = re.sub(r'[^\w\s-]', '', base_name)
    sanitized_name = re.sub(r'[\s]+', '_', sanitized_name)  # Replace spaces with underscores
    sanitized_name = sanitized_name[:50]  # Limit length
    
    # Add short timestamp to ensure uniqueness
    timestamp = int(time.time())
    upload_id = f"{sanitized_name}_{timestamp}"
    
    # Create upload directory
    upload_path = UPLOAD_DIR / upload_id
    upload_path.mkdir(parents=True, exist_ok=True)
    
    # Calculate SHA256 hash of the file content
    import hashlib
    content = await file.read()
    sha256_hash = hashlib.sha256(content).hexdigest()
    
    # Save the file
    pdf_path = upload_path / file.filename
    with open(pdf_path, "wb") as f:
        f.write(content)
    
    # Store metadata
    metadata = {
        "upload_id": upload_id,
        "filename": file.filename,
        "pdf_path": str(pdf_path),
        "uploaded_at": int(time.time() * 1000),
        "size_bytes": len(content),
        "file_hash": sha256_hash
    }
    
    with open(upload_path / "metadata.json", "w") as f:
        json.dump(metadata, f)
    
    logger.info(f"PDF uploaded: {upload_id} - {file.filename}")
    
    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "size_bytes": len(content)
    }


# ============== Analysis ==============

async def run_analysis(
    upload_id: str,
    session_id: str,
    mode: str,
    provider: Optional[str],
    model: Optional[str],
    verbose: bool,
    parser_type: str = "auto",
    enable_web_search: bool = None,
    language: str = "en",
    max_iterations: int = 0,
):
    """Background task to run paper analysis with WebSocket updates."""
    try:
        # Load upload metadata
        upload_path = UPLOAD_DIR / upload_id
        with open(upload_path / "metadata.json") as f:
            metadata = json.load(f)
        
        pdf_path = Path(metadata["pdf_path"])
        
        # Create output directory
        output_dir = OUTPUT_DIR / upload_id
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Create progress callback for orchestrator (with event loop for thread-safe emits)
        loop = asyncio.get_event_loop()
        progress_callback = ProgressCallback(ws_manager, session_id, loop)
        
        # ===== Phase 1: Parse PDF =====
        await ws_manager.send_progress(
            session_id, "parsing", "pdf_parser", "started",
            f"Starting PDF parsing ({parser_type})...", 0
        )
        
        parser = PDFParser()
        parsed_doc = None
        
        # --- Cache Logic Start ---
        file_hash = metadata.get("file_hash")
        cache_hit = False
        
        if file_hash:
            # Construct cache key: hash + parser_type
            # Note: "auto" resolves to a concrete type at runtime, but for caching we 
            # might just cache under "auto" if it worked, or we'd need to know what auto picked.
            # To be safe, we cache under the requested parser_type. 
            # Ideally, we should cache under the *actual* backend used, but "auto" is a strategy.
            # Let's use the requested parser_type for now as the key.
            cache_dir = DATA_DIR / "parse_cache" / f"{file_hash}_{parser_type}"
            cache_file = cache_dir / "parsed.json"
            
            if cache_file.exists():
                try:
                    logger.info(f"Cache hit for {upload_id} (hash: {file_hash}, parser: {parser_type})")
                    
                    # Load parsed document
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        from parsers.pdf_parser import ParsedDocument
                        parsed_doc = ParsedDocument.from_dict(data)
                    
                    # Skip cache if it has no content (avoid stale empty parses)
                    if not (parsed_doc.markdown_content or parsed_doc.raw_text or "").strip():
                        logger.warning("Cached parse has 0 content; invalidating and re-parsing")
                        parsed_doc = None
                    else:
                        # Copy cached images to current output directory
                        cached_images_dir = cache_dir / "images"
                        if cached_images_dir.exists():
                            for img_file in cached_images_dir.glob("*"):
                                shutil.copy2(img_file, images_dir)
                        
                        # Copy figure index if exists
                        cached_fig_index = cache_dir / "figure_index.json"
                        if cached_fig_index.exists():
                            shutil.copy2(cached_fig_index, output_dir)
                            
                        cache_hit = True
                        logger.info("Successfully restored from cache")
                        
                        await ws_manager.send_progress(
                            session_id, "parsing", "pdf_parser", "completed",
                            f"Parsed (Cached): {parsed_doc.title or 'Untitled'}", 100,
                            {"title": parsed_doc.title, "image_count": len(parsed_doc.images)}
                        )
                    
                except Exception as e:
                    logger.warning(f"Failed to restore from cache: {e}")
                    # Fallback to normal parsing
                    parsed_doc = None
        
        if not parsed_doc:
            # Normal parsing
            parsed_doc = parser.parse(pdf_path, images_dir, parser_backend=parser_type)
            
            # Don't cache empty parses (0 content) - they may be from transient parser issues
            # or scanned PDFs; caching would prevent retrying with different backends
            is_empty = not (parsed_doc.markdown_content or parsed_doc.raw_text or "").strip()
            if is_empty:
                logger.warning("Parse produced 0 characters; not caching. PDF may be scanned or need OCR.")
            
            # Save to cache if we have a hash and parse has content
            if file_hash and not is_empty:
                try:
                    cache_dir = DATA_DIR / "parse_cache" / f"{file_hash}_{parser_type}"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save parsed document
                    with open(cache_dir / "parsed.json", "w", encoding="utf-8") as f:
                        json.dump(parsed_doc.to_dict(), f, ensure_ascii=False, indent=2)
                    
                    # Copy images to cache (files only; skip MinerU subdirs that may be locked)
                    cached_images_dir = cache_dir / "images"
                    cached_images_dir.mkdir(exist_ok=True)
                    if images_dir.exists():
                        for img_file in images_dir.glob("*"):
                            if img_file.is_file():
                                shutil.copy2(img_file, cached_images_dir)
                    
                    # Save figure index to cache (will be generated next)
                    # We'll copy it after generation
                    
                    logger.info(f"Saved parse result to cache: {cache_dir}")
                except Exception as e:
                    logger.warning(f"Failed to save to cache: {e}")
            
            await ws_manager.send_progress(
                session_id, "parsing", "pdf_parser", "completed",
                f"Parsed: {parsed_doc.title or 'Untitled'}", 100,
                {"title": parsed_doc.title, "image_count": len(parsed_doc.images)}
            )
        # --- Cache Logic End ---
        
        # Generate figure index (if not restored from cache)
        # Note: If cache hit, we already copied figure_index.json if it existed.
        # But if it didn't exist in cache or we just parsed, we generate it.
        figure_index_path = output_dir / "figure_index.json"
        if not figure_index_path.exists():
            parser.generate_figure_index(parsed_doc.images, output_dir)
            
            # Update cache with figure index if we just populated the cache
            if file_hash and not cache_hit:
                 try:
                    cache_dir = DATA_DIR / "parse_cache" / f"{file_hash}_{parser_type}"
                    if cache_dir.exists():
                        shutil.copy2(figure_index_path, cache_dir)
                 except Exception as e:
                    logger.warning(f"Failed to update cache with figure index: {e}")
        
        # ===== Phase 2-3: Analyze with Orchestrator =====
        if mode == "hierarchical":
            # Hierarchical mode
            await ws_manager.send_progress(
                session_id, "analysis", "architect", "started",
                "Creating reading plan...", 0
            )

            # Build runtime app config from current env/user overrides,
            # then apply request-level provider/model overrides.
            app_config = AppConfig()
            app_config.per_agent_model = PerAgentModelConfig.from_env()
            env_default_provider = (os.getenv("DEFAULT_LLM_PROVIDER", "") or "").strip()
            env_default_model = (os.getenv("DEFAULT_LLM_MODEL", "") or "").strip()

            effective_provider = provider or env_default_provider or app_config.llm.provider
            effective_model = model or env_default_model or app_config.llm.model

            app_config.llm.provider = effective_provider
            app_config.llm.model = effective_model
            
            # Determine max_workers based on provider to avoid rate limits
            max_workers = 3
            if app_config.llm.provider == "siliconflow":
                max_workers = 1  # Reduce concurrency for Silicon Flow to avoid 429 errors
                
            orchestrator = HierarchicalOrchestrator(
                provider=app_config.llm.provider,
                model=app_config.llm.model,
                temperature=app_config.llm.temperature,
                max_tokens=app_config.llm.get_max_tokens(),
                max_workers=max_workers,
                verbose=verbose,
                per_agent_model=app_config.per_agent_model,
            )
            
            # Run analysis using asyncio.to_thread (no need for separate ThreadPoolExecutor)
            # Orchestrator handles its own internal parallelism
            analysis = await asyncio.to_thread(
                orchestrator.analyze_paper,
                content=parsed_doc.markdown_content,
                title=parsed_doc.title,
                images=parsed_doc.images,
                figure_index_path=figure_index_path if figure_index_path.exists() else None,
                progress_callback=progress_callback,
                language=language,
                max_iterations=max_iterations,
            )
            
            # Note: Progress events are now emitted by orchestrator via progress_callback
            # No need to manually send completed events here - they're handled internally
            
            
            report_en = analysis.final_report
            report_zh = analysis.final_report_chinese
            
            # Explicitly clear unused report based on language to avoid phantom content
            if language == 'en':
                report_zh = ""
            elif language == 'zh':
                report_en = ""
            
            domain = analysis.domain
            figure_suggestions = analysis.figure_suggestions
            
            # Extract P0 features
            variable_tracking = None
            reproduction_checklist = None
            
            if analysis.variable_tracking:
                variable_tracking = {
                    "variables": analysis.variable_tracking.variables,
                    "dependency_graph": analysis.variable_tracking.dependency_graph,
                    "raw_section": analysis.variable_tracking.raw_section
                }
            
            if analysis.reproduction_checklist:
                reproduction_checklist = {
                    "datasets": analysis.reproduction_checklist.datasets,
                    "hyperparameters": analysis.reproduction_checklist.hyperparameters,
                    "hardware": analysis.reproduction_checklist.hardware,
                    "code_availability": analysis.reproduction_checklist.code_availability,
                    "risk_assessment": analysis.reproduction_checklist.risk_assessment,
                    "raw_section": analysis.reproduction_checklist.raw_section
                }
            
            # Web search enrichment for reproduction resources
            # UI toggle overrides env; if not provided, fall back to env
            if enable_web_search is None:
                enable_web_search = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
            web_search_config = WebSearchConfig(
                enable_web_search=bool(enable_web_search)
            )
            
            if web_search_config.is_enabled() and reproduction_checklist:
                try:
                    logger.info("Running web search for reproduction resources...")
                    resource_finder = ResourceFinder(
                        enable_web=True,
                        github_token=web_search_config.get_github_token(),
                        huggingface_token=web_search_config.get_huggingface_token()
                    )
                    
                    # Extract dataset names from checklist
                    dataset_names = [
                        ds.get("dataset", ds.get("name", ""))
                        for ds in reproduction_checklist.get("datasets", [])
                        if ds.get("dataset") or ds.get("name")
                    ]
                    
                    # Enrich checklist with web resources
                    reproduction_checklist = await resource_finder.enrich_checklist(
                        checklist=reproduction_checklist,
                        paper_title=parsed_doc.title or "",
                        authors=""  # Authors extracted from paper if available
                    )
                    
                    logger.info("Web search enrichment completed")
                except Exception as e:
                    logger.warning(f"Web search enrichment failed (non-fatal): {e}")
            
            # Save specialist reports (always, not just in verbose mode)
            specialists_dir = output_dir / "specialists"
            specialists_dir.mkdir(exist_ok=True)
            
            # Prepare specialist reports for storage
            specialist_reports = {}
            
            if analysis.context_report:
                context_content = f"# Context Hunter Report\n\n**Domain**: {domain}\n\n{analysis.context_report}"
                with open(specialists_dir / "01_context_hunter.md", "w", encoding="utf-8") as f:
                    f.write(context_content)
                specialist_reports["context_hunter"] = context_content
            
            if analysis.math_report:
                math_content = f"# Math Specialist Report\n\n{analysis.math_report}"
                with open(specialists_dir / "02_math_specialist.md", "w", encoding="utf-8") as f:
                    f.write(math_content)
                specialist_reports["math_specialist"] = math_content
            
            if analysis.experiment_report:
                data_content = f"# Data Auditor Report\n\n{analysis.experiment_report}"
                with open(specialists_dir / "03_data_auditor.md", "w", encoding="utf-8") as f:
                    f.write(data_content)
                specialist_reports["data_auditor"] = data_content
            
            logger.info(f"Saved specialist reports to {specialists_dir}")

        else:
            # Simple mode (fallback)
            await ws_manager.send_progress(
                session_id, "analysis", "simple", "started",
                "Running simple analysis...", 0
            )
            
            # Import simple mode function
            from main import run_simple_mode
            # Placeholder for simple mode integration
            # For now, simple mode doesn't support language selection well, so we default to English
            # But we should respect the language flag to avoid empty tabs
            
            # Mock result for now as simple mode refactoring is needed
            report_en = "Simple mode analysis not yet fully integrated with web UI."
            report_zh = ""
            
            if language == 'zh':
                report_zh = "简单模式分析尚未完全集成到 Web UI。"
                report_en = ""
            
            domain = "General"
            figure_suggestions = {}
            variable_tracking = None
            reproduction_checklist = None
            specialist_reports = {}
        
        # ===== Save Reports =====
        generator = ReportGenerator()
        
        # English report
        report_path_en = output_dir / "paper_analysis.md"
        final_report_en = ""
        if report_en:
            final_report_en = generator.generate(
                analysis_report=report_en,
                image_map=parsed_doc.image_map,
                title=parsed_doc.title,
                output_path=report_path_en,
                images_output_dir=images_dir
            )
        
        # Chinese report
        report_path_zh = output_dir / "paper_analysis_zh.md"
        final_report_zh = report_zh  # Default to raw if no Chinese report
        if report_zh:
            final_report_zh = generator.generate(
                analysis_report=report_zh,
                image_map=parsed_doc.image_map,
                title=parsed_doc.title,
                output_path=report_path_zh,
                images_output_dir=images_dir
            )
        
        # Save to report store (use the generated reports with embedded images)
        report_id = await report_store.create_report(
            title=parsed_doc.title or "Untitled Paper",
            pdf_path=str(pdf_path),
            report_en=final_report_en,  # Save the generated markdown with images
            report_zh=final_report_zh,  # Save the generated markdown with images
            metadata={
                "upload_id": upload_id,
                "domain": domain,
                "figure_suggestions": figure_suggestions,
                "specialist_reports": specialist_reports,
                "variable_tracking": variable_tracking,
                "reproduction_checklist": reproduction_checklist
            }
        )
        
        # ===== Send Completion =====
        await ws_manager.send_complete(
            session_id,
            upload_id,
            reports={"english": final_report_en, "chinese": final_report_zh},
            figure_suggestions=figure_suggestions,
            metadata={
                "report_id": report_id,
                "title": parsed_doc.title,
                "domain": domain,
                "output_dir": str(output_dir),
                "specialist_reports": specialist_reports,
                "variable_tracking": variable_tracking,
                "reproduction_checklist": reproduction_checklist
            }
        )
        
        logger.info(f"Analysis complete: {upload_id}")
        
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        await ws_manager.send_error(session_id, str(e))


async def run_deep_research(
    query: str,
    session_id: str,
    provider: str = "tavily",
    model: str = "auto",
    citation_format: str = "numbered",
    auto_save: bool = True,
):
    """Background task: create research task (Tavily or Valyu) and poll until complete."""
    provider = validate_provider(provider)
    mode = model if model in ["fast", "standard", "heavy", "max"] else "standard"

    try:
        logger.info(f"Starting research with provider={provider}, model={model}")
        if provider == "valyu":
            service = valyu_service
            await ws_manager.send_deep_research_progress(
                session_id, "started", {"query": query, "provider": "valyu", "mode": mode}
            )
            create_result = await asyncio.to_thread(
                service.create_research_task, query=query, mode=mode
            )
            request_id = create_result.get("deepresearch_id")
        else:
            service = tavily_service
            await ws_manager.send_deep_research_progress(
                session_id, "started", {"query": query, "provider": "tavily", "model": model}
            )
            create_result = await asyncio.to_thread(
                service.create_research_task,
                query=query,
                model=model,
                stream=False,
                citation_format=citation_format,
            )
            if "stream" in create_result:
                raise TavilyServiceError("Streaming mode not supported in this flow")
            request_id = create_result.get("request_id")

        if not request_id:
            raise Exception(f"No request_id returned from {provider}")

        async def on_progress(result: Dict[str, Any]) -> None:
            st = result.get("status", "")
            payload = build_progress_data(st, provider, request_id, result=result)
            await ws_manager.send_deep_research_progress(session_id, st, payload)

        result = await poll_research(
            service, request_id, provider,
            timeout=600.0, interval=3.0, on_progress=on_progress
        )
        status = result.get("status", "")

        if status == "completed":
            content = _normalize_research_content(result.get("output") or result.get("content"))
            sources_raw = result.get("sources", [])
            sources = []
            for s in sources_raw:
                if hasattr(s, "__dict__"):
                    sources.append({
                        "title": getattr(s, "title", ""),
                        "url": getattr(s, "url", ""),
                        "snippet": getattr(s, "snippet", ""),
                        "source": getattr(s, "source", ""),
                    })
                else:
                    sources.append(s)
            research_id = None
            if auto_save:
                try:
                    title = query[:100] + "..." if len(query) > 100 else query
                    research_id = await research_store.create_research(
                        title=title,
                        query=query,
                        content=content,
                        sources=sources,
                        model=model if provider == "tavily" else mode,
                        citation_format=citation_format,
                        metadata={"provider": provider}
                    )
                    logger.info(f"Auto-saved research: {research_id}")
                except Exception as e:
                    logger.warning(f"Failed to auto-save research: {e}")
            await ws_manager.send_deep_research_progress(
                session_id,
                "completed",
                {
                    "request_id": request_id,
                    "content": content,
                    "sources": sources,
                    "research_id": research_id,
                    "provider": provider,
                },
            )
        elif status == "failed":
            error_msg = result.get("error", result.get("detail", "Research failed"))
            await ws_manager.send_deep_research_progress(
                session_id,
                "failed",
                {"request_id": request_id, "message": error_msg, "provider": provider},
            )
    except TimeoutError as e:
        logger.error(f"Deep Research timeout: {e}")
        await ws_manager.send_deep_research_progress(
            session_id, "failed",
            {"message": str(e), "provider": provider, "code": 408, "details": {"hint": "timeout"}}
        )
    except (TavilyServiceError, ValyuServiceError) as e:
        logger.error(f"Deep Research error: {e}")
        data = {"message": str(e), "provider": provider}
        if hasattr(e, "code") and e.code is not None:
            data["code"] = e.code
        if hasattr(e, "details") and e.details:
            data["details"] = e.details
        await ws_manager.send_deep_research_progress(session_id, "failed", data)
    except Exception as e:
        logger.error(f"Deep Research error: {e}", exc_info=True)
        await ws_manager.send_deep_research_progress(
            session_id, "failed", {"message": str(e), "provider": provider}
        )


# ============== Deep Research ==============

class SaveResearchRequest(BaseModel):
    title: str
    query: str
    content: str
    sources: List[Dict[str, Any]]
    model: str = "auto"
    citation_format: str = "numbered"


@app.post("/api/deep-research")
async def start_deep_research(req: DeepResearchRequest):
    """Create a Deep Research task (Tavily or Valyu). Progress is sent via WebSocket."""
    try:
        provider = validate_provider(req.provider)
        asyncio.create_task(
            run_deep_research(
                query=req.query,
                session_id=req.session_id,
                provider=provider,
                model=req.model,
                citation_format=req.citation_format,
                auto_save=True,
            )
        )
        return {"status": "started", "message": "Research task started. Connect to WebSocket for progress."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except (TavilyServiceError, ValyuServiceError) as e:
        status = getattr(e, "code", None) if hasattr(e, "code") else None
        if status is None or status < 400 or status >= 600:
            status = 400
        detail = {"message": str(e)}
        if hasattr(e, "details") and e.details:
            detail["details"] = e.details
        raise HTTPException(status_code=status, detail=detail)


@app.get("/api/deep-research/stream")
async def stream_deep_research(
    query: str,
    provider: str = "tavily",
    model: str = "auto",
    citation_format: str = "numbered",
):
    """
    Stream Deep Research results using Server-Sent Events (SSE).
    Supports both Tavily and Valyu providers.
    """
    from sse_starlette.sse import EventSourceResponse

    async def event_generator():
        try:
            prov = validate_provider(provider)
        except ValueError as e:
            yield {"event": "error", "data": json.dumps({"error": str(e), "provider": provider})}
            return
        mode = model if model in ["fast", "standard", "heavy", "max"] else "standard"
        queue = asyncio.Queue()

        async def run_poll():
            try:
                if prov == "valyu":
                    service = valyu_service
                    create_result = await asyncio.to_thread(
                        service.create_research_task, query=query, mode=mode
                    )
                    request_id = create_result.get("deepresearch_id")
                else:
                    service = tavily_service
                    create_result = await asyncio.to_thread(
                        service.create_research_task,
                        query=query,
                        model=model,
                        stream=False,
                        citation_format=citation_format,
                    )
                    if "stream" in create_result:
                        raise TavilyServiceError("Streaming mode not supported")
                    request_id = create_result.get("request_id")

                if not request_id:
                    raise Exception(f"No request_id from {prov}")

                async def on_progress(result: Dict[str, Any]) -> None:
                    await queue.put(("progress", (request_id, result)))

                final = await poll_research(
                    service, request_id, prov,
                    timeout=600.0, interval=3.0, on_progress=on_progress
                )
                await queue.put(("done", final))
            except TimeoutError as e:
                await queue.put(("error", e))
            except (TavilyServiceError, ValyuServiceError) as e:
                await queue.put(("error", e))
            except Exception as e:
                await queue.put(("error", e))

        try:
            yield {
                "event": "started",
                "data": json.dumps({"query": query, "provider": prov, "model": model})
            }

            asyncio.create_task(run_poll())

            while True:
                kind, data = await queue.get()
                if kind == "progress":
                    req_id, result = data if isinstance(data, tuple) else ("", data)
                    st = result.get("status", "")
                    progress_data = build_progress_data(st, prov, req_id, result=result)
                    if st in ["running", "in_progress"]:
                        msg = progress_data.get("message", "Research in progress...")
                        if progress_data.get("progress"):
                            p = progress_data["progress"]
                            msg = f"Step {p.get('current_step', 0)}/{p.get('total_steps', 1)}"
                        progress_data["message"] = msg
                    yield {"event": "progress", "data": json.dumps(progress_data)}
                elif kind == "done":
                    result = data
                    content = _normalize_research_content(result.get("output") or result.get("content"))
                    sources_raw = result.get("sources", [])
                    sources = []
                    for s in sources_raw:
                        if hasattr(s, "__dict__"):
                            sources.append({
                                "title": getattr(s, "title", ""),
                                "url": getattr(s, "url", ""),
                                "snippet": getattr(s, "snippet", ""),
                                "source": getattr(s, "source", ""),
                            })
                        else:
                            sources.append(s)
                    request_id = result.get("request_id", result.get("deepresearch_id", ""))

                    if content:
                        for i in range(0, len(content), 500):
                            yield {"event": "progress", "data": json.dumps({"content": content[i:i+500]})}
                            await asyncio.sleep(0.05)

                    yield {
                        "event": "completed",
                        "data": json.dumps({
                            "status": "completed",
                            "content": content,
                            "sources": sources,
                            "request_id": request_id,
                            "provider": prov,
                        })
                    }
                    break
                elif kind == "error":
                    e = data
                    if isinstance(e, (TavilyServiceError, ValyuServiceError)):
                        err_data = {"error": str(e), "provider": prov}
                        if hasattr(e, "code") and e.code is not None:
                            err_data["code"] = e.code
                        if hasattr(e, "details") and e.details:
                            err_data["details"] = e.details
                        yield {"event": "error", "data": json.dumps(err_data)}
                    else:
                        yield {"event": "error", "data": json.dumps({"error": str(e), "provider": prov})}
                    break
        except Exception as e:
            logger.error(f"SSE event generator error: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"error": str(e), "provider": prov})}

    return EventSourceResponse(event_generator())


@app.get("/api/deep-research/{request_id}")
async def get_deep_research_status(request_id: str):
    """Get research task status and results (for polling without WebSocket)."""
    try:
        result = await asyncio.to_thread(tavily_service.get_task_status, request_id)
        return result
    except (TavilyServiceError, ValyuServiceError) as e:
        status = getattr(e, "code", None) if hasattr(e, "code") else None
        if status is None or status < 400 or status >= 600:
            status = 400
        detail = {"message": str(e)}
        if hasattr(e, "details") and e.details:
            detail["details"] = e.details
        raise HTTPException(status_code=status, detail=detail)


# ============== Research Save & History ==============

@app.post("/api/research/save")
async def save_research(req: SaveResearchRequest):
    """Save a completed research to the database."""
    try:
        research_id = await research_store.create_research(
            title=req.title,
            query=req.query,
            content=req.content,
            sources=req.sources,
            model=req.model,
            citation_format=req.citation_format
        )
        return {"research_id": research_id, "status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research")
async def list_research(limit: int = 50, refresh: bool = False):
    """List all saved researches. Use ?refresh=1 to force reload from disk."""
    try:
        if refresh:
            await research_store._load(force=True)
        logger.info(f"Listing researches, db_path: {research_store.db_path}")
        logger.info(f"Cache loaded: {research_store._loaded}, cache size: {len(research_store._cache)}")
        
        researches = await research_store.list_researches(limit)
        logger.info(f"Found {len(researches)} researches")
        
        return {"researches": researches}
    except Exception as e:
        logger.error(f"Failed to list researches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research/{research_id}")
async def get_research(research_id: str):
    """Get a specific research by ID."""
    try:
        research = await research_store.get_research(research_id)
        if not research:
            raise HTTPException(status_code=404, detail="Research not found")
        return research
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/research/{research_id}")
async def delete_research(research_id: str):
    """Delete a research."""
    try:
        success = await research_store.delete_research(research_id)
        if not success:
            raise HTTPException(status_code=404, detail="Research not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ResearchChatRequest(BaseModel):
    research_id: str
    message: str


@app.post("/api/research/chat")
async def chat_with_research(request: ResearchChatRequest):
    """Chat with AI about a research report."""
    try:
        # Get research
        research = await research_store.get_research(request.research_id)
        if not research:
            raise HTTPException(status_code=404, detail="Research not found")
        
        # Get research content
        research_content = research.get("content", "")
        if not research_content:
            raise HTTPException(status_code=400, detail="Research content is empty")
        
        # Get chat history
        chat_history = await research_chat_store.get_chat_history(request.research_id)
        
        # Build prompt with research context and chat history
        system_prompt = """You are an AI research assistant. You have read the research report and can answer questions about it.
Your role is to:
1. Explain complex concepts in simple terms
2. Summarize key findings and insights
3. Clarify any confusing points
4. Provide additional context when helpful
5. Be concise but thorough

Always base your answers on the research content provided. If you don't know something, say so."""

        # Build messages with chat history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add last 10 messages from history for context
        for msg in chat_history[-10:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current question
        messages.append({
            "role": "user",
            "content": f"""Research Report Context:
{research_content[:15000]}

Current Question: {request.message}

Please provide a helpful answer based on the research report and our conversation history."""
        })

        # Call LLM using the same pattern as Paper Reader
        from config import LLMConfig
        from llm.client_factory import LLMClientFactory
        
        llm_config = LLMConfig()
        llm_factory = LLMClientFactory(llm_config)
        
        # Use the factory's client to make the chat call
        response = llm_factory.client.chat.completions.create(
            model=llm_config.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        ).choices[0].message.content
        
        # Save user message and assistant response to chat history
        now = int(time.time() * 1000)
        await research_chat_store.add_message(request.research_id, "user", request.message, now)
        await research_chat_store.add_message(request.research_id, "assistant", response, now + 1)
        
        return {
            "response": {
                "role": "assistant",
                "content": response,
                "timestamp": now + 1
            },
            "history_count": await research_chat_store.get_message_count(request.research_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research/{research_id}/chat")
async def get_research_chat_history(
    research_id: str,
    limit: int = 50,
    offset: int = 0,
):
    """Get chat history for a specific research with pagination."""
    try:
        total = await research_chat_store.get_message_count(research_id)
        messages = await research_chat_store.get_chat_history(
            research_id, limit=limit, offset=offset
        )
        return {
            "research_id": research_id,
            "messages": messages,
            "count": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/research/{research_id}/chat")
async def clear_research_chat_history(research_id: str):
    """Clear chat history for a specific research."""
    try:
        success = await research_chat_store.clear_history(research_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/research/{research_id}/export/notion")
async def export_research_to_notion(research_id: str):
    """Export research to Notion."""
    try:
        # Get research
        research = await research_store.get_research(research_id)
        if not research:
            raise HTTPException(status_code=404, detail="Research not found")
        
        # Check required environment variables
        missing = []
        if not os.environ.get("NOTION_SECRET"):
            missing.append("NOTION_SECRET")
        if not os.environ.get("NOTION_PARENT_PAGE_ID"):
            missing.append("NOTION_PARENT_PAGE_ID")
        if not os.environ.get("IMGBB_API_KEY"):
            missing.append("IMGBB_API_KEY")
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing config: {', '.join(missing)}")
        
        # Prepare content
        content = research.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Research content is empty")
        
        # Add sources to content
        sources = research.get("sources", [])
        if sources:
            sources_md = "\n\n## Sources\n\n"
            for i, source in enumerate(sources, 1):
                title = source.get("title", source.get("url", "Untitled"))
                url = source.get("url", "#")
                sources_md += f"{i}. [{title}]({url})\n"
            content += sources_md
        
        # Process images through ImgBB
        from ImageGo.imagego import rewrite_markdown_images_via_imgbb
        md_dir = OUTPUT_DIR  # Use OUTPUT_DIR as base for any relative paths
        cache_path = md_dir / ".imgbb-cache.json"
        expiration_value = os.environ.get("IMGBB_EXPIRATION", "0")
        try:
            expiration = int(expiration_value)
        except Exception:
            expiration = 0
        
        content = rewrite_markdown_images_via_imgbb(
            markdown=content,
            md_dir=md_dir,
            api_key=os.environ.get("IMGBB_API_KEY", ""),
            expiration=expiration,
            cache_path=cache_path
        )
        
        # Export to Notion
        from backend.app import _import_md2notionpage
        md2notionpage = _import_md2notionpage()
        title = (research.get("title") or research_id).strip() or research_id
        notion_url = md2notionpage(
            content,
            title=title,
            parent_page_id=os.environ.get("NOTION_PARENT_PAGE_ID", "")
        )
        
        return {"notion_url": notion_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export research to Notion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time progress updates."""
    await ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "analyze":
                # Start analysis in background
                upload_id = message.get("upload_id")
                mode = message.get("mode", "hierarchical")
                provider = message.get("provider")
                model = message.get("model")
                verbose = message.get("verbose", False)
                parser = message.get("parser", "auto")
                enable_web_search = message.get("enable_web_search")
                language = message.get("language", "en")
                max_iterations = message.get("max_iterations", 0)
                asyncio.create_task(
                    run_analysis(
                        upload_id, session_id, mode, provider, model, verbose,
                        parser, enable_web_search, language, max_iterations,
                    )
                )
            elif message.get("type") == "deep_research":
                query = message.get("query", "").strip()
                provider = message.get("provider", "tavily")
                model = message.get("model", "auto")
                citation_format = message.get("citation_format", "numbered")
                if not query:
                    await ws_manager.send_deep_research_progress(
                        session_id, "failed", {"message": "Query is required"}
                    )
                else:
                    try:
                        provider = validate_provider(provider)
                    except ValueError as e:
                        await ws_manager.send_deep_research_progress(
                            session_id, "failed", {"message": str(e), "provider": provider}
                        )
                    else:
                        asyncio.create_task(
                            run_deep_research(query, session_id, provider, model, citation_format)
                        )
                
    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(session_id)


# ============== Reports ==============

@app.get("/api/reports")
async def list_reports(limit: int = 50):
    """List all reports."""
    reports = await report_store.list_reports(limit)
    return {"reports": reports}


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str, lang: str = "en"):
    """Get a specific report."""
    report = await report_store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get specialist reports from database or fallback to disk
    specialist_reports = report.get("specialist_reports", {})
    
    # Fallback: if no specialist reports in DB, try loading from disk
    if not specialist_reports:
        upload_id = report["metadata"].get("upload_id", report["id"])
        specialists_dir = Path("outputs") / upload_id / "specialists"
        if specialists_dir.exists():
            specialist_files = {
                "context_hunter": "01_context_hunter.md",
                "math_specialist": "02_math_specialist.md",
                "data_auditor": "03_data_auditor.md"
            }
            for key, filename in specialist_files.items():
                filepath = specialists_dir / filename
                if filepath.exists():
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            specialist_reports[key] = f.read()
                    except Exception as e:
                        logger.warning(f"Failed to read specialist report {filepath}: {e}")
    
    return {
        "id": report["id"],
        "title": report["title"],
        "report": report["report_en"] if lang == "en" else report["report_zh"],
        "specialist_reports": specialist_reports,
        "metadata": report["metadata"],
        "upload_id": report["metadata"].get("upload_id", report["id"]),  # Include upload_id for image paths
        "created_at": report["created_at"]
    }


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: str):
    """Delete a report."""
    success = await report_store.delete_report(report_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True}


# ============== Chat ==============

@app.post("/api/reports/{report_id}/chat")
async def chat_with_report(report_id: str, request: Request):
    """Chat with AI about a report."""
    data = await request.json()
    message = data.get("message", "")
    
    # Get report
    report = await report_store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get chat history
    messages = await report_store.get_chat_messages(report_id)
    
    # Handle Context Summarization
    current_summary = report.get("chat_context_summary", "")
    
    # Check if we need to summarize (every 10 messages)
    if len(messages) > 0 and len(messages) % 10 == 0:
        logger.info(f"Summarizing chat history for report {report_id} (messages: {len(messages)})")
        chat_agent = ChatAgent()
        new_summary = await chat_agent.summarize_history(current_summary, messages[-10:])
        
        # Save new summary
        await report_store.update_chat_context(report_id, new_summary)
        current_summary = new_summary
        logger.info(f"Updated context summary length: {len(new_summary)}")

    # Add user message
    await report_store.add_chat_message(report_id, "user", message)
    
    # Build messages for API (include user message)
    chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    chat_messages.append({"role": "user", "content": message})
    
    # Get AI response
    try:
        chat_agent = ChatAgent()
        report_content = report.get("report_en") or report.get("report_zh", "")
        
        response, metadata = await chat_agent.chat(
            report=report_content, 
            messages=chat_messages,
            context_summary=current_summary
        )
        
        # Save assistant response
        await report_store.add_chat_message(report_id, "assistant", response, metadata)
        
        return {
            "response": {
                "role": "assistant",
                "content": response,
                "timestamp": int(time.time() * 1000),
                "metadata": metadata
            }
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/{report_id}/chat/stream")
async def chat_with_report_stream(report_id: str, request: Request):
    """Chat with AI about a report (streaming)."""
    try:
        data = await request.json()
        message = data.get("message", "")
        
        # Get report
        report = await report_store.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get chat history
        messages = await report_store.get_chat_messages(report_id)
        
        # Handle Context Summarization
        current_summary = report.get("chat_context_summary", "")
        
        # Check if we need to summarize (every 10 messages)
        # Note: We create a new ChatAgent instance here just for summarization if needed
        if len(messages) > 0 and len(messages) % 10 == 0:
            logger.info(f"Summarizing chat history for report {report_id} (messages: {len(messages)})")
            # We initialize a temporary agent for summarization
            summarizer_agent = ChatAgent()
            new_summary = await summarizer_agent.summarize_history(current_summary, messages[-10:])
            
            # Save new summary
            await report_store.update_chat_context(report_id, new_summary)
            current_summary = new_summary
            logger.info(f"Updated context summary length: {len(new_summary)}")

        # Add user message
        await report_store.add_chat_message(report_id, "user", message)
        
        # Build messages for API
        chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        chat_messages.append({"role": "user", "content": message})
        
        async def generate():
            chat_agent = ChatAgent()
            report_content = report.get("report_en") or report.get("report_zh", "")
            
            full_response = ""
            full_metadata = {"model": chat_agent.model}
            
            try:
                # chat_stream is a synchronous generator, so we iterate it directly.
                for chunk in chat_agent.chat_stream(
                    report=report_content, 
                    messages=chat_messages,
                    context_summary=current_summary
                ):
                    if chunk:
                        full_response += chunk
                        yield chunk
                        # Small sleep to allow event loop to breathe if needed
                        await asyncio.sleep(0)
                
                # Save assistant response after stream finishes
                await report_store.add_chat_message(report_id, "assistant", full_response, full_metadata)
                
            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                yield f"\n\n[Error: {str(e)}]"

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Chat stream init error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{report_id}/chat")
async def get_chat_history(report_id: str):
    """Get chat history for a report."""
    messages = await report_store.get_chat_messages(report_id)
    return {"messages": messages}


# ============== Export ==============

@app.get("/api/reports/{report_id}/export/{format}")
async def export_report(report_id: str, format: str, lang: str = "en"):
    """Export report in various formats."""
    report = await report_store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    content = report["report_en"] if lang == "en" else report["report_zh"]
    title = report["title"]
    
    # Create export directory
    export_dir = OUTPUT_DIR / "exports"
    export_dir.mkdir(exist_ok=True)
    
    filename = f"{report_id}_{lang}"
    
    if format == "md":
        output_path = export_dir / f"{filename}.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return FileResponse(output_path, filename=f"{title}.md")
    
    elif format == "pdf":
        output_path = export_dir / f"{filename}.pdf"
        result = await write_md_to_pdf(content, output_path, title)
        if result:
            return FileResponse(output_path, filename=f"{title}.pdf")
        raise HTTPException(status_code=500, detail="PDF export failed")
    
    elif format == "docx":
        output_path = export_dir / f"{filename}.docx"
        result = await write_md_to_word(content, output_path, title)
        if result:
            return FileResponse(output_path, filename=f"{title}.docx")
        raise HTTPException(status_code=500, detail="DOCX export failed")
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown format: {format}")


@app.post("/api/reports/{report_id}/export/notion")
async def export_report_to_notion(report_id: str, request: NotionExportRequest):
    report = await report_store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    missing = []
    if not os.environ.get("NOTION_SECRET"):
        missing.append("NOTION_SECRET")
    if not os.environ.get("NOTION_PARENT_PAGE_ID"):
        missing.append("NOTION_PARENT_PAGE_ID")
    if not os.environ.get("IMGBB_API_KEY"):
        missing.append("IMGBB_API_KEY")
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing config: {', '.join(missing)}")

    lang = (request.lang or "en").lower()
    content = report["report_en"] if lang == "en" else report["report_zh"]
    if not content:
        raise HTTPException(status_code=400, detail="Report content is empty")

    combined = content
    if request.include_specialists:
        specialist_reports = _load_specialist_reports(report)
        sections = []
        order = [
            ("context_hunter", "Context Hunter"),
            ("math_specialist", "Math Specialist"),
            ("data_auditor", "Data Auditor")
        ]
        for key, title in order:
            text = specialist_reports.get(key)
            if text:
                cleaned = _strip_first_h1(text).strip()
                if cleaned:
                    sections.append(f"### {title}\n\n{cleaned}")
        if sections:
            combined = f"{combined.rstrip()}\n\n---\n\n## Specialists\n\n" + "\n\n".join(sections)

    upload_id = report.get("metadata", {}).get("upload_id", report_id)
    md_dir = OUTPUT_DIR / upload_id
    cache_path = md_dir / ".imgbb-cache.json"
    expiration_value = os.environ.get("IMGBB_EXPIRATION", "0")
    try:
        expiration = int(expiration_value)
    except Exception:
        expiration = 0

    combined = rewrite_markdown_images_via_imgbb(
        markdown=combined,
        md_dir=md_dir,
        api_key=os.environ.get("IMGBB_API_KEY", ""),
        expiration=expiration,
        cache_path=cache_path
    )

    md2notionpage = _import_md2notionpage()
    title = (report.get("title") or report_id).strip() or report_id
    notion_url = md2notionpage(
        combined,
        title=title,
        parent_page_id=os.environ.get("NOTION_PARENT_PAGE_ID", "")
    )
    return {"notion_url": notion_url}


@app.get("/api/uploads/{upload_id}/images")
async def download_images(upload_id: str):
    """Download all images as a ZIP file."""
    images_dir = OUTPUT_DIR / upload_id / "images"
    
    if not images_dir.exists():
        raise HTTPException(status_code=404, detail="Images not found")
    
    zip_path = OUTPUT_DIR / f"{upload_id}_images.zip"
    result = await create_images_zip(images_dir, zip_path)
    
    if result:
        return FileResponse(zip_path, filename=f"images_{upload_id}.zip")
    
    raise HTTPException(status_code=404, detail="No images to download")


# ============== Entry Point ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
