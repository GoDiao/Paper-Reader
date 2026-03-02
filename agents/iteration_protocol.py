"""
Iterative Analysis Protocol - Data structures for expert information requests.

Experts can request additional information (sections, cross-references, clarification).
The orchestrator processes these requests and feeds resolved content back in the next round.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class InformationRequest:
    """Expert-initiated information request.

    This represents a *formal* request that the orchestrator will try to resolve
    between iterations (e.g. fetch appendix content, cross-reference another
    expert's report, etc.).
    """

    request_id: str
    requester: str  # context_hunter, math_specialist, data_auditor
    request_type: Literal[
        "section_needed",   # need extra section content
        "clarification",    # need clarification of ambiguous content
        "cross_reference",  # need another expert's output
        "figure_detail",    # need figure/table details
    ]
    content: str
    target: Optional[str] = None  # target expert for cross_reference
    priority: Literal["low", "medium", "high"] = "medium"
    context: Dict[str, str] = field(default_factory=dict)
    resolved_content: Optional[str] = None  # filled by orchestrator after processing


@dataclass
class IterationState:
    """Tracks iteration state across rounds."""

    current_round: int = 0
    max_rounds: int = 2
    pending_requests: List[InformationRequest] = field(default_factory=list)
    resolved_requests: List[InformationRequest] = field(default_factory=list)
    request_history: List[Dict] = field(default_factory=list)

    def can_continue(self) -> bool:
        """Whether another iteration round should run."""
        return (
            self.current_round < self.max_rounds
            and len(self.pending_requests) > 0
        )


@dataclass
class TentativeGap:
    """Lightweight gap hint emitted by specialists.

    These are *not* formal requests. They are soft signals that a gap may exist,
    which the Gap Agent can use as additional evidence when doing its review.
    """

    description: str
    severity: Literal["low", "medium", "high"] = "medium"


@dataclass
class SpecialistOutput:
    """Expert output container.

    In the original design, specialists emitted formal InformationRequest objects
    and a confidence score directly. The newer Gap Agent design prefers that
    specialists emit only their report plus optional `TentativeGap` hints, and
    lets the Gap Agent convert those into unified InformationRequest instances
    and global confidence.

    To stay backwards compatible, the old fields (`requests`, `confidence`,
    `needs_iteration`) are kept, but new code should prefer `tentative_gaps`
    and delegate scoring/iteration decisions to the Gap Agent.
    """

    agent_name: str
    report: str
    # New: lightweight gap hints for Gap Agent
    tentative_gaps: List[TentativeGap] = field(default_factory=list)
    # Legacy fields (kept for backward compatibility with old pipeline)
    requests: List[InformationRequest] = field(default_factory=list)
    confidence: float = 1.0
    needs_iteration: bool = False
