"""Checkpoint-safe state for ENE-C2-030."""

from framework.schemas.agent_state import AgentState


class State(AgentState):
    """Flat domain state; structured values are stored as JSON strings."""

    facility_id: str | None
    report_type: str | None
    incident_data: str | None
    sensor_alerts: str | None
    applicable_regulations: str | None
    iso_kb_enabled: bool | None
    compliance_gaps: str | None
    incident_type: str | None
    equipment_category: str | None
    corrective_action_plan: str | None
    incident_report: str | None
    regulatory_submission_draft: str | None
    executive_summary: str | None
