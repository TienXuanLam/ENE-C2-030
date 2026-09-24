"""PB-7: inner-workflow HITL interrupts must propagate through the node boundary."""

import json

import pytest
from framework.schemas.trust_level import TrustLevel
from langgraph.errors import GraphInterrupt

import src.nodes.documentation_node as documentation_module
from src.nodes.documentation_node import DocumentationNode


def _state(priority: str = "high", **overrides: object) -> dict:
    state = {
        "user_input": json.dumps({"facility_id": "HYD-STATION-001"}),
        "compliance_gaps": json.dumps(
            {"gaps": [{"priority": priority, "non_conformance": "review", "deadline_days": 14}]}
        ),
        "incident_type": "gas_leak",
        "equipment_category": "dispensing_equipment",
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "hitl_allowed": True,
        "node_history": [],
        "error_log": [],
    }
    state.update(overrides)
    return state


def _raise_interrupt(payload: dict) -> str:
    raise GraphInterrupt()


def test_interrupt_propagates_through_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documentation_module, "interrupt", _raise_interrupt)
    with pytest.raises(GraphInterrupt):
        DocumentationNode().execute(_state())


def test_interrupt_propagates_through_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documentation_module, "interrupt", _raise_interrupt)
    with pytest.raises(GraphInterrupt):
        DocumentationNode()(_state())


def test_review_required_priority_does_not_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        documentation_module,
        "interrupt",
        lambda payload: pytest.fail("interrupt must not run"),
    )
    assert DocumentationNode().execute(_state("review_required"))["status"] == "success"


def test_hitl_allowed_false_skips_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        documentation_module,
        "interrupt",
        lambda payload: pytest.fail("interrupt must not run"),
    )
    assert DocumentationNode().execute(_state(hitl_allowed=False))["status"] == "success"


def test_only_hitl_draft_is_written(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documentation_module, "interrupt", lambda payload: "approve")
    result = DocumentationNode().execute(_state())
    assert "hitl_draft" in result
    assert "hitl_status" not in result
    assert "hitl_feedback" not in result


def test_rejection_cancels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documentation_module, "interrupt", lambda payload: "reject")
    assert DocumentationNode().execute(_state())["status"] == "cancelled"
