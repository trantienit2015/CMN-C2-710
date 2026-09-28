# CMN-C2-710 — Unit Tests: InputValidateNode

from framework.schemas.agent_status import AgentStatus
from src.nodes.input_validate_node import InputValidateNode


class TestInputValidateNode:
    def setup_method(self):
        self.node = InputValidateNode()

    def test_success_path(self):
        state = {
            "user_input": "How should I tune HNSW efConstruction?",
            "input_context": {"constraints": {"scale": "10M vectors"}},
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert "validated_input" in result
        assert result["constraints"] == {"scale": "10M vectors"}

    def test_empty_input(self):
        state = {"user_input": "", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR

    def test_extra_security_gate_input_rejects_credential(self):
        # Assembled at run time so the repository never holds a literal URL credential.
        dsn = "postgres://" + "user:" + "pass" + "@host:5432/db"
        state = {"user_input": f"connect using {dsn} please"}
        result = self.node._extra_security_gate_input(state)
        assert result["status"] == AgentStatus.ERROR
        assert "S-2" in result["error_log"][0]

    def test_extra_security_gate_input_passes_clean_query(self):
        state = {"user_input": "How should I tune HNSW efConstruction?"}
        result = self.node._extra_security_gate_input(state)
        assert result is state

    def test_trust_gate_denies_insufficient_trust(self):
        from framework.schemas.trust_level import TrustLevel

        state = {
            "user_input": "How should I tune HNSW efConstruction?",
            "caller_trust_level": TrustLevel.ANONYMOUS.value,
            "node_history": [],
            "error_log": [],
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.ERROR.value
        assert any("S-1 trust gate denied" in msg for msg in result.get("error_log", []))

    def test_trust_gate_allows_sufficient_trust(self):
        from framework.schemas.trust_level import TrustLevel

        state = {
            "user_input": "How should I tune HNSW efConstruction?",
            "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
            "node_history": [],
            "error_log": [],
        }
        result = self.node(state)
        assert result["status"] == AgentStatus.SUCCESS.value
