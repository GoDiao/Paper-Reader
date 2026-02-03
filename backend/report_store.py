"""
Report Store for Paper Reader

JSON-based storage for research history and reports.
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ReportStore:
    """
    Stores research reports and history in a JSON file.
    Thread-safe with async locking.
    """
    
    def __init__(self, store_path: Path = None):
        self.store_path = store_path or Path("data/reports.json")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Dict] = {}
        self._loaded = False
    
    async def _load(self):
        """Load reports from disk."""
        if self._loaded:
            return
        
        async with self._lock:
            if self.store_path.exists():
                try:
                    with open(self.store_path, "r", encoding="utf-8") as f:
                        self._cache = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Corrupted reports.json, starting fresh")
                    self._cache = {}
            self._loaded = True
    
    async def _save(self):
        """Save reports to disk."""
        async with self._lock:
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
    
    async def create_report(
        self,
        title: str,
        pdf_path: str,
        report_en: str = "",
        report_zh: str = "",
        metadata: Dict = None
    ) -> str:
        """Create a new report entry and return its ID."""
        await self._load()
        
        report_id = str(uuid.uuid4())[:8]
        timestamp = int(datetime.now().timestamp() * 1000)
        
        report = {
            "id": report_id,
            "title": title,
            "pdf_path": pdf_path,
            "report_en": report_en,
            "report_zh": report_zh,
            "chat_messages": [],
            "metadata": metadata or {},
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        self._cache[report_id] = report
        await self._save()
        
        logger.info(f"Created report: {report_id} - {title}")
        return report_id
    
    async def update_report(
        self,
        report_id: str,
        report_en: str = None,
        report_zh: str = None,
        metadata: Dict = None
    ) -> bool:
        """Update an existing report."""
        await self._load()
        
        if report_id not in self._cache:
            return False
        
        report = self._cache[report_id]
        
        if report_en is not None:
            report["report_en"] = report_en
        if report_zh is not None:
            report["report_zh"] = report_zh
        if metadata is not None:
            report["metadata"].update(metadata)
        
        report["updated_at"] = int(datetime.now().timestamp() * 1000)
        
        await self._save()
        return True
    
    async def get_report(self, report_id: str) -> Optional[Dict]:
        """Get a report by ID."""
        await self._load()
        return self._cache.get(report_id)
    
    async def list_reports(self, limit: int = 50) -> List[Dict]:
        """List reports, most recent first."""
        await self._load()
        
        reports = list(self._cache.values())
        reports.sort(key=lambda r: r.get("updated_at", 0), reverse=True)
        
        # Return summary without full report content
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "has_en": bool(r.get("report_en")),
                "has_zh": bool(r.get("report_zh")),
                "chat_count": len(r.get("chat_messages", []))
            }
            for r in reports[:limit]
        ]
    
    async def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        await self._load()
        
        if report_id not in self._cache:
            return False
        
        del self._cache[report_id]
        await self._save()
        
        logger.info(f"Deleted report: {report_id}")
        return True
    
    async def add_chat_message(
        self,
        report_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> bool:
        """Add a chat message to a report."""
        await self._load()
        
        if report_id not in self._cache:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "metadata": metadata or {}
        }
        
        self._cache[report_id]["chat_messages"].append(message)
        self._cache[report_id]["updated_at"] = message["timestamp"]
        
        await self._save()
        return True
    
    async def get_chat_messages(self, report_id: str) -> List[Dict]:
        """Get chat messages for a report."""
        await self._load()
        
        report = self._cache.get(report_id)
        if not report:
            return []
        
        return report.get("chat_messages", [])
