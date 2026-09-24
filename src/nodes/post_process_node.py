"""AgentCore Platform v1.0"""

# Real FunctionNode dispatcher for docs/02_design.md "2+4+1 split" post_process slot:
#   step 7 - OutputComposeNode.execute()
# S-1 (required_trust_level), S-3 (_extra_security_gate_output), S-4
# (emit_trace_event) all run here — never inside the pure-Python step helper.

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.services.document_draft_service import AI_DRAFT_DISCLAIMER
from src.services.output_compose_service import OutputComposeNode

# Independent re-check after DocumentationNode's S-3 hook: security-sensitive facility detail must
# never appear in the final package (proposal §2-3 point 3).
_SENSITIVE_DETAIL_MARKERS: tuple[str, ...] = (
    "valve_layout",
    "valve layout",
    "vulnerability",
    "bypass_procedure",
    "bypass procedure",
)


class PostProcessNode(FunctionNode):
    """Step 7: executive summary + final compliance documentation package."""

    # S-1 (CLAUDE.md §3): standard business operation on facility compliance data.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self) -> None:
        self._output_compose = OutputComposeNode()

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        # S-3 domain hook: mandatory-disclaimer re-check (independent of DocumentationNode's
        # hook) + sensitive facility-detail content filter. May raise.
        summary = result.get("executive_summary", "")
        if summary and AI_DRAFT_DISCLAIMER not in summary:
            raise RuntimeError("PostProcessNode S-3: mandatory AI-draft disclaimer missing from executive_summary")

        package_str = json.dumps(result.get("formatted_output", {})).lower()
        for marker in _SENSITIVE_DETAIL_MARKERS:
            if marker in package_str:
                raise RuntimeError(
                    f"PostProcessNode S-3: sensitive facility detail marker '{marker}' " "detected in output — blocked"
                )
        return result

    def execute(self, state: AgentState) -> dict[str, Any]:
        try:
            composed = self._output_compose.execute(
                facility_id=str(state.get("facility_id", "")),
                report_type=str(state.get("report_type", "")),
                compliance_gaps_json=str(state.get("compliance_gaps", "")),
                corrective_action_plan_json=str(state.get("corrective_action_plan", "")),
                incident_report_json=str(state.get("incident_report", "")),
                regulatory_submission_draft_json=str(state.get("regulatory_submission_draft", "")),
                applicable_regulations_json=str(state.get("applicable_regulations", "")),
            )
        except (TypeError, ValueError) as exc:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"PostProcessNode: {exc}"],
            }

        emit_trace_event(
            "compliance_summary_composed",
            {"facility_id": state.get("facility_id", "")},
            state,
        )

        return {
            "executive_summary": composed["executive_summary"],
            "formatted_output": composed["formatted_output"],
            "status": AgentStatus.SUCCESS.value,
        }
