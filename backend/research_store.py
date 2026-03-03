"""
Research Store for Deep Research results

Stores and manages completed Deep Research results separately from paper analysis reports.
"""

import json
import asyncio
import aiofiles
import aiofiles.os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


class ResearchStore:
    """Persistent storage for Deep Research results."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._cache: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self._loaded = False
    
    def invalidate_cache(self):
        """Force reload from disk on next access."""
        self._loaded = False

    async def _load(self, force: bool = False):
        """Load database from disk."""
        if self._loaded and not force:
            return
        
        async with self._lock:
            if self._loaded and not force:
                return
            if force:
                self._loaded = False

            if self.db_path.exists():
                try:
                    async with aiofiles.open(self.db_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        self._cache = json.loads(content)
                except Exception as e:
                    print(f"Failed to load research database: {e}")
                    self._cache = {}
            else:
                self._cache = {}
            
            self._loaded = True
    
    async def _save(self):
        """Save database to disk."""
        async with self._lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.db_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self._cache, ensure_ascii=False, indent=2))
    
    async def create_research(
        self,
        title: str,
        query: str,
        content: str,
        sources: List[Dict],
        model: str = "auto",
        citation_format: str = "numbered",
        metadata: Optional[Dict] = None
    ) -> str:
        """Create a new research record."""
        await self._load()
        
        research_id = f"research_{uuid.uuid4().hex[:12]}"
        now = int(datetime.now().timestamp() * 1000)
        
        research = {
            "id": research_id,
            "title": title,
            "query": query,
            "content": content,
            "sources": sources,
            "model": model,
            "citation_format": citation_format,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now
        }
        
        self._cache[research_id] = research
        await self._save()
        
        return research_id
    
    async def get_research(self, research_id: str) -> Optional[Dict]:
        """Get a research record by ID."""
        await self._load()
        return self._cache.get(research_id)
    
    async def list_researches(self, limit: int = 50) -> List[Dict]:
        """List researches, most recent first."""
        await self._load()
        
        researches = list(self._cache.values())
        researches.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        
        # Return summary without full content
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "query": r["query"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "model": r.get("model", "auto"),
                "sources_count": len(r.get("sources", []))
            }
            for r in researches[:limit]
        ]
    
    async def delete_research(self, research_id: str) -> bool:
        """Delete a research record."""
        await self._load()
        
        if research_id not in self._cache:
            return False
        
        del self._cache[research_id]
        await self._save()
        return True
    
    async def update_research(self, research_id: str, **updates) -> bool:
        """Update a research record."""
        await self._load()
        
        if research_id not in self._cache:
            return False
        
        research = self._cache[research_id]
        research.update(updates)
        research["updated_at"] = int(datetime.now().timestamp() * 1000)
        
        await self._save()
        return True
