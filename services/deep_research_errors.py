"""
Deep Research Service Error Base

Structured error handling for Tavily/Valyu Deep Research APIs with
code and details for fine-grained frontend messaging.
"""

from typing import Optional, Dict, Any


def _extract_http_code(e: Exception) -> Optional[int]:
    """Extract HTTP status code from common exception types."""
    if hasattr(e, "response") and e.response is not None:
        resp = getattr(e, "response")
        if hasattr(resp, "status_code"):
            return int(resp.status_code)
    if hasattr(e, "status_code"):
        try:
            return int(getattr(e, "status_code"))
        except (TypeError, ValueError):
            pass
    if hasattr(e, "code"):
        c = getattr(e, "code")
        if isinstance(c, int):
            return c
        if isinstance(c, str) and c.isdigit():
            return int(c)
    return None


def _extract_details(e: Exception, provider: str) -> Dict[str, Any]:
    """Extract structured details from exception."""
    details: Dict[str, Any] = {"provider": provider}
    if hasattr(e, "response") and e.response is not None:
        resp = getattr(e, "response")
        if hasattr(resp, "json"):
            try:
                body = resp.json()
                if isinstance(body, dict):
                    details["response"] = body
            except Exception:
                pass
        if hasattr(resp, "text") and resp.text:
            details["raw"] = resp.text[:500]
    return details


class DeepResearchServiceError(Exception):
    """
    Base exception for Deep Research API failures.
    Supports code and details for fine-grained frontend handling.
    """

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API response."""
        d: Dict[str, Any] = {"message": self.message}
        if self.code is not None:
            d["code"] = self.code
        if self.details:
            d["details"] = self.details
        return d
