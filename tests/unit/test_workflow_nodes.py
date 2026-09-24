"""Unit tests for the real inner workflow nodes."""

import json

import pytest
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

import src.nodes.documentation_node as documentation_module
from src.nodes.compliance_analysis_node import ComplianceAnalysisNode
from src.nodes.documentation_node import DocumentationNode
from src.services.document_draft_service import AI_DRAFT_DISCLAIMER


def _analysis_state(raw_text: str = "Routine inspection completed.") -> dict:
    return {
        "user_input": json.dumps(
            {
                "facility_id": "HYD-STATION-001",
                "report_type": "incident_report",
                "incident_data": json.dumps({"raw_text": raw_text, "maintenance_records": []}),
                "applicable_regulations": json.dumps(
                    {
                        "provisions": [{"source": "METI", "citation": "Article 8"}],
                        "iso_kb_enabled": False,
                        "disclaimer": "ISO coverage is excluded",
                    }
                ),
            }
        ),
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "hitl_allowed": True,
        "node_history": [],
        "error_log": [],
    }


def _documentation_state(priority: str = "review_required") -> dict:
    state = _analysis_state()
    state.update(
        {
            "compliance_gaps": json.dumps(
                {"gaps": [{"priority": priority, "non_conformance": "review", "deadline_days": None}]}
            ),
            "incident_type": "periodic_inspection_finding",
            "equipment_category": "unspecified",
        }
    )
    return state


def test_analysis_flags_leak_without_iso_kb() -> None:
    result = ComplianceAnalysisNode().execute(_analysis_state("Hydrogen leak at dispenser"))
    assert result["status"] == AgentStatus.SUCCESS.value
    assert json.loads(result["compliance_gaps"])["gaps"][0]["priority"] == "high"


def test_analysis_fails_closed_on_malformed_envelope() -> None:
    result = ComplianceAnalysisNode().execute({"user_input": "not-json"})
    assert result["status"] == AgentStatus.ERROR.value


def test_documentation_generates_disclaimed_documents() -> None:
    result = DocumentationNode().execute(_documentation_state())
    assert result["status"] == AgentStatus.SUCCESS.value
    assert json.loads(result["incident_report"])["disclaimer"] == AI_DRAFT_DISCLAIMER


def test_high_priority_documentation_requests_review(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"value": False}

    def approve(payload: dict) -> str:
        called["value"] = True
        return "approve"

    monkeypatch.setattr(documentation_module, "interrupt", approve)
    result = DocumentationNode().execute(_documentation_state("high"))
    assert called["value"] is True
    assert result["status"] == AgentStatus.SUCCESS.value
    assert "hitl_draft" in result


def test_documentation_gate_rejects_missing_disclaimer() -> None:
    with pytest.raises(RuntimeError, match="disclaimer"):
        DocumentationNode()._extra_security_gate_output({"incident_report": json.dumps({"disclaimer": "wrong"})})
