# ENE-C2-030 — Unit Tests: InputParseNode + RegulationRetrieveNode step helpers
#
# Pure-Python step helpers — no framework/shared import needed.

import json

from src.services.input_regulation_service import InputParseNode, RegulationRetrieveNode


class TestInputParseNode:
    def setup_method(self):
        self.node = InputParseNode()

    def test_success_path(self):
        result = self.node.execute(
            user_input="Pressure sensor detected a leak at dispenser unit 3.",
            input_context={
                "facility_id": "HYD-STATION-001",
                "report_type": "incident_report",
            },
        )
        assert result["ok"] is True
        assert result["facility_id"] == "HYD-STATION-001"
        assert result["report_type"] == "incident_report"
        incident_data = json.loads(result["incident_data"])
        assert "leak" in incident_data["raw_text"].lower()

    def test_missing_facility_id_rejected(self):
        result = self.node.execute(
            user_input="test incident",
            input_context={"report_type": "incident_report"},
        )
        assert result["ok"] is False
        assert "facility_id" in result["error"]

    def test_invalid_report_type_rejected(self):
        result = self.node.execute(
            user_input="test incident",
            input_context={"facility_id": "HYD-STATION-001", "report_type": "not_a_real_type"},
        )
        assert result["ok"] is False
        assert "report_type" in result["error"]

    def test_empty_user_input_rejected(self):
        result = self.node.execute(
            user_input="   ",
            input_context={"facility_id": "HYD-STATION-001", "report_type": "incident_report"},
        )
        assert result["ok"] is False

    def test_optional_sensor_alerts_passthrough(self):
        result = self.node.execute(
            user_input="Routine inspection, no anomalies.",
            input_context={
                "facility_id": "HYD-STATION-002",
                "report_type": "periodic_inspection",
                "sensor_alerts": {"pressure_bar": 12.4, "leak_detected": False},
            },
        )
        assert result["ok"] is True
        alerts = json.loads(result["sensor_alerts"])
        assert alerts["leak_detected"] is False

    def test_sensor_alerts_optional_when_absent(self):
        result = self.node.execute(
            user_input="Routine inspection, no anomalies.",
            input_context={"facility_id": "HYD-STATION-002", "report_type": "periodic_inspection"},
        )
        assert result["ok"] is True
        assert result["sensor_alerts"] is None


class TestRegulationRetrieveNode:
    def setup_method(self):
        self.node = RegulationRetrieveNode()

    def test_iso_kb_disabled_by_default_includes_disclaimer(self):
        incident_data = json.dumps({"raw_text": "leak detected"})
        result = self.node.execute(incident_data, iso_kb_enabled=False)
        assert result["ok"] is True
        payload = json.loads(result["applicable_regulations"])
        assert payload["iso_kb_enabled"] is False
        assert payload["disclaimer"] is not None
        assert "ISO 19880" in payload["disclaimer"]
        sources = {p["source"] for p in payload["provisions"]}
        assert "ISO 19880-1" not in sources

    def test_iso_kb_enabled_includes_iso_provisions_no_disclaimer(self):
        incident_data = json.dumps({"raw_text": "leak detected"})
        result = self.node.execute(incident_data, iso_kb_enabled=True)
        payload = json.loads(result["applicable_regulations"])
        assert payload["iso_kb_enabled"] is True
        assert payload["disclaimer"] is None
        sources = {p["source"] for p in payload["provisions"]}
        assert "ISO 19880-1" in sources

    def test_malformed_incident_data_fails_closed(self):
        import pytest

        with pytest.raises(ValueError):
            self.node.execute("not-json", iso_kb_enabled=False)
