"""
Valyu Deep Research Service

Wraps Valyu Deep Research API for comprehensive topic research with
asynchronous task creation, status polling, and result retrieval.
"""

import os
import logging
from typing import Optional, Literal, Dict, Any, List

from .deep_research_errors import (
    DeepResearchServiceError,
    _extract_http_code,
    _extract_details,
)

logger = logging.getLogger(__name__)

ValyuMode = Literal["fast", "standard", "heavy", "max"]


class ValyuServiceError(DeepResearchServiceError):
    """Raised when Valyu API operations fail."""

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details.setdefault("provider", "valyu")
        super().__init__(message=message, code=code, details=details)


class ValyuService:
    """
    Valyu Deep Research API client wrapper.
    
    Supports creating research tasks, querying status, and polling until complete.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Valyu service.

        Args:
            api_key: Valyu API key. If None, reads from VALYU_API_KEY env var.
        """
        self._api_key = api_key or os.getenv("VALYU_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy-load the Valyu client."""
        if self._client is None:
            if not self._api_key:
                raise ValyuServiceError(
                    "VALYU_API_KEY not set. Add it to .env or pass api_key.",
                    code=401,
                    details={"provider": "valyu", "hint": "missing_api_key"},
                )
            try:
                from valyu import Valyu
                self._client = Valyu(api_key=self._api_key)
            except ImportError as e:
                logger.error(f"Failed to import Valyu: {e}")
                raise ValyuServiceError(
                    f"valyu not installed. Run: pip install valyu. Error: {e}",
                    code=500,
                    details={"provider": "valyu", "hint": "missing_package"},
                )
        return self._client

    def create_research_task(
        self,
        query: str,
        mode: ValyuMode = "standard",
    ) -> Dict[str, Any]:
        """
        Create a Deep Research task.

        Args:
            query: Research topic or question.
            mode: Research mode - "fast" ($0.10), "standard" ($0.50), 
                  "heavy" ($2.50), "max" ($15.00).

        Returns:
            Dict with deepresearch_id, status, mode, created_at.
        """
        client = self._get_client()
        try:
            # Use the Valyu SDK to create a research task
            response = client.deepresearch.create(
                query=query,
                mode=mode,
            )

            # 支持对象和字典两种返回格式
            def _get(obj, key, default=None):
                if hasattr(obj, key):
                    return getattr(obj, key)
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return default

            success = _get(response, "success", True)
            if success is False:
                err_msg = _get(response, "error") or "Task creation failed"
                logger.error(f"Valyu create research task failed: {err_msg}")
                code = _get(response, "code") or _get(response, "status_code")
                if code is not None and not isinstance(code, int):
                    try:
                        code = int(code)
                    except (TypeError, ValueError):
                        code = 400
                elif code is None:
                    code = 400
                details = {"provider": "valyu", "hint": "api_error"}
                raise ValyuServiceError(str(err_msg), code=code, details=details)

            deepresearch_id = _get(response, "deepresearch_id") or _get(response, "id")
            status = _get(response, "status", "queued")
            created_at = _get(response, "created_at", "")

            if not deepresearch_id:
                logger.error("Valyu create returned no deepresearch_id")
                raise ValyuServiceError(
                    "Valyu API did not return deepresearch_id. "
                    "Check API key, account credits, and Valyu SDK version (pip install -U valyu).",
                    code=402,
                    details={"provider": "valyu", "hint": "insufficient_credits_or_invalid_response"},
                )

            return {
                "deepresearch_id": str(deepresearch_id),
                "status": status,
                "mode": mode,
                "created_at": created_at,
            }
        except ValyuServiceError:
            raise
        except Exception as e:
            logger.error(f"Valyu create research task failed: {e}")
            code = _extract_http_code(e)
            details = _extract_details(e, "valyu")
            raise ValyuServiceError(str(e), code=code, details=details) from e

    def get_task_status(self, deepresearch_id: str) -> Dict[str, Any]:
        """
        Get research task status and results.

        Returns:
            Dict with status (queued/running/completed/failed),
            and when completed: output (content), sources.
        """
        client = self._get_client()
        try:
            result = client.deepresearch.status(deepresearch_id)
            
            response_data = {
                "deepresearch_id": result.deepresearch_id,
                "status": result.status,
                "query": result.query,
                "mode": result.mode,
                "created_at": result.created_at,
            }
            
            # Add optional fields if present
            if hasattr(result, 'output') and result.output is not None:
                response_data["output"] = result.output
            
            if hasattr(result, 'sources') and result.sources is not None:
                response_data["sources"] = result.sources
            
            if hasattr(result, 'completed_at') and result.completed_at is not None:
                response_data["completed_at"] = result.completed_at
            
            if hasattr(result, 'cost'):
                response_data["cost"] = result.cost
            
            if hasattr(result, 'error') and result.error is not None:
                response_data["error"] = result.error
            
            # 提取真实进度（running 时返回）
            if hasattr(result, 'progress') and result.progress is not None:
                progress = result.progress
                response_data["progress"] = {
                    "current_step": getattr(progress, 'current_step', 0),
                    "total_steps": getattr(progress, 'total_steps', 0),
                }
            
            return response_data
        except ValyuServiceError:
            raise
        except Exception as e:
            logger.error(f"Valyu get research status failed: {e}")
            code = _extract_http_code(e)
            details = _extract_details(e, "valyu")
            raise ValyuServiceError(str(e), code=code, details=details) from e
