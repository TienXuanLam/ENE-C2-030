# ENE-C2-030 — Integration Tests: full graph compile + invoke
#
# Requires the `framework`/`shared` packages (agenticstar-agentcore wheel).
# No secrets binding needed — this template declares requires.secrets: []
# (config/agent.yaml) and no code path under test calls ctx.secrets.require().

import pytest
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import HydrogenSupplyChainComplianceDocAgent


@pytest.fixture
def agent():
    a = HydrogenSupplyChainComplianceDocAgent(config={"max_retry": 1, "iso_kb_enabled": False})
    a.compile()
    return a


def _ctx() -> InvocationContext:
    return InvocationContext(
        session_id="integration-test-session",
        caller_trust_level=TrustLevel.VERIFIED_EXTERNAL,
    )


def test_full_pipeline_success(agent):
    result = agent.invoke(
        "Routine periodic inspection completed with no deterministic rule match.",
        ctx=_ctx(),
        input_context={"facility_id": "HYD-STATION-001", "report_type": "incident_report"},
    )

    assert result["status"] == "success"
    assert result["output"] is not None
    assert "InitializeNode" in result["node_history"]
    assert "HydrogenComplianceWorkflowGraphNode" in result["node_history"]
    assert "FinalizeNode" in result["node_history"]
    assert result["output"]["compliance_status"] == "manual_review_required"
    assert "ISO 19880" in result["output"]["regulatory_scope"]["disclaimer"]


def test_full_pipeline_error_on_missing_facility_id(agent):
    result = agent.invoke(
        "A hydrogen leak was detected near dispenser unit 3.",
        ctx=_ctx(),
        input_context={"report_type": "incident_report"},
    )

    assert result["status"] == "error"


def test_full_pipeline_blocks_anonymous_caller(agent):
    anonymous_ctx = InvocationContext(
        session_id="integration-test-session-anon",
        caller_trust_level=TrustLevel.ANONYMOUS,
    )
    result = agent.invoke(
        "A hydrogen leak was detected near dispenser unit 3.",
        ctx=anonymous_ctx,
        input_context={"facility_id": "HYD-STATION-001", "report_type": "incident_report"},
    )

    assert result["status"] == "error"
