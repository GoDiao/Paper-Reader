"""
Research Chat Store for storing chat history per research
"""

import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class ResearchChatStore:
    """Storage for research-specific chat histories."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._cache: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self._loaded = False
    
    async def _load(self):
        """Load chat database from disk."""
        if self._loaded:
            return
        
        async with self._lock:
            if self._loaded:
                return
            
            if self.db_path.exists():
                try:
                    async with aiofiles.open(self.db_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        self._cache = json.loads(content)
                except Exception as e:
                    print(f"Failed to load chat database: {e}")
                    self._cache = {}
            else:
                self._cache = {}
            
            self._loaded = True
    
    async def _save(self):
        """Save chat database to disk."""
        async with self._lock:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.db_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self._cache, ensure_ascii=False, indent=2))
    
    async def get_chat_history(
        self,
        research_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict]:
        """
        Get chat history for a specific research with optional pagination.
        When limit is set, returns the most recent `limit` messages first (offset=0),
        then older messages for offset>0. Messages are in chronological order (oldest first).
        """
        await self._load()
        msgs = self._cache.get(research_id, {}).get("messages", [])
        if limit is None:
            return msgs
        if offset == 0:
            return msgs[-limit:]
        return msgs[-(offset + limit) : -offset]
    
    async def add_message(self, research_id: str, role: str, content: str, timestamp: int) -> bool:
        """Add a message to research chat history."""
        await self._load()
        
        if research_id not in self._cache:
            self._cache[research_id] = {
                "research_id": research_id,
                "messages": [],
                "created_at": int(datetime.now().timestamp() * 1000),
                "updated_at": int(datetime.now().timestamp() * 1000)
            }
        
        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp
        }
        
        self._cache[research_id]["messages"].append(message)
        self._cache[research_id]["updated_at"] = int(datetime.now().timestamp() * 1000)
        
        await self._save()
        return True
    
    async def clear_history(self, research_id: str) -> bool:
        """Clear chat history for a specific research."""
        await self._load()
        
        if research_id in self._cache:
            del self._cache[research_id]
            await self._save()
        
        return True
    
    async def get_message_count(self, research_id: str) -> int:
        """Get number of messages for a research."""
        await self._load()
        return len(self._cache.get(research_id, {}).get("messages", []))
