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
from backend.chat import ChatAgent
from backend.export import write_md_to_pdf, write_md_to_word, create_images_zip
from backend.websocket_manager import ProgressCallback

from parsers.pdf_parser import PDFParser
from agents.hierarchical_orchestrator import HierarchicalOrchestrator
from generators.report_generator import ReportGenerator
from config import LLMConfig, WebSearchConfig
from services.resource_finder import ResourceFinder

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Request/Response models
class AnalysisRequest(BaseModel):
    upload_id: str
    mode: str = "hierarchical"  # "simple" or "hierarchical"
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    verbose: bool = False
    parser: str = "auto"  # "auto", "mineru", "pymupdf"
    language: str = "en"  # "en" or "zh"
    enable_web_search: bool = False


class ChatRequest(BaseModel):
    report_id: str
    message: str


class ChatResponse(BaseModel):
    role: str
    content: str
    timestamp: int
    metadata: Optional[Dict] = None


# Global instances
ws_manager = WebSocketManager()
report_store = ReportStore(DATA_DIR / "reports.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Paper Reader API starting...")
    
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


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": int(time.time() * 1000)}


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
    
    # Save the file
    pdf_path = upload_path / file.filename
    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Store metadata
    metadata = {
        "upload_id": upload_id,
        "filename": file.filename,
        "pdf_path": str(pdf_path),
        "uploaded_at": int(time.time() * 1000),
        "size_bytes": len(content)
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
    provider: str,
    model: str,
    verbose: bool,
    parser_type: str = "auto",
    enable_web_search: bool = None,
    language: str = "en"
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
        parsed_doc = parser.parse(pdf_path, images_dir, parser_backend=parser_type)
        
        await ws_manager.send_progress(
            session_id, "parsing", "pdf_parser", "completed",
            f"Parsed: {parsed_doc.title or 'Untitled'}", 100,
            {"title": parsed_doc.title, "image_count": len(parsed_doc.images)}
        )
        
        # Generate figure index
        parser.generate_figure_index(parsed_doc.images, output_dir)
        figure_index_path = output_dir / "figure_index.json"
        
        # ===== Phase 2-3: Analyze with Orchestrator =====
        if mode == "hierarchical":
            # Hierarchical mode
            await ws_manager.send_progress(
                session_id, "analysis", "architect", "started",
                "Creating reading plan...", 0
            )
            
            # Determine max_workers based on provider to avoid rate limits
            max_workers = 3
            if provider == "siliconflow":
                max_workers = 1  # Reduce concurrency for Silicon Flow to avoid 429 errors
                
            orchestrator = HierarchicalOrchestrator(
                provider=provider,
                model=model,
                max_tokens=LLMConfig(model=model).get_max_tokens(),
                max_workers=max_workers,
                verbose=verbose
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
                language=language
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
                provider = message.get("provider", "deepseek")
                model = message.get("model", "deepseek-chat")
                verbose = message.get("verbose", False)
                parser = message.get("parser", "auto")
                enable_web_search = message.get("enable_web_search")
                language = message.get("language", "en")
                
                asyncio.create_task(
                    run_analysis(upload_id, session_id, mode, provider, model, verbose, parser, enable_web_search, language)
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
