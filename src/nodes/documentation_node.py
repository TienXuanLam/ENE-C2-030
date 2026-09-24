"""Corrective-action and regulatory-document graph node."""

import json
from typing import Any, ClassVar

from langgraph.types import interrupt

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.document_draft_service import (
    AI_DRAFT_DISCLAIMER,
    ActionPlanDraftNode,
    RegulatorySubmissionFormatNode,
)

_DOCUMENT_FIELDS = ("incident_report", "regulatory_submission_draft")
_CORRECTABLE_FIELDS = frozenset(_DOCUMENT_FIELDS)


class DocumentationNode(FunctionNode):
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self) -> None:
        super().__init__()
        self._action_plan = ActionPlanDraftNode()
        self._submission_format = RegulatorySubmissionFormatNode()

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        for field in _DOCUMENT_FIELDS:
            value = result.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                raise RuntimeError(f"DocumentationNode S-3: '{field}' must be a JSON string")
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"DocumentationNode S-3: '{field}' is not valid JSON") from exc
            if not isinstance(parsed, dict) or parsed.get("disclaimer") != AI_DRAFT_DISCLAIMER:
                raise RuntimeError(f"DocumentationNode S-3: mandatory AI-draft disclaimer missing from '{field}'")
        return result

    def execute(self, state: AgentState) -> dict[str, Any]:
        emit_trace_event("regulatory_documentation_started", {}, state)
        try:
            envelope = json.loads(str(state.get("user_input", "")))
            facility_id = str(envelope["facility_id"])
            compliance_gaps = str(state["compliance_gaps"])
            incident_type = str(state["incident_type"])
            equipment_category = str(state["equipment_category"])
            action_plan = self._action_plan.execute(compliance_gaps)["corrective_action_plan"]
            formatted = self._submission_format.execute(
                facility_id=facility_id,
                incident_type=incident_type,
                equipment_category=equipment_category,
                compliance_gaps_json=compliance_gaps,
                corrective_action_plan_json=action_plan,
            )
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"DocumentationNode: {exc}"],
            }

        draft: dict[str, Any] = {
            "corrective_action_plan": action_plan,
            "incident_report": formatted["incident_report"],
            "regulatory_submission_draft": formatted["regulatory_submission_draft"],
        }
        emit_trace_event("document_generation", {"facility_id": facility_id}, state)

        if state.get("hitl_allowed", True) and self._requires_review(compliance_gaps):
            feedback = interrupt(
                {
                    "prompt": "High-priority compliance gap detected. Review the draft before finalization.",
                    "draft": draft,
                }
            )
            return self._handle_feedback(feedback, draft)
        return {**draft, "status": AgentStatus.SUCCESS.value}

    @staticmethod
    def _requires_review(compliance_gaps_json: str) -> bool:
        gaps_data = json.loads(compliance_gaps_json)
        gaps = gaps_data.get("gaps", [])
        return isinstance(gaps, list) and any(isinstance(gap, dict) and gap.get("priority") == "high" for gap in gaps)

    @staticmethod
    def _handle_feedback(feedback: Any, draft: dict[str, Any]) -> dict[str, Any]:
        if feedback == "approve":
            return {**draft, "hitl_draft": draft, "status": AgentStatus.SUCCESS.value}
        if isinstance(feedback, dict) and isinstance(feedback.get("correction"), dict):
            correction = feedback["correction"]
            unexpected = set(correction) - _CORRECTABLE_FIELDS
            if unexpected or not all(isinstance(value, str) for value in correction.values()):
                return {
                    "hitl_draft": draft,
                    "status": AgentStatus.CANCELLED.value,
                    "error_log": ["DocumentationNode: invalid safety-manager correction shape"],
                }
            return {
                **draft,
                **correction,
                "hitl_draft": draft,
                "status": AgentStatus.SUCCESS.value,
            }
        return {
            "hitl_draft": draft,
            "status": AgentStatus.CANCELLED.value,
            "error_log": ["DocumentationNode: safety manager rejected the regulatory submission draft"],
        }
