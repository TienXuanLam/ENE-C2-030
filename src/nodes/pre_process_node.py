"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Read input_context via state.get("input_context", {}) — read-only [C1]
#  - Never import from mediator/, api/, or other agents
#
# Real FunctionNode dispatcher for docs/02_design.md "2+4+1 split" pre_process slot:
#   step 1 - InputParseNode.execute()
#   step 2 - RegulationRetrieveNode.execute()
# S-1 (required_trust_level), S-2 (_extra_security_gate_input), S-4 (emit_trace_event)
# all run here — never inside the pure-Python step helpers.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.services.input_regulation_service import InputParseNode, RegulationRetrieveNode


class PreProcessNode(FunctionNode):
    """Step 1-2: ingest incident data, retrieve applicable regulations."""

    # S-1: standard business operation on facility incident data — requires a
    # verified caller identity, not anonymous access (proposal §5 Security row).
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self, iso_kb_enabled: bool = False) -> None:
        self._input_parse = InputParseNode()
        self._regulation_retrieve = RegulationRetrieveNode()
        self._iso_kb_enabled = iso_kb_enabled

    def _extra_security_gate_input(self, state: AgentState) -> AgentState:
        # Domain check: when input_context IS present, it must carry facility_id.
        # Reject via status=ERROR — never raise (S-2 contract). When
        # input_context is absent entirely (e.g. a generic framework-level
        # invocation with no domain payload), pass through — InputParseNode.execute()
        # still rejects on empty user_input/facility_id (defense in depth); this
        # hook only guards against a domain caller sending a malformed payload.
        input_context = state.get("input_context")
        if input_context is not None and (
            not isinstance(input_context, dict)
            or not isinstance(input_context.get("facility_id"), str)
            or not input_context["facility_id"].strip()
        ):
            state = dict(state)
            state["status"] = AgentStatus.ERROR.value
            state["error_log"] = ["PreProcessNode S-2: input_context.facility_id is required"]
        return state

    def execute(self, state: AgentState) -> dict[str, Any]:
        user_input = state.get("user_input", "")
        input_context = state.get("input_context", {}) or {}

        parsed = self._input_parse.execute(user_input, input_context)
        if not parsed["ok"]:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [parsed["error"]],
            }

        emit_trace_event(
            "incident_data_ingested",
            {"facility_id": parsed["facility_id"], "report_type": parsed["report_type"]},
            state,
        )

        try:
            retrieved = self._regulation_retrieve.execute(parsed["incident_data"], self._iso_kb_enabled)
        except (TypeError, ValueError) as exc:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"PreProcessNode: {exc}"],
            }

        emit_trace_event(
            "regulation_retrieval",
            {"iso_kb_enabled": self._iso_kb_enabled, "facility_id": parsed["facility_id"]},
            state,
        )

        return {
            "facility_id": parsed["facility_id"],
            "report_type": parsed["report_type"],
            "incident_data": parsed["incident_data"],
            "sensor_alerts": parsed["sensor_alerts"],
            "applicable_regulations": retrieved["applicable_regulations"],
            "iso_kb_enabled": self._iso_kb_enabled,
            "status": AgentStatus.SUCCESS.value,
        }
