"""AgentCore Platform v1.0"""

# Step-helper classes for the main slot, part 2 (docs/02_design.md "2+4+1 split"):
#   step 5 - ActionPlanDraftNode
#   step 6 - RegulatorySubmissionFormatNode
#
# Pure-Python business logic only — NOT BaseNode subclasses. Invoked sequentially
# by src/nodes/documentation_node.py (the real FunctionNode), which applies the
# S-3 domain hook (_extra_security_gate_output) on the combined result AFTER these
# helpers run — see documentation_node.py for the disclaimer-presence check
# check (proposal §11 Risk #2, Risk #5).

from __future__ import annotations

import json
from typing import Any

# Mandatory disclaimer — proposal §11 Risk #5. The dispatcher's S-3 hook verifies
# this exact marker is present in incident_report/regulatory_submission_draft
# before output leaves the node boundary; do not alter the wording independently
# of docs/02_design.md and the S-3 hook check.
AI_DRAFT_DISCLAIMER = "This document is an AI-generated draft. Submission without expert review is prohibited."


class ActionPlanDraftNode:
    """Step 5 — corrective action plan (task, owner, deadline) from the gap list."""

    def execute(self, compliance_gaps_json: str) -> dict[str, Any]:
        gaps_data = json.loads(compliance_gaps_json)
        if not isinstance(gaps_data, dict) or not isinstance(gaps_data.get("gaps"), list):
            raise ValueError("ActionPlanDraftNode: compliance_gaps must contain a gaps list")

        gaps = gaps_data.get("gaps", [])
        tasks = []
        for gap in gaps:
            if not isinstance(gap, dict):
                raise ValueError("ActionPlanDraftNode: every gap must be an object")
            if gap.get("priority") == "informational":
                continue
            tasks.append(
                {
                    "task": f"Address non-conformance: {gap.get('non_conformance', '')}",
                    "owner": "facility_safety_manager",
                    "deadline_days": gap.get("deadline_days"),
                    "citation": gap.get("citation"),
                }
            )

        return {"ok": True, "corrective_action_plan": json.dumps({"tasks": tasks}, allow_nan=False)}


class RegulatorySubmissionFormatNode:
    """Step 6 — incident report + regulatory submission draft (statutory fill-in-the-blank).

    Fill-in-the-blank only — no zero-shot generation (proposal §11 Risk #2).
    """

    def execute(
        self,
        facility_id: str,
        incident_type: str,
        equipment_category: str,
        compliance_gaps_json: str,
        corrective_action_plan_json: str,
    ) -> dict[str, Any]:
        gaps_data = json.loads(compliance_gaps_json)
        action_plan = json.loads(corrective_action_plan_json)
        if not isinstance(gaps_data, dict) or not isinstance(gaps_data.get("gaps"), list):
            raise ValueError("RegulatorySubmissionFormatNode: invalid compliance gaps")
        if not isinstance(action_plan, dict) or not isinstance(action_plan.get("tasks"), list):
            raise ValueError("RegulatorySubmissionFormatNode: invalid corrective action plan")

        incident_report = {
            "facility_id": facility_id,
            "incident_type": incident_type,
            "equipment_category": equipment_category,
            "non_conformances": gaps_data.get("gaps", []),
            "disclaimer": AI_DRAFT_DISCLAIMER,
        }

        regulatory_submission_draft = {
            "facility_id": facility_id,
            "form": "METI prescribed incident report form (fill-in-the-blank)",
            "incident_type": incident_type,
            "corrective_actions": action_plan.get("tasks", []),
            "disclaimer": AI_DRAFT_DISCLAIMER,
        }

        return {
            "ok": True,
            "incident_report": json.dumps(incident_report, allow_nan=False),
            "regulatory_submission_draft": json.dumps(regulatory_submission_draft, allow_nan=False),
        }
