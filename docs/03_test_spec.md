# Test Specification

## Test Strategy
- Coverage target: every node covers success path + error/edge path (CLAUDE.md §8-1);
  domain gate branches (S-2 facility_id reject, S-3 disclaimer/sensitive-detail block,
  S-5 tiered KB) each covered explicitly.
- Test types: Unit (`tests/unit/`) / Integration (`tests/integration/`) /
  Proof-of-Boundary (`tests/proof_of_boundary/`)

## Framework Compliance Tests (Mandatory — 7 TC)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: `State` (src/schemas/state.py) is a flat TypedDict, all fields primitives/`Optional[str]` JSON | Type check pass, no Pydantic/dataclass | |
| TC-02 | `required_trust_level` enforced on every real FunctionNode | Pre-process, compliance-analysis, documentation, and post-process nodes called via `__call__()` with `caller_trust_level=ANONYMOUS` → `status=error`, `execute()` not invoked | |
| TC-03 | S-2: `_extra_security_gate_input()` on `PreProcessNode` rejects missing `facility_id` | `status=error`, `error_log` contains "facility_id is required"; hook does not raise | |
| TC-04 | S-3: `_extra_security_gate_output()` on `DocumentationNode` + `PostProcessNode` blocks output missing the mandatory AI-draft disclaimer | `RuntimeError` raised, `__call__()` converts to `status=error` | |
| TC-05 | S-4: domain `emit_trace_event()` called at least once inside every real dispatcher's `execute()` (no duplicate `node_start`/`node_complete`/`node_error`) | ≥1 domain event per node; 0 duplicate lifecycle events in `execute()` body | |
| TC-06 | Import isolation: no `agenticstar` SDK import anywhere under `src/` | AST scan: 0 violations | |
| TC-07 | HITL compliance: `config/config.yaml` has `hitl.enabled: true` AND `memory_enabled: true`; `DocumentationNode` uses `interrupt()` and writes only `hitl_draft` | Config validated; no other HITL field written by template code | |

## Business Logic / Compliance Gate Tests

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | `RegulationRetrieveNode` — `iso_kb_enabled=false` (default) | incident text, no ISO flag | `applicable_regulations` contains only METI KB provisions + explicit ISO-not-included disclaimer | |
| BL-02 | `RegulationRetrieveNode` — `iso_kb_enabled=true` | incident text, ISO flag on | `applicable_regulations` contains both METI + ISO 19880 provisions, no disclaimer | |
| BL-03 | `ComplianceGapAnalyzeNode` — leak keyword present | incident text mentioning a leak + leak-detection provision | `compliance_gaps` includes a `high` priority non-conformance with a 14-day deadline | |
| BL-04 | `IncidentClassifyNode` — keyword classification | incident text mentioning "pressure" | `incident_type="overpressure"` | |
| BL-05 | `RegulatorySubmissionFormatNode` — disclaimer presence | any valid gap/action-plan input | Both `incident_report` and `regulatory_submission_draft` contain the exact `AI_DRAFT_DISCLAIMER` string | |
| BL-06 | `PostProcessNode` S-3 — sensitive detail marker blocked | `formatted_output` containing a `_SENSITIVE_DETAIL_MARKERS` term (e.g. `"vulnerability"`) | `RuntimeError` raised before output leaves node boundary | |

## Proof-of-Boundary Tests (Mandatory — 4 PB, this revision)

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-01 | S-1 trust gate | Invoke every real FunctionNode via `__call__()` with `caller_trust_level=ANONYMOUS` | `execute()` never runs; `status=error` returned by the framework before business logic | |
| PB-02 | S-3 output credential/content gate | `DocumentationNode`/`PostProcessNode` result missing the mandatory disclaimer, or containing a sensitive-detail marker | `_extra_security_gate_output()` raises `RuntimeError`; sensitive content never reaches the caller | |
| PB-03 | S-5 tiered KB source disclosure | `RegulationRetrieveNode.execute(..., iso_kb_enabled=False)` | Output includes the explicit "ISO 19880 provisions not included" disclaimer — no implicit/silent omission of the licensing-gated source | |
| PB-07 | HITL interrupt propagation (`hitl.enabled: true`) | `DocumentationNode` calls `interrupt()` for `priority=high`; `interrupt()` is monkeypatched to raise `GraphInterrupt` | `GraphInterrupt` propagates uncaught through `execute()` and `__call__()`; template writes only `hitl_draft` | |

> Full 6-PB framework template (`import_isolation`, `state_safety`, `invoke_order`, etc.)
> remains available under `tests/proof_of_boundary/` from scaffold defaults; PB-01/02/03/07
> above are the domain-specific additions for this template revision (tasks #12, #HITL).

## Test Execution Summary
- Execution date: _pending first CI run on `feature/implement-core-pipeline`_
- Total tests: _see tests/unit, tests/integration, tests/proof_of_boundary_
- Pass: / Fail: / Skip:
- Coverage: _pending `pytest --cov`_
