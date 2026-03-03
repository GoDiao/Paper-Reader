"""
Tavily Deep Research Service

Wraps Tavily Research API for comprehensive topic research with
asynchronous task creation, status polling, and result retrieval.
"""

import asyncio
import logging
from typing import Optional, Literal, Dict, Any, List, Callable, Awaitable

from .deep_research_errors import (
    DeepResearchServiceError,
    _extract_http_code,
    _extract_details,
)

logger = logging.getLogger(__name__)

TavilyModel = Literal["mini", "pro", "auto"]
CitationFormat = Literal["numbered", "mla", "apa", "chicago"]


class TavilyServiceError(DeepResearchServiceError):
    """Raised when Tavily API operations fail."""

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details.setdefault("provider", "tavily")
        super().__init__(message=message, code=code, details=details)


class TavilyService:
    """
    Tavily Research API client wrapper.
    
    Supports creating research tasks, querying status, and polling until complete.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Tavily service.

        Args:
            api_key: Tavily API key. If None, reads from TAVILY_API_KEY env var.
        """
        import os
        self._api_key = api_key or os.getenv("TAVILY_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy-load the Tavily client."""
        if self._client is None:
            if not self._api_key:
                raise TavilyServiceError(
                    "TAVILY_API_KEY not set. Add it to .env or pass api_key.",
                    code=401,
                    details={"provider": "tavily", "hint": "missing_api_key"},
                )
            try:
                from tavily import TavilyClient
                self._client = TavilyClient(api_key=self._api_key)
            except ImportError:
                raise TavilyServiceError(
                    "tavily-python not installed. Run: pip install tavily-python",
                    code=500,
                    details={"provider": "tavily", "hint": "missing_package"},
                )
        return self._client

    def create_research_task(
        self,
        query: str,
        model: TavilyModel = "auto",
        stream: bool = False,
        citation_format: CitationFormat = "numbered",
    ) -> Dict[str, Any]:
        """
        Create a Deep Research task.

        Args:
            query: Research topic or question.
            model: Research model - "mini" (fast), "pro" (comprehensive), "auto".
            stream: If True, returns SSE stream. For polling workflow use False.
            citation_format: Citation format for the report.

        Returns:
            Dict with request_id, created_at, status, input, model.
        """
        client = self._get_client()
        try:
            response = client.research(
                input=query,
                model=model,
                stream=stream,
                citation_format=citation_format,
            )
            if stream:
                return {"stream": response, "request_id": None}
            return response
        except TavilyServiceError:
            raise
        except Exception as e:
            logger.error(f"Tavily create research task failed: {e}")
            code = _extract_http_code(e)
            details = _extract_details(e, "tavily")
            raise TavilyServiceError(str(e), code=code, details=details) from e

    def get_task_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get research task status and results.

        Returns:
            Dict with status (pending|in_progress|completed|failed),
            and when completed: content, sources.
        """
        client = self._get_client()
        try:
            result = client.get_research(request_id)
            return result
        except TavilyServiceError:
            raise
        except Exception as e:
            logger.error(f"Tavily get research status failed: {e}")
            code = _extract_http_code(e)
            details = _extract_details(e, "tavily")
            raise TavilyServiceError(str(e), code=code, details=details) from e

    async def poll_until_complete(
        self,
        request_id: str,
        interval: float = 5.0,
        timeout: float = 600.0,
        on_progress: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        """
        Poll until the research task completes or fails.

        Args:
            request_id: Task ID from create_research_task.
            interval: Seconds between polls.
            timeout: Max seconds to wait.
            on_progress: Async callback(status) called on each poll.

        Returns:
            Final result dict with status, content, sources (when completed).
        """
        elapsed = 0.0
        while elapsed < timeout:
            result = await asyncio.to_thread(
                self.get_task_status, request_id
            )
            status = result.get("status", "unknown")
            if on_progress:
                await on_progress(status)
            if status in ("completed", "failed"):
                return result
            await asyncio.sleep(interval)
            elapsed += interval
        raise TavilyServiceError(
            f"Research task {request_id} did not complete within {timeout}s",
            code=408,
            details={"provider": "tavily", "hint": "timeout", "request_id": request_id},
        )
