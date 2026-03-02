"""Unit tests for Gap Agent parsing logic.

We do not call the LLM; instead we exercise `_parse_gap_agent_output` directly
with synthetic JSON, to verify that it converts into GapAnalysisResult and
InformationRequest objects correctly.
"""

import sys
from pathlib import Path

import pytest

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from agents.hierarchical_orchestrator import HierarchicalOrchestrator
    from agents.gap_agent import GapAnalysisResult
    _HAS_DEPS = True
except Exception:
    _HAS_DEPS = False


@pytest.mark.skipif(not _HAS_DEPS, reason="agents/llm deps not installed")
def test_parse_gap_agent_output_basic_json():
    orch = HierarchicalOrchestrator(provider="openai", model="gpt-4o-mini")
    json_text = """{
      "assessments": {
        "context_hunter": {
          "completeness": 0.8,
          "coherence": 0.9,
          "gaps_found": ["Missing prior work X"],
          "cross_ref_needs": []
        }
      },
      "unified_requests": [
        {
          "request_type": "section_needed",
          "requester": "math_specialist",
          "content": "Appendix A content for Theorem 3 proof",
          "priority": "high"
        },
        {
          "request_type": "cross_reference",
          "requester": "data_auditor",
          "target": "math_specialist",
          "content": "Equation 5 derivation for loss convergence verification",
          "priority": "medium"
        }
      ],
      "overall_confidence": 0.72,
      "needs_iteration": true,
      "iteration_recommendation": "Missing critical derivations. Recommend one more round."
    }"""

    result = orch._parse_gap_agent_output(json_text)
    assert isinstance(result, GapAnalysisResult)
    assert pytest.approx(result.overall_confidence, rel=1e-6) == 0.72
    assert result.needs_iteration is True
    assert "one more round" in result.iteration_recommendation

    # Assessments
    assert "context_hunter" in result.assessments
    ch = result.assessments["context_hunter"]
    assert pytest.approx(ch.completeness, rel=1e-6) == 0.8
    assert pytest.approx(ch.coherence, rel=1e-6) == 0.9
    assert "Missing prior work X" in ch.gaps_found

    # Unified requests
    assert len(result.unified_requests) == 2
    req0 = result.unified_requests[0]
    assert req0.request_type == "section_needed"
    assert req0.requester == "math_specialist"
    assert "Appendix A" in req0.content
    assert req0.priority == "high"

    req1 = result.unified_requests[1]
    assert req1.request_type == "cross_reference"
    assert req1.requester == "data_auditor"
    assert req1.target == "math_specialist"


@pytest.mark.skipif(not _HAS_DEPS, reason="agents/llm deps not installed")
def test_parse_gap_agent_output_invalid_json():
    """Invalid output should not crash and should indicate no iteration."""
    orch = HierarchicalOrchestrator(provider="openai", model="gpt-4o-mini")
    bad_text = "this is not json at all"

    result = orch._parse_gap_agent_output(bad_text)
    assert isinstance(result, GapAnalysisResult)
    assert result.needs_iteration is False
    assert result.unified_requests == []

