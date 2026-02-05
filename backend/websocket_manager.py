"""
WebSocket Manager for Paper Reader

Handles real-time progress updates during paper analysis.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ProgressPhase(str, Enum):
    """Analysis phases"""
    PARSING = "parsing"
    ANALYSIS = "analysis"
    ASSEMBLY = "assembly"


class ProgressStatus(str, Enum):
    """Progress status"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressEvent:
    """Progress event for WebSocket broadcast"""
    type: str = "progress"
    phase: str = ""
    agent: str = ""
    status: str = ""
    message: str = ""
    progress: int = 0
    data: Dict = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))


class WebSocketManager:
    """Manages WebSocket connections and broadcasts progress events."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # session_id -> websocket
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store a WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    async def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_progress(
        self,
        session_id: str,
        phase: str,  # Changed from ProgressPhase to str
        agent: str,
        status: str,  # Changed from ProgressStatus to str
        message: str,
        progress: int = 0,
        data: Dict = None
    ):
        """Send a progress update to a specific session."""
        event = ProgressEvent(
            type="progress",
            phase=phase,  # Use directly as string
            agent=agent,
            status=status,  # Use directly as string
            message=message,
            progress=progress,
            data=data or {}
        )
        await self._send_to_session(session_id, event.to_json())
    
    async def send_complete(
        self,
        session_id: str,
        upload_id: str,
        reports: Dict[str, str],
        figure_suggestions: Dict,
        metadata: Dict
    ):
        """Send completion event with final reports."""
        event = {
            "type": "complete",
            "upload_id": upload_id,
            "reports": reports,
            "figure_suggestions": figure_suggestions,
            "metadata": metadata
        }
        await self._send_to_session(session_id, json.dumps(event))
    
    async def send_error(self, session_id: str, error: str, details: str = ""):
        """Send error event."""
        event = {
            "type": "error",
            "error": error,
            "details": details
        }
        await self._send_to_session(session_id, json.dumps(event))
    
    async def send_stream(
        self,
        session_id: str,
        agent: str, # agent key
        token: str
    ):
        """Send a stream token to a specific session."""
        event = {
            "type": "stream",
            "agent": agent,
            "token": token
        }
        # Use send_to_session directly for raw JSON speed if needed, 
        # but here we stick to standard structure
        await self._send_to_session(session_id, json.dumps(event))

    async def send_architect_plan(
        self,
        session_id: str,
        plan: Dict[str, Any]
    ):
        """Send architect plan."""
        event = {
            "type": "architect_plan",
            "plan": plan
        }
        await self._send_to_session(session_id, json.dumps(event))

    async def _send_to_session(self, session_id: str, message: str):
        """Send message to a specific session."""
        async with self._lock:
            websocket = self.active_connections.get(session_id)
        
        if websocket:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending to {session_id}: {e}")
                await self.disconnect(session_id)


class ProgressCallback:
    """
    Callback wrapper for the orchestrator to emit WebSocket progress events.
    
    Usage:
        callback = ProgressCallback(ws_manager, session_id, asyncio.get_event_loop())
        orchestrator.analyze_paper(..., progress_callback=callback)
    """
    
    def __init__(self, manager: WebSocketManager, session_id: str, loop: asyncio.AbstractEventLoop = None):
        self.manager = manager
        self.session_id = session_id
        self._loop = loop
    
    def emit(
        self,
        phase: str,
        agent: str,
        status: str,
        message: str,
        progress: int = 0,
        data: Dict = None
    ):
        """Emit progress event (thread-safe wrapper for async send)."""
        if self._loop is None:
            return
        
        # Create coroutine
        coro = self.manager.send_progress(
            self.session_id,
            phase,  # Use as string directly
            agent,
            status,  # Use as string directly
            message,
            progress,
            data
        )
        
        # Schedule on the main event loop (thread-safe)
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception as e:
            logger.warning(f"Failed to emit progress: {e}")

    def stream_token(self, agent: str, token: str):
        """Emit a stream token (thread-safe)."""
        if self._loop is None:
            return

        coro = self.manager.send_stream(self.session_id, agent, token)
        
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception as e:
            # Silent fail for stream to not flood logs
            pass
            
    def report_architect_plan(self, plan: Any):
        """Emit architect plan (thread-safe)."""
        if self._loop is None:
            return
        
        # Convert ReadingPlan object to dict if needed
        plan_dict = asdict(plan) if hasattr(plan, '__dataclass_fields__') else plan
            
        coro = self.manager.send_architect_plan(self.session_id, plan_dict)
        
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception as e:
             logger.warning(f"Failed to emit architect plan: {e}")
    
    def parsing_started(self, message: str = "Starting PDF parsing..."):
        self.emit("parsing", "pdf_parser", "started", message, 0)
    
    def parsing_progress(self, message: str, progress: int):
        self.emit("parsing", "pdf_parser", "in_progress", message, progress)
    
    def parsing_completed(self, message: str = "PDF parsing complete"):
        self.emit("parsing", "pdf_parser", "completed", message, 100)
    
    def architect_started(self):
        self.emit("analysis", "architect", "started", "Creating reading plan...", 0)
    
    def architect_completed(self, domain: str):
        self.emit("analysis", "architect", "completed", f"Reading plan created. Domain: {domain}", 100)
    
    def specialist_started(self, name: str):
        self.emit("analysis", name, "started", f"{name} analyzing...", 0)
    
    def specialist_completed(self, name: str):
        self.emit("analysis", name, "completed", f"{name} completed", 100)
    
    def editor_started(self, lang: str):
        agent = f"editor_{lang}"
        self.emit("assembly", agent, "started", f"Assembling {lang} report...", 0)
    
    def editor_completed(self, lang: str, char_count: int):
        agent = f"editor_{lang}"
        self.emit("assembly", agent, "completed", f"{lang} report: {char_count:,} chars", 100)
