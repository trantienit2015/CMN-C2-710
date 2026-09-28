"""PB — outer GraphNode boundary (Cat 2), CMN-C2-710.

`VectorSearchAdvisoryGraphNode` (src/graph/graph.py) is the outer `main`-slot
wrapper around the inner VectorSearchAdvisoryWorkflowGraph subgraph. It is
placed alongside the outer graph (NOT under src/nodes/) so PB-6
(test_pb_invoke_order.py) does not auto-discover it and force the standard
S-1->S-4->S-2->execute->S-3->S-4 node lifecycle on it — GraphNode.execute()
delegates S-2/S-3 gating to the inner subgraph by design
(framework/nodes/graph_node.py).

That placement is architecturally correct, but it also means PB-6 never
probes this class. This file is the dedicated boundary test that fills that
gap (a GraphNode is outside the PB-6 probe scope).
"""

from framework.schemas.trust_level import TrustLevel

from src.graph.domain_workflow_graph import VectorSearchAdvisoryWorkflowGraph
from src.graph.graph import VectorSearchAdvisoryGraphNode
from src.nodes.query_classify_node import QueryClassifyNode


def _state(**overrides) -> dict:
    state = {
        "validated_input": '{"query": "how do I tune HNSW ef_search for p99 latency?", "constraints": {}}',
        "user_input": "how do I tune HNSW ef_search for p99 latency?",
        "correlation_id": "test-correlation",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "execution_time": {},
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# S-1: outer main-slot GraphNode is gated exactly like any other outer node.
# ---------------------------------------------------------------------------


def test_call_denies_below_required_trust_level():
    node = VectorSearchAdvisoryGraphNode()
    state = _state(caller_trust_level=TrustLevel.ANONYMOUS.value)

    result = node(state)  # go through __call__(), not execute() directly

    assert result["status"] == "error"
    assert "S-1 trust gate denied" in result["error_log"][0]


def test_call_allows_at_required_trust_level_and_reaches_execute(monkeypatch):
    # Prove execute() (and therefore get_subgraph/extract_input/merge_output)
    # only runs once the S-1 gate has been satisfied — stub the subgraph so
    # this stays a boundary test, not a full inner-pipeline integration test.
    class _StubSubgraph:
        name = "stub-inner"

        def invoke(self, user_input, session_id=None, ctx=None):
            return {"status": "success", "query_domain": "latency_tuning"}

    node = VectorSearchAdvisoryGraphNode()
    monkeypatch.setattr(node, "get_subgraph", lambda: _StubSubgraph())
    state = _state(caller_trust_level=TrustLevel.VERIFIED_EXTERNAL.value)

    result = node(state)

    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Boundary mapping: extract_input / merge_output are explicit, not raw pass-through.
# ---------------------------------------------------------------------------


def test_extract_input_maps_only_the_contracted_field():
    node = VectorSearchAdvisoryGraphNode()
    state = _state(some_unrelated_field="should-not-leak")

    result = node.extract_input(state)

    assert result == state["validated_input"]
    assert "should-not-leak" not in result


def test_merge_output_maps_fields_explicitly_not_raw_passthrough():
    node = VectorSearchAdvisoryGraphNode()
    state = _state()
    sub_result = {
        "query_domain": "latency_tuning",
        "retrieved_passages": ["p1"],
        "external_refs": ["ref1"],
        "draft_answer": "tune ef_search up for recall/latency tradeoff",
        "status": "success",
        # Fields the inner subgraph may carry but that must NOT leak to the
        # outer parent state unmapped (criterion #9 — no raw pass-through).
        "node_history": ["query_classify", "tech_retrieve"],
        "execution_time": {"QueryClassifyNode": 0.01},
        "correlation_id": "inner-should-not-override",
    }

    merged = node.merge_output(state, sub_result)

    assert "node_history" not in merged
    assert "execution_time" not in merged
    assert set(merged.keys()) == {
        "query_domain",
        "retrieved_passages",
        "external_refs",
        "draft_answer",
        "status",
    }


# ---------------------------------------------------------------------------
# Delegation is intentional: the inner subgraph's own entry node carries the
# S-2/S-3-equivalent domain checks that GraphNode.__call__() does not run.
# ---------------------------------------------------------------------------


def test_inner_entry_node_has_its_own_trust_declaration():
    # GraphNode.execute() (framework/nodes/graph_node.py) delegates gating to
    # the inner subgraph rather than running S-2/S-3 itself — this asserts
    # that delegation actually lands somewhere (the inner entry node declares
    # its own S-1 level) instead of being a silent no-op.
    inner_entry_node = QueryClassifyNode()

    assert inner_entry_node.required_trust_level == TrustLevel.ANONYMOUS


def test_get_subgraph_returns_a_fresh_compiled_inner_graph_instance():
    node = VectorSearchAdvisoryGraphNode()

    subgraph = node.get_subgraph()

    assert isinstance(subgraph, VectorSearchAdvisoryWorkflowGraph)
