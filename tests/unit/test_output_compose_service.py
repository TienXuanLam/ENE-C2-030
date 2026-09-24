# ENE-C2-030 — Unit Tests: OutputComposeNode step helper

import json

from src.services.document_draft_service import AI_DRAFT_DISCLAIMER
from src.services.output_compose_service import OutputComposeNode


class TestOutputComposeNode:
    def setup_method(self):
        self.node = OutputComposeNode()

    def test_disclaimer_present_in_executive_summary(self):
        result = self.node.execute(
            facility_id="HYD-STATION-001",
            report_type="incident_report",
            compliance_gaps_json=json.dumps({"gaps": []}),
            corrective_action_plan_json=json.dumps({"tasks": []}),
            incident_report_json=json.dumps({"facility_id": "HYD-STATION-001"}),
            regulatory_submission_draft_json=json.dumps({"facility_id": "HYD-STATION-001"}),
            applicable_regulations_json=json.dumps(
                {"provisions": [], "iso_kb_enabled": False, "disclaimer": "ISO excluded"}
            ),
        )
        assert AI_DRAFT_DISCLAIMER in result["executive_summary"]

    def test_high_priority_gap_marks_non_compliant(self):
        gaps_json = json.dumps({"gaps": [{"priority": "high"}]})
        result = self.node.execute(
            facility_id="HYD-STATION-001",
            report_type="incident_report",
            compliance_gaps_json=gaps_json,
            corrective_action_plan_json=json.dumps({"tasks": [{"task": "fix"}]}),
            incident_report_json=json.dumps({}),
            regulatory_submission_draft_json=json.dumps({}),
            applicable_regulations_json=json.dumps(
                {"provisions": [], "iso_kb_enabled": False, "disclaimer": "ISO excluded"}
            ),
        )
        assert result["formatted_output"]["compliance_status"] == "non_compliant"
        assert len(result["formatted_output"]["corrective_action_plan"]) == 1

    def test_no_high_priority_gap_marks_compliant(self):
        gaps_json = json.dumps({"gaps": [{"priority": "informational"}]})
        result = self.node.execute(
            facility_id="HYD-STATION-001",
            report_type="periodic_inspection",
            compliance_gaps_json=gaps_json,
            corrective_action_plan_json=json.dumps({"tasks": []}),
            incident_report_json=json.dumps({}),
            regulatory_submission_draft_json=json.dumps({}),
            applicable_regulations_json=json.dumps(
                {"provisions": [], "iso_kb_enabled": False, "disclaimer": "ISO excluded"}
            ),
        )
        assert result["formatted_output"]["compliance_status"] == "compliant_no_critical_gaps"

    def test_review_required_does_not_claim_compliance(self):
        result = self.node.execute(
            facility_id="HYD-STATION-001",
            report_type="periodic_inspection",
            compliance_gaps_json=json.dumps({"gaps": [{"priority": "review_required"}]}),
            corrective_action_plan_json=json.dumps({"tasks": []}),
            incident_report_json=json.dumps({}),
            regulatory_submission_draft_json=json.dumps({}),
            applicable_regulations_json=json.dumps(
                {"provisions": [], "iso_kb_enabled": False, "disclaimer": "ISO excluded"}
            ),
        )
        assert result["formatted_output"]["compliance_status"] == "manual_review_required"
        assert result["formatted_output"]["regulatory_scope"]["disclaimer"] == "ISO excluded"
