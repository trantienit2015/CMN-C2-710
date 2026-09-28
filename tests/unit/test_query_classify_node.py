# CMN-C2-710 — Unit Tests: QueryClassifyNode

import json

from framework.schemas.agent_status import AgentStatus
from src.nodes.query_classify_node import QueryClassifyNode


class TestQueryClassifyNode:
    def setup_method(self):
        self.node = QueryClassifyNode()

    def test_success_path_index_config(self):
        envelope = json.dumps({"query": "How do I tune HNSW efConstruction?", "constraints": {"scale": "10M"}})
        state = {"user_input": envelope, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["query_domain"] == "index_config"
        assert result["constraints"] == {"scale": "10M"}

    def test_success_path_onprem_appi(self):
        envelope = json.dumps({"query": "Can I deploy this on-premise in Japan for APPI compliance?", "constraints": {}})
        state = {"user_input": envelope}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["query_domain"] == "onprem_appi"

    def test_empty_query_error(self):
        state = {"user_input": json.dumps({"query": "", "constraints": {}})}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR

    def test_unparseable_envelope_error(self):
        state = {"user_input": "not-json"}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
