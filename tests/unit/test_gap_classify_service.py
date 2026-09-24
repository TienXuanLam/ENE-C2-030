# ENE-C2-030 — Unit Tests: ComplianceGapAnalyzeNode + IncidentClassifyNode step helpers

import json

from src.services.gap_classify_service import ComplianceGapAnalyzeNode, IncidentClassifyNode


def _regulations_json(with_leak_provision: bool = True) -> str:
    provisions = []
    if with_leak_provision:
        provisions.append(
            {
                "source": "ISO 19880-1",
                "citation": "ISO 19880-1:2020 §6.4",
                "requirement_text": (
                    "Hydrogen fuelling stations shall be equipped with leak "
                    "detection systems capable of triggering an emergency shutdown."
                ),
            }
        )
    return json.dumps({"provisions": provisions})


class TestComplianceGapAnalyzeNode:
    def setup_method(self):
        self.node = ComplianceGapAnalyzeNode()

    def test_leak_incident_flags_high_priority_gap(self):
        incident_data = json.dumps({"raw_text": "A hydrogen leak was detected near the dispenser."})
        result = self.node.execute(incident_data, _regulations_json(with_leak_provision=True))
        assert result["ok"] is True
        gaps = json.loads(result["compliance_gaps"])["gaps"]
        assert any(g["priority"] == "high" and g["deadline_days"] == 14 for g in gaps)

    def test_no_deterministic_match_requires_manual_review(self):
        incident_data = json.dumps({"raw_text": "Routine inspection, no anomalies."})
        result = self.node.execute(incident_data, _regulations_json(with_leak_provision=True))
        gaps = json.loads(result["compliance_gaps"])["gaps"]
        assert len(gaps) == 1
        assert gaps[0]["priority"] == "review_required"

    def test_malformed_json_fails_closed(self):
        import pytest

        with pytest.raises(ValueError):
            self.node.execute("not-json", "not-json-either")


class TestIncidentClassifyNode:
    def setup_method(self):
        self.node = IncidentClassifyNode()

    def test_leak_keyword_classified_as_gas_leak(self):
        incident_data = json.dumps({"raw_text": "A leak was detected at the storage tank."})
        result = self.node.execute(incident_data)
        assert result["incident_type"] == "gas_leak"
        assert result["equipment_category"] == "storage_vessel"

    def test_pressure_keyword_classified_as_overpressure(self):
        incident_data = json.dumps({"raw_text": "Pressure exceeded the safe threshold at the compressor."})
        result = self.node.execute(incident_data)
        assert result["incident_type"] == "overpressure"
        assert result["equipment_category"] == "compression_equipment"

    def test_unrecognized_text_defaults_to_unclassified(self):
        incident_data = json.dumps({"raw_text": "Routine paperwork update."})
        result = self.node.execute(incident_data)
        assert result["incident_type"] == "unclassified"
        assert result["equipment_category"] == "unspecified"
