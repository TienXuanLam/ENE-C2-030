"""Compliance-gap and incident-classification graph node."""

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.gap_classify_service import ComplianceGapAnalyzeNode, IncidentClassifyNode


class ComplianceAnalysisNode(FunctionNode):
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def __init__(self) -> None:
        super().__init__()
        self._gap_analyze = ComplianceGapAnalyzeNode()
        self._incident_classify = IncidentClassifyNode()

    def execute(self, state: AgentState) -> dict[str, Any]:
        emit_trace_event("compliance_analysis_started", {}, state)
        try:
            envelope = json.loads(str(state.get("user_input", "")))
            incident_data = str(envelope["incident_data"])
            regulations = str(envelope["applicable_regulations"])
            gap_result = self._gap_analyze.execute(incident_data, regulations)
            classify_result = self._incident_classify.execute(incident_data)
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"ComplianceAnalysisNode: {exc}"],
            }

        emit_trace_event(
            "compliance_gap_analysis",
            {"incident_type": classify_result["incident_type"]},
            state,
        )
        return {
            "compliance_gaps": gap_result["compliance_gaps"],
            "incident_type": classify_result["incident_type"],
            "equipment_category": classify_result["equipment_category"],
            "status": AgentStatus.SUCCESS.value,
        }
