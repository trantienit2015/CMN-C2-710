# Template Design Specification

## Position in AgentCore Architecture

- **Agent Class**: VectorSearchAdvisoryGraph (outer) + VectorSearchAdvisoryGraphNode (GraphNode, `main` slot) + VectorSearchAdvisoryWorkflowGraph (inner)
- **L1 Base**: AgentBaseGraph (outer, L1 direct) + BaseGraph (inner subgraph)
- **Three-Layer Separation**:
  - State: flat TypedDict composition (no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution); Cat 2 pattern — outer backbone + GraphNode wrapping inner subgraph

## Architecture Overview

### Node Configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | schema_version, session_id, trust_level | — | — | InitializeNode (default) |
| pre_process (InputValidateNode) | S-2 domain scan (credential/connection-string/endpoint regex) + build JSON envelope for inner graph | `user_input`, `input_context` | `validated_input`, `constraints` | FunctionNode |
| main (VectorSearchAdvisoryGraphNode → inner VectorSearchAdvisoryWorkflowGraph) | dispatch to inner: classify domain → retrieve Tier-2 KB + Tier-1 refs → enrich constraints → LLM-generate recommendation | `validated_input` | `query_domain`, `retrieved_passages`, `external_refs`, `draft_answer` | GraphNode wrapping BaseGraph |
| ↳ inner: query_classify (QueryClassifyNode) | parse envelope, classify into 1 of 6 domains | `user_input` (JSON envelope) | `query_text`, `query_domain`, `constraints` | FunctionNode (inner, ANONYMOUS) |
| ↳ inner: tech_retrieve (TechRetrieveNode) | hybrid Tier-2 KB retrieval + Tier-1 external refs, filtered by domain | `query_text`, `query_domain` | `retrieved_passages`, `external_refs` | FunctionNode (inner, ANONYMOUS) |
| ↳ inner: constraint_enrich (ConstraintEnrichNode) | inject caller scale/latency/deployment constraints into prompt context | `constraints`, `query_domain` | `enriched_context` | FunctionNode (inner, ANONYMOUS) |
| ↳ inner: architecture_generate (ArchitectureGenerateNode) | LLM generates config recommendation + YAML + tradeoffs | `query_text`, `retrieved_passages`, `enriched_context` | `draft_answer` | FunctionNode (inner, ANONYMOUS) |
| post_process (OutputValidateNode) | S-3 domain gate: reject fabricated benchmark figures not grounded in retrieved passages; inject APPI/DPO disclaimer | `draft_answer`, `retrieved_passages` | `formatted_output` (+ `retrieved_passages` echoed unchanged, because the S-3 hook sees only the node's own result) | FunctionNode |
| finalize | response_metadata, total_time_ms | — | — | FinalizeNode (default) |

### Data Flow

```
START → initialize → pre_process → main(GraphNode) → {route} → post_process → finalize → END
                                        │ inner: query_classify → tech_retrieve
                                        │        → constraint_enrich → architecture_generate
                                            ↓ (retry)
                                          pre_process
```

### State Definition

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| query_text | NotRequired[str] | parsed question text (set by inner query_classify) | No |
| query_domain | NotRequired[str] | classified domain tag (1 of 6) | No |
| constraints | NotRequired[dict] | caller-supplied scale/latency/deployment constraints | No |
| retrieved_passages | NotRequired[list[dict]] | Tier-2 KB passages retrieved for the question | No |
| external_refs | NotRequired[list[str]] | Tier-1 public OSS doc URLs referenced (not ingested) | No |
| draft_answer | NotRequired[str] | LLM-generated recommendation before S-3 validation | No |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types)
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, permissions, credential handle)
- [ ] ConnectionPolicy (retry/timeout strategy) — not needed, no external network call with retry semantics
- [x] SecurityViolationError (framework-raised on S-2 default PII scan)
- [x] S-2: `_extra_security_gate_input()` on InputValidateNode — deterministic regex scan for
      credentials/connection-strings/endpoint URLs embedded in the question (NOT an LLM check).
- [x] S-3: `_extra_security_gate_output()` on OutputValidateNode — regex-screen rejects fabricated
      benchmark figures not grounded in retrieved Tier-2 passages; injects an APPI/DPO disclaimer
      when the output makes an on-premise compliance claim (preservation variant).
      The hook receives only the dict `execute()` returned, so `execute()` returns the passages the
      answer is checked against, and the hook keeps every key of that result.
- [x] S-4: `emit_trace_event()` — at least one domain-specific event inside each `execute()`
      (input_validated, query_classified, kb_retrieved, constraints_enriched,
      architecture_generated, plus GraphNode wrapper hooks vector_search_advisory_dispatched/completed)

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs automatically;
>   extend via `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` / `RemoteAgentNode` → deliberate no-op (upstream or remote node's gate already applied)
> - Custom `BaseNode` subclass → must implement `_security_gate_input()` and
>   `_security_gate_output()` directly (`@abstractmethod` — omission raises `TypeError` at instantiation)

### Composition Pattern

- **Pattern**: GraphNode (subgraph) — outer `main` slot wraps the inner `VectorSearchAdvisoryWorkflowGraph`
- **Composition target**: `src/graph/domain_workflow_graph.py` (inner `BaseGraph`)
- **Error propagation strategy**: propagate (`error_strategy = "propagate"`) — inner failures fail fast. The one degraded mode is the no-LLM case: when no LLM client is configured, `ArchitectureGenerateNode` returns a deterministic answer labelled "Retrieval-only answer (no language model configured)" that lists the retrieved passages and references, and emits its trace event with `method: retrieval_only`

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: framework/ and shared/ only (no agents/base/ required)

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | AgentBaseGraph | Fixed advisory pipeline, no autonomous loop/termination needed |
| Composition pattern | Flat 3-node (Cat 1 style) | GraphNode + inner subgraph (Cat 2) | GraphNode + inner subgraph | Cat 2 requires outer AgentBaseGraph + GraphNode in `main`, per the gate-composition check |
| KB retrieval scoring | Real dense embedding + BM25 hybrid | Deterministic term-overlap scoring (BM25-lite) | Deterministic term-overlap (Phase 3 placeholder) | No embedding client wired yet; same `KBRetrievalService.retrieve()` interface swaps in a real hybrid retriever without touching node code |
| S-3 fabricated-benchmark detection | LLM self-check | Deterministic regex vs grounded-passage text | Deterministic regex | S-3 gate must be non-LLM, deterministic |
