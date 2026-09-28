# CMN-C2-710 — Unit Tests: ArchitectureGenerateNode

from framework.schemas.agent_status import AgentStatus
from src.nodes.architecture_generate_node import ArchitectureGenerateNode


class _FakeLLM:
    def complete(self, prompt: str) -> str:
        return "Recommended config: HNSW M=16, efConstruction=200."


class _CanonicalLLM:
    """Returns the canonical BaseLLM.complete() dict, like the shipped clients."""

    def __init__(self, content):
        self._content = content
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        return {"content": self._content, "tool_calls": [], "model": "fake-model", "usage": {}}


_STATE = {
    "query_text": "How do I tune HNSW?",
    "query_domain": "index_config",
    "retrieved_passages": [{"id": "idx-001", "title": "HNSW tuning", "content": "M controls recall."}],
    "external_refs": [],
    "enriched_context": {"domain": "index_config"},
}


class TestArchitectureGenerateNode:
    def test_canonical_completion_dict_is_normalised_to_text(self):
        llm = _CanonicalLLM("Recommended config: HNSW M=16, efConstruction=200.")
        result = ArchitectureGenerateNode(llm=llm).execute(dict(_STATE))
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["draft_answer"] == "Recommended config: HNSW M=16, efConstruction=200."
        assert isinstance(result["draft_answer"], str)
        # The prompt is sent as a message list, per the BaseLLM contract.
        assert llm.calls[0][0]["role"] == "user"
        assert "How do I tune HNSW?" in llm.calls[0][0]["content"]

    def test_content_block_list_is_joined_to_text(self):
        llm = _CanonicalLLM([{"type": "text", "text": "Use HNSW "}, {"type": "text", "text": "with M=16."}])
        result = ArchitectureGenerateNode(llm=llm).execute(dict(_STATE))
        assert result["draft_answer"] == "Use HNSW with M=16."

    def test_empty_completion_content_errors(self):
        result = ArchitectureGenerateNode(llm=_CanonicalLLM("")).execute(dict(_STATE))
        assert result["status"] == AgentStatus.ERROR.value
        assert "draft_answer" not in result

    def test_success_path(self):
        node = ArchitectureGenerateNode(llm=_FakeLLM())
        state = {
            "query_text": "How do I tune HNSW?",
            "query_domain": "index_config",
            "retrieved_passages": [{"id": "idx-001", "title": "HNSW tuning", "content": "M controls recall."}],
            "external_refs": ["https://github.com/facebookresearch/faiss/wiki"],
            "enriched_context": {"domain": "index_config"},
            "node_history": [],
            "error_log": [],
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert "HNSW" in result["draft_answer"]

    def test_no_llm_configured_returns_retrieval_only_answer(self):
        node = ArchitectureGenerateNode(llm=None)
        state = {
            "query_text": "How do I tune HNSW?",
            "query_domain": "index_config",
            "retrieved_passages": [{"id": "idx-001", "title": "HNSW tuning", "content": "M controls recall."}],
            "external_refs": ["https://github.com/facebookresearch/faiss/wiki"],
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["draft_answer"].startswith("Retrieval-only answer (no language model configured)")
        assert "HNSW tuning: M controls recall." in result["draft_answer"]

    def test_missing_query_text_error(self):
        node = ArchitectureGenerateNode(llm=None)
        result = node.execute({})
        assert result["status"] == AgentStatus.ERROR.value
