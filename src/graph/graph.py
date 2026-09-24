"""ENE-C2-030 outer Cat 2 graph."""

import json
from typing import TYPE_CHECKING, Any, ClassVar

from framework.errors import ConfigError
from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import State

if TYPE_CHECKING:
    from src.graph.domain_workflow_graph import HydrogenComplianceWorkflowGraph


class HydrogenComplianceWorkflowGraphNode(GraphNode):
    """Secure outer boundary for the multi-node compliance workflow."""

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = True

    def get_subgraph(self) -> "HydrogenComplianceWorkflowGraph":
        from src.graph.domain_workflow_graph import HydrogenComplianceWorkflowGraph

        return HydrogenComplianceWorkflowGraph()

    def extract_input(self, state: AgentState) -> str:
        return json.dumps(
            {
                "facility_id": state.get("facility_id"),
                "report_type": state.get("report_type"),
                "incident_data": state.get("incident_data"),
                "applicable_regulations": state.get("applicable_regulations"),
            }
        )

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        output = sub_result.get("output", {}) or {}
        if not isinstance(output, dict):
            output = {}
        return {**output, "status": sub_result.get("status")}


class HydrogenSupplyChainComplianceDocAgent(AgentBaseGraph):
    """Hydrogen facility safety compliance documentation agent."""

    @property
    def name(self) -> str:
        return "HydrogenSupplyChainComplianceDocAgent"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        super()._validate_config()
        iso_enabled = self.config.get("iso_kb_enabled", False)
        if not isinstance(iso_enabled, bool):
            raise ConfigError("iso_kb_enabled must be a boolean")

    def register_nodes(self) -> None:
        super().register_nodes()
        self._nodes["pre_process"] = PreProcessNode(iso_kb_enabled=bool(self.config.get("iso_kb_enabled", False)))
        self._nodes["main"] = HydrogenComplianceWorkflowGraphNode()
        self._nodes["post_process"] = PostProcessNode()
