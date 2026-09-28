# CMN-C2-710 — Unit Tests: TechRetrieveNode

from framework.schemas.agent_status import AgentStatus
from src.nodes.tech_retrieve_node import TechRetrieveNode


class TestTechRetrieveNode:
    def setup_method(self):
        self.node = TechRetrieveNode()

    def test_success_path(self):
        state = {
            "query_text": "How do I tune HNSW efConstruction and M?",
            "query_domain": "index_config",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert len(result["retrieved_passages"]) > 0
        assert len(result["external_refs"]) > 0

    def test_missing_query_text_error(self):
        state = {"query_text": "", "query_domain": "index_config"}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR

    def test_unknown_domain_returns_empty_passages(self):
        state = {"query_text": "some question", "query_domain": "unknown_domain"}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["retrieved_passages"] == []
