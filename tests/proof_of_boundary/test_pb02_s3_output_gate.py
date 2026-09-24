# PB-02: S-3 Output Credential/Content Gate Boundary
#
# Verifies that _extra_security_gate_output() on DocumentationNode and PostProcessNode
# blocks output that is missing the mandatory AI-draft disclaimer (proposal §11
# Risk #5) or that contains a sensitive facility-detail marker (proposal §2-3
# point 3) — content never reaches the caller in either case.
#
# NOTE: Requires `framework`/`shared` (agenticstar-agentcore wheel or ci_stubs/
# on PYTHONPATH). Not resolvable in this sandbox — run on CI for final confirmation.

import json

import pytest

from src.nodes.documentation_node import DocumentationNode
from src.nodes.post_process_node import PostProcessNode
from src.services.document_draft_service import AI_DRAFT_DISCLAIMER


class TestPB02DocumentationNodeDisclaimerGate:
    def test_missing_disclaimer_blocks_output(self):
        node = DocumentationNode()
        with pytest.raises(RuntimeError, match="disclaimer"):
            node._extra_security_gate_output(
                {
                    "incident_report": json.dumps({"disclaimer": "not the required text"}),
                    "regulatory_submission_draft": json.dumps({"disclaimer": AI_DRAFT_DISCLAIMER}),
                }
            )

    def test_present_disclaimer_passes_through(self):
        # incident_report / regulatory_submission_draft are JSON strings with a
        # "disclaimer" key (document_draft_service.py) — the S-3 hook deserializes
        # and strict-compares, it does not substring-match the raw string (F-02).
        node = DocumentationNode()
        payload = {
            "incident_report": json.dumps({"disclaimer": AI_DRAFT_DISCLAIMER}),
            "regulatory_submission_draft": json.dumps({"disclaimer": AI_DRAFT_DISCLAIMER}),
        }
        result = node._extra_security_gate_output(payload)
        assert result == payload

    def test_non_json_field_blocks_output(self):
        node = DocumentationNode()
        with pytest.raises(RuntimeError):
            node._extra_security_gate_output({"incident_report": "not valid json"})


class TestPB02PostProcessNodeContentGate:
    def test_missing_disclaimer_in_summary_blocks_output(self):
        node = PostProcessNode()
        with pytest.raises(RuntimeError, match="disclaimer"):
            node._extra_security_gate_output({"executive_summary": "Status: compliant", "formatted_output": {}})

    def test_sensitive_detail_marker_blocks_output(self):
        node = PostProcessNode()
        with pytest.raises(RuntimeError, match="sensitive facility detail"):
            node._extra_security_gate_output(
                {
                    "executive_summary": AI_DRAFT_DISCLAIMER,
                    "formatted_output": {"equipment_notes": "bypass_procedure documented here"},
                }
            )

    def test_clean_output_passes_through(self):
        node = PostProcessNode()
        payload = {
            "executive_summary": AI_DRAFT_DISCLAIMER,
            "formatted_output": {"equipment_notes": "no sensitive content"},
        }
        result = node._extra_security_gate_output(payload)
        assert result == payload
