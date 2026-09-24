# ENE-C2-030 — Unit Tests: PostProcessNode dispatcher (real FunctionNode boundary)
#
# Requires the `framework`/`shared` packages (agenticstar-agentcore wheel).
# No secrets binding needed — this template declares requires.secrets: []
# (config/agent.yaml) and no code path under test calls ctx.secrets.require().

import json

import pytest
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.post_process_node import PostProcessNode


def _base_state(**overrides) -> dict:
    state = {
        "facility_id": "HYD-STATION-001",
        "report_type": "incident_report",
        "compliance_gaps": json.dumps({"gaps": [{"priority": "high", "deadline_days": 14}]}),
        "corrective_action_plan": json.dumps({"tasks": [{"task": "verify leak detection"}]}),
        "incident_report": json.dumps({"facility_id": "HYD-STATION-001"}),
        "regulatory_submission_draft": json.dumps({"facility_id": "HYD-STATION-001"}),
        "applicable_regulations": json.dumps(
            {"provisions": [], "iso_kb_enabled": False, "disclaimer": "ISO 19880 excluded"}
        ),
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "",
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "caller_id": "",
        "hitl_allowed": True,
        "node_history": [],
        "error_log": [],
    }
    state.update(overrides)
    return state


@pytest.fixture
def node():
    return PostProcessNode()


class TestPostProcessNodeExecute:
    def test_success_path(self, node):
        result = node.execute(_base_state())
        assert result["status"] == AgentStatus.SUCCESS.value
        assert "AI-generated draft" in result["executive_summary"]
        assert result["formatted_output"]["compliance_status"] == "non_compliant"


class TestPostProcessNodeTrustGate:
    def test_blocks_anonymous_caller(self, node):
        state = _base_state(caller_trust_level=TrustLevel.ANONYMOUS.value)
        result = node(state)  # __call__ — S-1 boundary
        assert result["status"] == AgentStatus.ERROR.value


class TestPostProcessNodeS3Gate:
    def test_extra_gate_raises_when_disclaimer_missing(self, node):
        with pytest.raises(RuntimeError):
            node._extra_security_gate_output({"executive_summary": "no disclaimer here", "formatted_output": {}})

    def test_extra_gate_raises_on_sensitive_detail_marker(self, node):
        with pytest.raises(RuntimeError):
            node._extra_security_gate_output(
                {
                    "executive_summary": (
                        "This document is an AI-generated draft. " "Submission without expert review is prohibited."
                    ),
                    "formatted_output": {"notes": "valve_layout diagram attached"},
                }
            )

    def test_extra_gate_passes_clean_output(self, node):
        result = node._extra_security_gate_output(
            {
                "executive_summary": (
                    "This document is an AI-generated draft. " "Submission without expert review is prohibited."
                ),
                "formatted_output": {"notes": "no sensitive detail"},
            }
        )
        assert "formatted_output" in result
