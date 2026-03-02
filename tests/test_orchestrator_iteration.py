"""Unit tests for orchestrator iteration (parse specialist output, build context).
   Requires project deps (openai, etc.) to be installed; skip if not.
"""

import sys
from pathlib import Path

import pytest

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from agents.hierarchical_orchestrator import HierarchicalOrchestrator
    from agents.iteration_protocol import InformationRequest, SpecialistOutput
    _HAS_DEPS = True
except Exception:
    _HAS_DEPS = False


@pytest.mark.skipif(not _HAS_DEPS, reason="agents/llm deps not installed")
def test_parse_specialist_output_no_tentative_gaps():
    """When no <TENTATIVE_GAPS> block is present, report should be unchanged and gaps empty."""
    orch = HierarchicalOrchestrator(provider="openai", model="gpt-4o-mini")  # not used for LLM
    raw = "## Report\n\nThis is the analysis.\n"
    out = orch._parse_specialist_output("context_hunter", raw)
    assert isinstance(out, SpecialistOutput)
    assert out.agent_name == "context_hunter"
    assert out.report.strip().startswith("## Report")
    assert "<TENTATIVE_GAPS>" not in out.report
    assert out.tentative_gaps == []


@pytest.mark.skipif(not _HAS_DEPS, reason="agents/llm deps not installed")
def test_parse_specialist_output_with_tentative_gaps():
    """Parse <TENTATIVE_GAPS> into TentativeGap instances and strip block from report."""
    orch = HierarchicalOrchestrator(provider="openai", model="gpt-4o-mini")
    raw = """## Report

Content here.

<TENTATIVE_GAPS>
- [HIGH] Need Appendix A for Theorem 3 proof
- Missing: ablation study on dataset X
</TENTATIVE_GAPS>
"""
    out = orch._parse_specialist_output("data_auditor", raw)
    assert out.agent_name == "data_auditor"
    assert "Content here." in out.report
    assert "<TENTATIVE_GAPS>" not in out.report
    assert len(out.tentative_gaps) == 2
    assert out.tentative_gaps[0].severity == "high"
    assert "Appendix A" in out.tentative_gaps[0].description
    assert out.tentative_gaps[1].severity == "medium"
    assert "ablation study" in out.tentative_gaps[1].description


@pytest.mark.skipif(not _HAS_DEPS, reason="agents/llm deps not installed")
def test_build_iteration_context():
    orch = HierarchicalOrchestrator(provider="openai", model="gpt-4o-mini")
    req = InformationRequest(
        request_id="r1",
        requester="context_hunter",
        request_type="section_needed",
        content="Need Appendix",
    )
    req.resolved_content = "Appendix A content here."
    ctx = orch._build_iteration_context([req], {"context_hunter": "Report A"})
    assert "Additional Information from Previous Iteration" in ctx
    assert "context_hunter" in ctx
    assert "section_needed" in ctx
    assert "Appendix A content here" in ctx
