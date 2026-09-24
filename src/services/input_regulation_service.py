"""AgentCore Platform v1.0"""

# Step-helper classes for the pre_process slot (docs/02_design.md "2+4+1 split"):
#   step 1 - InputParseNode
#   step 2 - RegulationRetrieveNode
#
# Pure-Python business logic only — NOT BaseNode subclasses. S-1/S-2/S-4 run
# exclusively inside src/nodes/pre_process_node.py (the real FunctionNode
# dispatcher) via BaseNode.__call__(). These classes are plain helpers invoked
# sequentially by that dispatcher's execute().

from __future__ import annotations

import json
import re
from typing import Any

_FACILITY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
_VALID_REPORT_TYPES = {
    "incident_report",
    "periodic_inspection",
    "corrective_action_confirmation",
}
_MAX_INPUT_BYTES = 1024 * 1024
_MAX_CONTEXT_BYTES = 256 * 1024
_MAX_RECORDS = 1000
_ALLOWED_CONTEXT_FIELDS = {
    "facility_id",
    "report_type",
    "sensor_alerts",
    "maintenance_records",
}

# Initial public regulation KB — proposal §11 Risk #4 Option A (tiered KB).
# Real deployments populate this from the actual indexed KB corpus (see
# docs/07_operation_guide.md "Knowledge Base Setup"); this in-repo fallback
# keeps the template runnable without external KB wiring.
_METI_KB: list[dict[str, str]] = [
    {
        "source": "高圧ガス保安法",
        "article": "第八条",
        "citation": "高圧ガス保安法 第八条（技術上の基準）",
        "requirement_text": (
            "高圧ガスの製造、貯蔵、販売、移動その他の取扱及び消費並びに容器の"
            "製造及び取扱は、経済産業省令で定める技術上の基準に従ってしなければならない。"
        ),
    },
    {
        "source": "METI Hydrogen Station Safety Standards",
        "article": "§3.2",
        "citation": "METI Hydrogen Station Safety Standards (2023 edition) §3.2",
        "requirement_text": (
            "Pressure relief devices at hydrogen dispensing facilities must be "
            "inspected and function-tested at the interval prescribed by the "
            "facility's safety management plan."
        ),
    },
]

_ISO_KB: list[dict[str, str]] = [
    {
        "source": "ISO 19880-1",
        "article": "§6.4",
        "citation": "ISO 19880-1:2020 §6.4",
        "requirement_text": (
            "Hydrogen fuelling stations shall be equipped with leak detection "
            "systems capable of triggering an emergency shutdown."
        ),
    },
]


class InputParseNode:
    """Step 1 — ingest and normalize incident logs, sensor alerts, maintenance records."""

    def execute(
        self,
        user_input: str,
        input_context: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(input_context, dict):
            return {"ok": False, "error": "InputParseNode: input_context must be an object"}
        extra = set(input_context) - _ALLOWED_CONTEXT_FIELDS
        if extra:
            return {"ok": False, "error": f"InputParseNode: unsupported input_context fields: {sorted(extra)}"}
        try:
            context_bytes = len(json.dumps(input_context, allow_nan=False).encode("utf-8"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "InputParseNode: input_context must be finite JSON data"}
        if context_bytes > _MAX_CONTEXT_BYTES:
            return {"ok": False, "error": "InputParseNode: input_context exceeds 256 KiB"}

        facility_value = input_context.get("facility_id", "")
        report_value = input_context.get("report_type", "")
        if not isinstance(facility_value, str) or not isinstance(report_value, str):
            return {"ok": False, "error": "InputParseNode: facility_id and report_type must be strings"}
        facility_id = facility_value.strip()
        report_type = report_value.strip()
        sensor_alerts = input_context.get("sensor_alerts")  # optional, proposal §4 Notes
        maintenance_records = input_context.get("maintenance_records", [])

        if not facility_id or not _FACILITY_ID_RE.match(facility_id):
            return {
                "ok": False,
                "error": f"InputParseNode: invalid or missing facility_id ({facility_id!r})",
            }
        if report_type not in _VALID_REPORT_TYPES:
            return {
                "ok": False,
                "error": (
                    f"InputParseNode: invalid report_type ({report_type!r}); "
                    f"expected one of {sorted(_VALID_REPORT_TYPES)}"
                ),
            }
        if not isinstance(user_input, str) or not user_input.strip():
            return {"ok": False, "error": "InputParseNode: incident/inspection data is empty"}
        if len(user_input.encode("utf-8")) > _MAX_INPUT_BYTES:
            return {"ok": False, "error": "InputParseNode: incident/inspection data exceeds 1 MiB"}
        if not isinstance(maintenance_records, list) or len(maintenance_records) > _MAX_RECORDS:
            return {"ok": False, "error": "InputParseNode: maintenance_records must be a list of at most 1000 entries"}
        if sensor_alerts is not None and not isinstance(sensor_alerts, (dict, list)):
            return {"ok": False, "error": "InputParseNode: sensor_alerts must be an object or list"}
        if isinstance(sensor_alerts, list) and len(sensor_alerts) > _MAX_RECORDS:
            return {"ok": False, "error": "InputParseNode: sensor_alerts list exceeds 1000 entries"}

        incident_data = {
            "raw_text": user_input.strip(),
            "maintenance_records": maintenance_records,
        }

        normalized_alerts = None
        if sensor_alerts is not None:
            normalized_alerts = json.dumps(sensor_alerts, allow_nan=False)

        return {
            "ok": True,
            "facility_id": facility_id,
            "report_type": report_type,
            "incident_data": json.dumps(incident_data, allow_nan=False),
            "sensor_alerts": normalized_alerts,
        }


class RegulationRetrieveNode:
    """Step 2 — RAG cross-search of 高圧ガス保安法 / METI standards / ISO 19880 (tiered)."""

    def execute(self, incident_data_json: str, iso_kb_enabled: bool) -> dict[str, Any]:
        incident_data = json.loads(incident_data_json)
        if not isinstance(incident_data, dict) or not isinstance(incident_data.get("raw_text"), str):
            raise ValueError("RegulationRetrieveNode: incident_data must contain raw_text")

        query_text = str(incident_data.get("raw_text", ""))

        provisions = list(_METI_KB)
        disclaimer = None
        if iso_kb_enabled:
            provisions = provisions + list(_ISO_KB)
        else:
            disclaimer = (
                "ISO 19880 provisions not included — confirm with an ISO-certified "
                "consultant. (proposal §11 Risk #4: ISO 19880 commercial-use license "
                "unconfirmed; this deployment runs on the public METI KB only.)"
            )

        result = {
            "query_text": query_text,
            "provisions": provisions,
            "iso_kb_enabled": iso_kb_enabled,
            "disclaimer": disclaimer,
        }
        return {"ok": True, "applicable_regulations": json.dumps(result, allow_nan=False)}
