"""Inner hydrogen compliance analysis and documentation workflow."""

from typing import Any

from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from src.nodes.compliance_analysis_node import ComplianceAnalysisNode
from src.nodes.documentation_node import DocumentationNode
from src.schemas.state import State


class HydrogenComplianceWorkflowGraph(BaseGraph):
    @property
    def name(self) -> str:
        return "hydrogen_compliance_documentation_workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        return None

    def register_nodes(self) -> None:
        self._nodes["compliance_analysis"] = ComplianceAnalysisNode()
        self._nodes["documentation"] = DocumentationNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "compliance_analysis")
        self._sg.add_conditional_edges("compliance_analysis", self.route)
        self._sg.add_edge("documentation", END)

    def route(self, state: AgentState) -> str:
        return END if state.get("status") == AgentStatus.ERROR.value else "documentation"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "output": {
                "compliance_gaps": state.get("compliance_gaps"),
                "incident_type": state.get("incident_type"),
                "equipment_category": state.get("equipment_category"),
                "corrective_action_plan": state.get("corrective_action_plan"),
                "incident_report": state.get("incident_report"),
                "regulatory_submission_draft": state.get("regulatory_submission_draft"),
                "hitl_draft": state.get("hitl_draft"),
            },
            "status": state.get("status", AgentStatus.ERROR.value),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
