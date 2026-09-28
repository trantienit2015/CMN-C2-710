# CMN-C2-710 — Unit Tests: ConstraintEnrichNode

from framework.schemas.agent_status import AgentStatus
from src.nodes.constraint_enrich_node import ConstraintEnrichNode


class TestConstraintEnrichNode:
    def setup_method(self):
        self.node = ConstraintEnrichNode()

    def test_success_path_with_constraints(self):
        state = {
            "constraints": {"scale": "10M vectors", "latency_target_ms": 50, "deployment": "on-premise"},
            "query_domain": "latency_tuning",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["enriched_context"]["scale"] == "10M vectors"
        assert result["enriched_context"]["latency_target_ms"] == 50
        assert result["enriched_context"]["domain"] == "latency_tuning"

    def test_success_path_no_constraints(self):
        state = {"constraints": {}, "query_domain": "index_config"}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["enriched_context"]["scale"] is None
