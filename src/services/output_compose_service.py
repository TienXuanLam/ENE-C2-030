"""AgentCore Platform v1.0"""

# Step-helper class for the post_process slot (docs/02_design.md "2+4+1 split"):
#   step 7 - OutputComposeNode
#
# Pure-Python business logic only — NOT a BaseNode subclass. Invoked by
# src/nodes/post_process_node.py (the real FunctionNode dispatcher), which
# applies the S-3 domain hook after this helper runs.

from __future__ import annotations

import json
from typing import Any

from src.services.document_draft_service import AI_DRAFT_DISCLAIMER


class OutputComposeNode:
    """Step 7 — executive summary + final compliance documentation package."""

    def execute(
        self,
        facility_id: str,
        report_type: str,
        compliance_gaps_json: str,
        corrective_action_plan_json: str,
        incident_report_json: str,
        regulatory_submission_draft_json: str,
        applicable_regulations_json: str,
    ) -> dict[str, Any]:
        gaps_data = json.loads(compliance_gaps_json)
        action_plan = json.loads(corrective_action_plan_json)
        incident_report = json.loads(incident_report_json)
        submission_draft = json.loads(regulatory_submission_draft_json)
        regulations = json.loads(applicable_regulations_json)
        if not all(
            isinstance(item, dict) for item in (gaps_data, action_plan, incident_report, submission_draft, regulations)
        ):
            raise ValueError("OutputComposeNode: inputs must be JSON objects")

        open_actions = action_plan.get("tasks", [])
        gaps = gaps_data.get("gaps", [])
        provisions = regulations.get("provisions", [])
        if not isinstance(open_actions, list) or not isinstance(gaps, list) or not isinstance(provisions, list):
            raise ValueError("OutputComposeNode: tasks, gaps, and provisions must be lists")
        if not all(isinstance(gap, dict) for gap in gaps):
            raise ValueError("OutputComposeNode: every gap must be an object")
        high_priority = [gap for gap in gaps if gap.get("priority") == "high"]

        review_required = any(isinstance(gap, dict) and gap.get("priority") == "review_required" for gap in gaps)
        if high_priority:
            compliance_status = "non_compliant"
        elif review_required:
            compliance_status = "manual_review_required"
        else:
            compliance_status = "compliant_no_critical_gaps"

        summary_lines = [
            f"Facility: {facility_id}",
            f"Report type: {report_type}",
            f"Compliance status: {compliance_status}",
            f"Open corrective actions: {len(open_actions)}",
            AI_DRAFT_DISCLAIMER,
        ]
        executive_summary = "\n".join(summary_lines)

        package = {
            "facility_id": facility_id,
            "report_type": report_type,
            "compliance_status": compliance_status,
            "executive_summary": executive_summary,
            "incident_report": incident_report,
            "regulatory_submission_draft": submission_draft,
            "corrective_action_plan": open_actions,
            "regulatory_scope": {
                "iso_kb_enabled": bool(regulations.get("iso_kb_enabled", False)),
                "sources": [
                    provision.get("source")
                    for provision in provisions
                    if isinstance(provision, dict) and provision.get("source")
                ],
                "disclaimer": regulations.get("disclaimer"),
            },
        }

        return {
            "ok": True,
            "executive_summary": executive_summary,
            "formatted_output": package,
        }
