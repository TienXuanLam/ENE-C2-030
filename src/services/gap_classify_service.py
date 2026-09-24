"""AgentCore Platform v1.0"""

# Step-helper classes for the main slot, part 1 (docs/02_design.md "2+4+1 split"):
#   step 3 - ComplianceGapAnalyzeNode
#   step 4 - IncidentClassifyNode
#
# Pure-Python business logic only — NOT BaseNode subclasses. Invoked sequentially
# by src/nodes/compliance_analysis_node.py (the real FunctionNode).

from __future__ import annotations

import json
from typing import Any

# Incident-type keyword heuristics (proposal §4 step 4). A production deployment
# would classify via LLM or a trained model; this deterministic mapping keeps the
# template runnable without an LLM dependency for classification.
_INCIDENT_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("leak", "gas_leak"),
    ("漏洩", "gas_leak"),
    ("pressure", "overpressure"),
    ("圧力", "overpressure"),
    ("inspection", "periodic_inspection_finding"),
    ("点検", "periodic_inspection_finding"),
]
_DEFAULT_INCIDENT_TYPE = "unclassified"

_EQUIPMENT_CATEGORY_KEYWORDS: list[tuple[str, str]] = [
    ("dispenser", "dispensing_equipment"),
    ("compressor", "compression_equipment"),
    ("storage", "storage_vessel"),
    ("貯蔵", "storage_vessel"),
]
_DEFAULT_EQUIPMENT_CATEGORY = "unspecified"


class ComplianceGapAnalyzeNode:
    """Step 3 — cross-reference incident data against retrieved regulatory provisions."""

    def execute(
        self,
        incident_data_json: str,
        applicable_regulations_json: str,
    ) -> dict[str, Any]:
        incident_data = json.loads(incident_data_json)
        regulations = json.loads(applicable_regulations_json)
        if not isinstance(incident_data, dict) or not isinstance(regulations, dict):
            raise ValueError("compliance analysis inputs must be JSON objects")

        raw_text = str(incident_data.get("raw_text", "")).lower()
        provisions = regulations.get("provisions", [])

        if not isinstance(provisions, list) or not provisions:
            raise ValueError("no applicable regulatory provisions are available")
        citation = next(
            (str(item.get("citation")) for item in provisions if isinstance(item, dict) and item.get("citation")),
            "Applicable hydrogen safety regulation",
        )

        gaps = []
        if "leak" in raw_text or "漏洩" in raw_text:
            gaps.append(
                {
                    "citation": citation,
                    "non_conformance": "Leak event requires verified detection, isolation, and statutory review",
                    "priority": "high",
                    "deadline_days": 14,
                }
            )
        elif "pressure" in raw_text or "圧力" in raw_text:
            gaps.append(
                {
                    "citation": citation,
                    "non_conformance": "Pressure event requires relief-system and operating-limit review",
                    "priority": "high",
                    "deadline_days": 7,
                }
            )

        if not gaps:
            gaps.append(
                {
                    "citation": None,
                    "non_conformance": "Automated rules were insufficient for a compliance determination",
                    "priority": "review_required",
                    "deadline_days": None,
                }
            )

        return {"ok": True, "compliance_gaps": json.dumps({"gaps": gaps}, allow_nan=False)}


class IncidentClassifyNode:
    """Step 4 — classify incident type / equipment category (drives step 6 form selection)."""

    def execute(self, incident_data_json: str) -> dict[str, Any]:
        incident_data = json.loads(incident_data_json)
        if not isinstance(incident_data, dict):
            raise ValueError("incident_data must be a JSON object")

        raw_text = str(incident_data.get("raw_text", "")).lower()

        incident_type = _DEFAULT_INCIDENT_TYPE
        for keyword, label in _INCIDENT_TYPE_KEYWORDS:
            if keyword in raw_text:
                incident_type = label
                break

        equipment_category = _DEFAULT_EQUIPMENT_CATEGORY
        for keyword, label in _EQUIPMENT_CATEGORY_KEYWORDS:
            if keyword in raw_text:
                equipment_category = label
                break

        return {
            "ok": True,
            "incident_type": incident_type,
            "equipment_category": equipment_category,
        }
