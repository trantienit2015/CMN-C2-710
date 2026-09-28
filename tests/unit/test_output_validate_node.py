# CMN-C2-710 — Unit Tests: OutputValidateNode

from framework.schemas.agent_status import AgentStatus
from src.nodes.output_validate_node import OutputValidateNode


class TestOutputValidateNode:
    def setup_method(self):
        self.node = OutputValidateNode()

    def test_success_path(self):
        state = {"draft_answer": "Use HNSW with M=16.", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["formatted_output"] == "Use HNSW with M=16."

    def test_empty_draft_errors(self):
        state = {"draft_answer": "", "result": "", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR

    def test_upstream_error_propagates(self):
        state = {"status": AgentStatus.ERROR, "draft_answer": "", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR

    def test_extra_security_gate_output_rejects_fabricated_benchmark(self):
        state = {
            "formatted_output": "This config gives you 99% faster search.",
            "retrieved_passages": [{"id": "idx-001", "content": "HNSW M controls recall/latency tradeoff."}],
        }
        result = self.node._extra_security_gate_output(state)
        assert result["status"] == AgentStatus.ERROR
        assert "fabricated" in result["error_log"][0].lower()

    def test_extra_security_gate_output_passes_grounded_figure(self):
        state = {
            "formatted_output": "Recall improves at 95% with M=32.",
            "retrieved_passages": [{"id": "idx-001", "content": "M=32 achieves 95% recall in benchmarks."}],
        }
        result = self.node._extra_security_gate_output(state)
        assert "status" not in result or result.get("status") != AgentStatus.ERROR

    def test_extra_security_gate_output_injects_appi_disclaimer(self):
        state = {
            "formatted_output": "Deploy this on-premise for APPI compliance.",
            "retrieved_passages": [],
        }
        result = self.node._extra_security_gate_output(state)
        assert "DPO" in result["formatted_output"]

    # The framework hands _extra_security_gate_output() only the dict execute()
    # returned, never graph state; these run execute() and then the real @final
    # S-3 gate on its result, exactly as BaseNode.__call__() does.
    def test_gate_on_execute_result_passes_grounded_figure(self):
        state = {
            "draft_answer": "Recall improves to 95% with M=32.",
            "retrieved_passages": [{"id": "idx-001", "content": "M=32 achieves 95% recall in benchmarks."}],
        }
        result = self.node._security_gate_output(self.node.execute(state))
        assert result["status"] == AgentStatus.SUCCESS.value
        assert result["formatted_output"] == "Recall improves to 95% with M=32."

    def test_gate_on_execute_result_rejects_ungrounded_figure(self):
        state = {
            "draft_answer": "This config gives you 99% faster search.",
            "retrieved_passages": [{"id": "idx-001", "content": "M=32 achieves 95% recall in benchmarks."}],
        }
        result = self.node._security_gate_output(self.node.execute(state))
        assert result["status"] == AgentStatus.ERROR.value
        assert "formatted_output" not in result
        assert "99%" in result["error_log"][0]

    def test_gate_on_execute_result_keeps_status_when_adding_disclaimer(self):
        state = {"draft_answer": "Deploy this on-premise for APPI compliance.", "retrieved_passages": []}
        result = self.node._security_gate_output(self.node.execute(state))
        assert result["status"] == AgentStatus.SUCCESS.value
        assert "DPO" in result["formatted_output"]
