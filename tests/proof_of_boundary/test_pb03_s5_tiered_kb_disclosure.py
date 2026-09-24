# PB-03: S-5 Tiered KB Source Disclosure Boundary
#
# Verifies proposal §11 Risk #4 Option A: when iso_kb_enabled=False (the
# licensing-gated default), RegulationRetrieveNode must NEVER silently omit
# ISO 19880 coverage — it must emit an explicit disclaimer so the caller knows
# the retrieved regulation set is incomplete. Pure-Python step helper — no
# framework/shared import needed, runs in this sandbox directly.

import json

from src.services.input_regulation_service import RegulationRetrieveNode


class TestPB03TieredKBDisclosure:
    def test_iso_disabled_never_silently_omits_iso_coverage(self):
        node = RegulationRetrieveNode()
        incident_data = json.dumps({"raw_text": "leak detected at dispenser"})

        result = node.execute(incident_data, iso_kb_enabled=False)
        payload = json.loads(result["applicable_regulations"])

        # The boundary contract: disabled ISO KB MUST surface an explicit
        # disclaimer, not just quietly return fewer provisions.
        assert payload["disclaimer"] is not None
        assert "ISO 19880" in payload["disclaimer"]
        assert "ISO-certified consultant" in payload["disclaimer"]

        sources = {p["source"] for p in payload["provisions"]}
        assert "ISO 19880-1" not in sources, (
            "iso_kb_enabled=False must not include ISO 19880 provisions "
            "(unconfirmed commercial licensing — proposal §11 Risk #4)"
        )

    def test_iso_enabled_includes_coverage_with_no_disclaimer(self):
        node = RegulationRetrieveNode()
        incident_data = json.dumps({"raw_text": "leak detected at dispenser"})

        result = node.execute(incident_data, iso_kb_enabled=True)
        payload = json.loads(result["applicable_regulations"])

        assert payload["disclaimer"] is None
        sources = {p["source"] for p in payload["provisions"]}
        assert "ISO 19880-1" in sources

    def test_config_default_matches_licensing_gated_state(self):
        # config/config.yaml must default iso_kb_enabled to False until ISO
        # 19880 commercial-use licensing is confirmed (proposal §12 dependency #2).
        import pathlib

        import yaml

        config_path = pathlib.Path(__file__).parent.parent.parent / "config" / "config.yaml"
        config = yaml.safe_load(config_path.read_text())
        assert config.get("iso_kb_enabled") is False, (
            "config/config.yaml must default iso_kb_enabled=False until ISO 19880 "
            "licensing is confirmed — flipping this without confirming the license "
            "expands unlicensed regulatory content into every response"
        )
