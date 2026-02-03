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
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
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

from parsers.pdf_parser import PDFParser
from agents.hierarchical_orchestrator import HierarchicalOrchestrator
from generators.report_generator import ReportGenerator

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
    verbose: bool
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
        
        # Create progress callback
        callback = ProgressCallback(ws_manager, session_id)
        
        # ===== Phase 1: Parse PDF =====
        await ws_manager.send_progress(
            session_id, "parsing", "pdf_parser", "started",
            "Starting PDF parsing...", 0
        )
        
        parser = PDFParser()
        parsed_doc = parser.parse(pdf_path, images_dir)
        
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
            
            orchestrator = HierarchicalOrchestrator(
                provider=provider,
                model=model,
                verbose=verbose
            )
            
            # Run analysis in thread pool to avoid blocking event loop
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                # Use lambda to call with keyword arguments (executor doesn't support kwargs directly)
                analysis = await loop.run_in_executor(
                    pool,
                    lambda: orchestrator.analyze_paper(
                        content=parsed_doc.markdown_content,
                        title=parsed_doc.title,
                        images=parsed_doc.images,
                        figure_index_path=figure_index_path if figure_index_path.exists() else None
                    )
                )
            
            # Send progress updates for completed phases
            # Architect completed
            await ws_manager.send_progress(
                session_id, "analysis", "architect", "completed",
                f"Domain: {analysis.domain}", 100
            )
            
            # Specialists completed (they ran during analyze_paper)
            await ws_manager.send_progress(
                session_id, "analysis", "context_hunter", "completed",
                "Background analysis complete", 100
            )
            await ws_manager.send_progress(
                session_id, "analysis", "math_specialist", "completed",
                "Mathematical analysis complete", 100
            )
            await ws_manager.send_progress(
                session_id, "analysis", "data_auditor", "completed",
                "Experimental analysis complete", 100
            )
            
            # Editors completed
            await ws_manager.send_progress(
                session_id, "assembly", "editor_english", "completed",
                f"English report: {len(analysis.final_report):,} chars", 100
            )
            await ws_manager.send_progress(
                session_id, "assembly", "editor_chinese", "completed",
                f"Chinese report: {len(analysis.final_report_chinese):,} chars", 100
            )
            
            
            report_en = analysis.final_report
            report_zh = analysis.final_report_chinese
            domain = analysis.domain
            figure_suggestions = analysis.figure_suggestions
            
            # Save specialist reports (always, not just in verbose mode)
            specialists_dir = output_dir / "specialists"
            specialists_dir.mkdir(exist_ok=True)
            
            if analysis.context_report:
                with open(specialists_dir / "01_context_hunter.md", "w", encoding="utf-8") as f:
                    f.write(f"# Context Hunter Report\n\n")
                    f.write(f"**Domain**: {domain}\n\n")
                    f.write(analysis.context_report)
            
            if analysis.math_report:
                with open(specialists_dir / "02_math_specialist.md", "w", encoding="utf-8") as f:
                    f.write(f"# Math Specialist Report\n\n")
                    f.write(analysis.math_report)
            
            if analysis.experiment_report:
                with open(specialists_dir / "03_data_auditor.md", "w", encoding="utf-8") as f:
                    f.write(f"# Data Auditor Report\n\n")
                    f.write(analysis.experiment_report)
            
            logger.info(f"Saved specialist reports to {specialists_dir}")

        else:
            # Simple mode (fallback)
            await ws_manager.send_progress(
                session_id, "analysis", "simple", "started",
                "Running simple analysis...", 0
            )
            
            # Import simple mode function
            from main import run_simple_mode
            # ... (would need adaptation)
            report_en = ""
            report_zh = ""
            domain = ""
            figure_suggestions = {}
        
        # ===== Save Reports =====
        generator = ReportGenerator()
        
        # English report
        report_path_en = output_dir / "paper_analysis.md"
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
                "figure_suggestions": figure_suggestions
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
                "output_dir": str(output_dir)
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
                
                asyncio.create_task(
                    run_analysis(upload_id, session_id, mode, provider, model, verbose)
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
    
    return {
        "id": report["id"],
        "title": report["title"],
        "report": report["report_en"] if lang == "en" else report["report_zh"],
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
    
    # Add user message
    await report_store.add_chat_message(report_id, "user", message)
    
    # Build messages for API
    chat_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    chat_messages.append({"role": "user", "content": message})
    
    # Get AI response
    try:
        chat_agent = ChatAgent()
        report_content = report.get("report_en") or report.get("report_zh", "")
        response, metadata = await chat_agent.chat(report_content, chat_messages)
        
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
