# ENE-C2-030 — Unit Tests: ActionPlanDraftNode + RegulatorySubmissionFormatNode step helpers

import json

from src.services.document_draft_service import (
    AI_DRAFT_DISCLAIMER,
    ActionPlanDraftNode,
    RegulatorySubmissionFormatNode,
)


class TestActionPlanDraftNode:
    def setup_method(self):
        self.node = ActionPlanDraftNode()

    def test_generates_task_per_non_informational_gap(self):
        gaps_json = json.dumps(
            {
                "gaps": [
                    {
                        "citation": "Art. 8",
                        "non_conformance": "Leak detection unverified",
                        "priority": "high",
                        "deadline_days": 14,
                    },
                    {
                        "citation": None,
                        "non_conformance": "No issue",
                        "priority": "informational",
                        "deadline_days": None,
                    },
                ]
            }
        )
        result = self.node.execute(gaps_json)
        tasks = json.loads(result["corrective_action_plan"])["tasks"]
        assert len(tasks) == 1
        assert tasks[0]["deadline_days"] == 14
        assert tasks[0]["owner"] == "facility_safety_manager"

    def test_no_tasks_when_all_informational(self):
        gaps_json = json.dumps({"gaps": [{"priority": "informational"}]})
        result = self.node.execute(gaps_json)
        tasks = json.loads(result["corrective_action_plan"])["tasks"]
        assert tasks == []


class TestRegulatorySubmissionFormatNode:
    def setup_method(self):
        self.node = RegulatorySubmissionFormatNode()

    def test_disclaimer_present_in_both_documents(self):
        result = self.node.execute(
            facility_id="HYD-STATION-001",
            incident_type="gas_leak",
            equipment_category="storage_vessel",
            compliance_gaps_json=json.dumps({"gaps": []}),
            corrective_action_plan_json=json.dumps({"tasks": []}),
        )
        incident_report = json.loads(result["incident_report"])
        submission_draft = json.loads(result["regulatory_submission_draft"])
        assert incident_report["disclaimer"] == AI_DRAFT_DISCLAIMER
        assert submission_draft["disclaimer"] == AI_DRAFT_DISCLAIMER

    def test_fields_carried_through(self):
        result = self.node.execute(
            facility_id="HYD-STATION-042",
            incident_type="overpressure",
            equipment_category="compression_equipment",
            compliance_gaps_json=json.dumps({"gaps": [{"non_conformance": "x"}]}),
            corrective_action_plan_json=json.dumps({"tasks": [{"task": "fix valve"}]}),
        )
        incident_report = json.loads(result["incident_report"])
        submission_draft = json.loads(result["regulatory_submission_draft"])
        assert incident_report["facility_id"] == "HYD-STATION-042"
        assert incident_report["incident_type"] == "overpressure"
        assert submission_draft["corrective_actions"] == [{"task": "fix valve"}]
