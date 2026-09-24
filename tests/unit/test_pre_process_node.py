# ENE-C2-030 — Unit Tests: PreProcessNode dispatcher (real FunctionNode boundary)
#
# Requires the `framework`/`shared` packages (agenticstar-agentcore wheel).
# No secrets binding needed — this template declares requires.secrets: []
# (config/agent.yaml) and no code path under test calls ctx.secrets.require().

import pytest
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.pre_process_node import PreProcessNode


def _base_state(**overrides) -> dict:
    state = {
        "user_input": "A hydrogen leak was detected near dispenser unit 3.",
        "input_context": {
            "facility_id": "HYD-STATION-001",
            "report_type": "incident_report",
        },
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
    return PreProcessNode(iso_kb_enabled=False)


class TestPreProcessNodeExecute:
    def test_success_path(self, node):
        result = node.execute(_base_state())
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["facility_id"] == "HYD-STATION-001"
        assert result["report_type"] == "incident_report"
        assert result["iso_kb_enabled"] is False

    def test_missing_facility_id_in_input_context_errors(self, node):
        state = _base_state(input_context={"report_type": "incident_report"})
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value
        assert len(result["error_log"]) > 0


class TestPreProcessNodeTrustGate:
    def test_blocks_anonymous_caller(self, node):
        state = _base_state(caller_trust_level=TrustLevel.ANONYMOUS.value)
        result = node(state)  # __call__ — S-1 boundary
        assert result["status"] == AgentStatus.ERROR.value

    def test_allows_verified_external_caller(self, node):
        state = _base_state()
        result = node(state)
        assert result["status"] == AgentStatus.SUCCESS.value


class TestPreProcessNodeS2Gate:
    def test_extra_gate_rejects_missing_facility_id(self, node):
        state = _base_state(input_context={"report_type": "incident_report"})
        result = node(state)  # goes through _extra_security_gate_input
        assert result["status"] == AgentStatus.ERROR.value
