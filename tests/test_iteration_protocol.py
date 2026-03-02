"""Unit tests for iterative analysis protocol (iteration_protocol.py)."""

import sys
from pathlib import Path

# Import protocol module only (no llm/openai dependency)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "iteration_protocol",
    Path(__file__).resolve().parent.parent / "agents" / "iteration_protocol.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
InformationRequest = _mod.InformationRequest
IterationState = _mod.IterationState
SpecialistOutput = _mod.SpecialistOutput


def test_iteration_state_can_continue():
    state = IterationState(current_round=0, max_rounds=2, pending_requests=[])
    assert state.can_continue() is False

    state.pending_requests.append(
        InformationRequest("r1", "context_hunter", "section_needed", "Need Appendix")
    )
    assert state.can_continue() is True

    state.current_round = 2
    assert state.can_continue() is False


def test_information_request_defaults():
    req = InformationRequest(
        request_id="id1",
        requester="math_specialist",
        request_type="cross_reference",
        content="Need context report",
        target="context_hunter",
    )
    assert req.priority == "medium"
    assert req.context == {}
    assert req.resolved_content is None


def test_specialist_output_defaults():
    out = SpecialistOutput(agent_name="data_auditor", report="Some report")
    assert out.requests == []
    assert out.confidence == 1.0
    assert out.needs_iteration is False

    out_low = SpecialistOutput(
        agent_name="context_hunter",
        report="Report",
        confidence=0.5,
        needs_iteration=True,
    )
    assert out_low.needs_iteration is True
