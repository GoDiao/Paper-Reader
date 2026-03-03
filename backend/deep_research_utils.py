"""
Deep Research shared utilities: polling, provider validation, progress format.
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

VALID_PROVIDERS = frozenset({"tavily", "valyu"})


def validate_provider(provider: str) -> str:
    """Normalize and validate provider. Raises ValueError if invalid."""
    p = (provider or "tavily").lower().strip()
    if p not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider: {provider}. Must be one of: {list(VALID_PROVIDERS)}")
    return p


def build_progress_data(
    status: str,
    provider: str,
    request_id: str,
    result: Optional[Dict[str, Any]] = None,
    **extra,
) -> Dict[str, Any]:
    """Build unified progress payload for WebSocket/SSE."""
    data = {
        "status": status,
        "provider": provider,
        "request_id": request_id,
        **extra,
    }
    if result and result.get("progress"):
        prog = result["progress"]
        data["progress"] = {
            "current_step": prog.get("current_step", 0),
            "total_steps": prog.get("total_steps", 1),
        }
    return data


async def poll_research(
    service: Any,
    request_id: str,
    provider: str,
    timeout: float = 600.0,
    interval: float = 3.0,
    on_progress: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """
    Poll research task until complete or failed.
    Unified logic for WebSocket and SSE flows.
    """
    elapsed = 0.0
    while elapsed < timeout:
        result = await asyncio.to_thread(service.get_task_status, request_id)
        status = result.get("status")

        if status is None:
            if result.get("output") or result.get("content"):
                logger.info("Status is None but output exists, treating as completed")
                status = "completed"
                result = dict(result, status=status)
            else:
                logger.warning("Status is None and no output yet, waiting...")
                await asyncio.sleep(interval)
                elapsed += interval
                continue

        if on_progress:
            await on_progress(result)

        if status in ("completed", "failed"):
            return result

        await asyncio.sleep(interval)
        elapsed += interval

    raise TimeoutError(
        f"Research task {request_id} did not complete within {timeout}s ({provider})"
    )
