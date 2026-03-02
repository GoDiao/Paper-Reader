"""
Gap Agent data structures and helper types.

The Gap Agent reviews specialist reports, identifies information gaps, and
produces a unified list of InformationRequest objects plus high-level
assessments for each specialist.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .iteration_protocol import InformationRequest


@dataclass
class ExpertAssessment:
    """Assessment for a single specialist report.

    This is a qualitative + quantitative view of how good a specialist's
    report is, and what gaps the Gap Agent has found.
    """

    agent_name: str
    completeness: float  # 0.0 - 1.0
    coherence: float  # 0.0 - 1.0
    gaps_found: List[str] = field(default_factory=list)
    cross_ref_needs: List[str] = field(default_factory=list)


@dataclass
class GapAnalysisResult:
    """Unified result produced by the Gap Agent.

    - `assessments` holds per-specialist evaluations.
    - `unified_requests` is the list of normalized InformationRequest objects
      that the orchestrator can feed into the existing request-processing
      pipeline.
    - `overall_confidence` is a global confidence score for the current
      analysis state.
    - `needs_iteration` indicates whether another iteration round is
      recommended.
    - `iteration_recommendation` is a short natural-language explanation
      summarizing why another round is (or is not) needed.
    """

    assessments: Dict[str, ExpertAssessment] = field(default_factory=dict)
    unified_requests: List[InformationRequest] = field(default_factory=list)
    overall_confidence: float = 1.0
    needs_iteration: bool = False
    iteration_recommendation: str = ""

