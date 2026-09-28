# CMN-C2-710 — Integration test: full graph compile + invoke (Cat 2 outer + inner).

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import Graph

QUESTION = "How should I tune HNSW efConstruction and M for a 10M-vector index?"
EMPTY_INPUT = ""


class _FakeLLM:
    def complete(self, prompt: str) -> str:
        return "Recommended config: HNSW M=16, efConstruction=200. See tradeoffs above."


class _CanonicalLLM:
    """Returns the canonical BaseLLM.complete() dict, like the shipped clients."""

    def complete(self, messages):
        return {"content": "Recommended config: HNSW M=16, efConstruction=200.", "tool_calls": [], "model": "fake", "usage": {}}


class TestAgentIntegration:
    def test_llm_path_with_canonical_completion_returns_text(self):
        agent = Graph(config={"llm": _CanonicalLLM(), "max_retry": 1, "top_k": 3})
        agent.compile()
        ctx = InvocationContext(session_id="it-4", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="engineer-001")
        result = agent.invoke(QUESTION, ctx=ctx)
        assert result["status"] == "success"
        assert "HNSW M=16, efConstruction=200." in str(result.get("output"))
        assert "'content'" not in str(result.get("output"))

    def test_happy_path_reaches_full_pipeline(self):
        agent = Graph(config={"llm": _FakeLLM(), "max_retry": 1, "top_k": 3})
        agent.compile()
        ctx = InvocationContext(session_id="it-1", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="engineer-001")
        result = agent.invoke(QUESTION, ctx=ctx)

        assert len(result.get("node_history", [])) >= 4
        assert result["status"] in ("success", "error", "cancelled")

    def test_empty_input_error(self):
        agent = Graph(config={"llm": _FakeLLM(), "max_retry": 1})
        agent.compile()
        ctx = InvocationContext(session_id="it-2", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="engineer-001")
        result = agent.invoke(EMPTY_INPUT, ctx=ctx)
        assert result["status"] in ("error", "cancelled")

    def test_no_llm_configured_returns_retrieval_only_answer(self):
        agent = Graph(config={"max_retry": 1})
        agent.compile()
        ctx = InvocationContext(session_id="it-3", caller_trust_level=TrustLevel.VERIFIED_EXTERNAL, caller_id="engineer-001")
        result = agent.invoke(QUESTION, ctx=ctx)
        assert result["status"] == "success"
        assert "Retrieval-only answer" in str(result.get("output"))
