# ENE-C2-030 Design

## Classification and topology

This is a Category 2 agent. Its **L1 Base** is `AgentBaseGraph`. The fixed
outer lifecycle delegates the multi-step domain job to a real `GraphNode` and
inner `BaseGraph`:

```text
initialize -> pre_process -> HydrogenComplianceWorkflowGraphNode -> post_process -> finalize
                                  |
                                  +-> ComplianceAnalysisNode
                                      -> DocumentationNode
```

`ComplianceAnalysisNode` performs gap analysis and incident classification.
`DocumentationNode` drafts actions and statutory documents and owns the HITL
review point. A conditional edge prevents documentation from running after an
analysis error. `GraphNode.error_strategy` is `propagate`, and
`propagate_hitl` is enabled.

## Boundary responsibilities

| Boundary | Responsibility |
|---|---|
| `PreProcessNode` | Enforce size/shape limits; validate the facility, report type, alerts and maintenance records; retrieve the configured regulatory tier. |
| `ComplianceAnalysisNode` | Produce fail-closed compliance findings and incident/equipment classifications. |
| `DocumentationNode` | Draft corrective actions and disclaimed regulatory documents; interrupt for high-priority expert review. |
| `PostProcessNode` | Assemble the caller-facing package, recheck the disclaimer and sensitive-detail policy, and expose regulatory-scope disclosure. |

## State and checkpoint safety

`State` extends `AgentState`. Domain mappings and lists cross node boundaries
only as JSON strings; configuration and credentials are not stored in state.
HITL fields are inherited from the framework rather than redeclared by the
template.

## Fail-closed compliance rules

- `user_input` is limited to 1 MiB and `input_context` to 256 KiB.
- Unknown context fields, non-JSON/non-finite values, invalid identifiers, and
  oversized alert/maintenance collections are rejected.
- Malformed intermediate JSON or a missing regulation set produces an error;
  it is never converted into a clean-compliance result.
- Leak and pressure incidents become high-priority review findings even while
  the ISO tier is disabled.
- If deterministic rules cannot establish a result, status is
  `manual_review_required`, not compliant.
- Every generated statutory document carries the exact expert-review
  disclaimer. Corrections may update only the two documented draft fields and
  are checked again by the S-3 output gate.

## Regulatory knowledge disclosure

`iso_kb_enabled` defaults to `false`. The final package contains
`regulatory_scope` with enabled tier, source names, and the explicit ISO 19880
coverage disclaimer. Enabling the ISO tier removes the disclaimer only when
the corresponding licensed corpus is intentionally configured.

## Runtime and security

The standalone adapter loads `config/config.yaml`, compiles with a
`MemorySaver` when memory/HITL is enabled, distinguishes external and internal
Bearer credentials, and uses framework `InvocationContext`. All real domain
nodes declare `VERIFIED_EXTERNAL`, emit audit events, and retain framework
S-1/S-2/S-3/S-4 boundaries.
