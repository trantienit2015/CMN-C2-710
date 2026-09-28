"""AgentCore Platform v1.0"""

# Outer pre_process node — Step 1 InputValidate.
# S-1 trust gate (required_trust_level) is framework-enforced via __call__().
# S-2 domain scan (credentials / connection strings / endpoint URLs embedded
# in the question) runs via the _extra_security_gate_input() hook — a
# deterministic regex scan, NOT an LLM check.

import json
import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class InputValidateNode(FunctionNode):
    """Validate the incoming vector-search question and build the inner-graph envelope."""

    # S-1: outer node — matches config/agent.yaml agent-level default.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    _CREDENTIAL_PATTERN = re.compile(
        r"(sk-[A-Za-z0-9]{10,}|eyJ[A-Za-z0-9_\-]{10,}|AKIA[0-9A-Z]{10,}"
        r"|(?:mongodb|postgres|redis|mysql)://\S+"
        r"|https?://\S+:\d{2,5}(?:/\S*)?)",
        re.IGNORECASE,
    )

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("user_input", "")
        input_context = state.get("input_context", {}) or {}

        if not user_input or not user_input.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["InputValidateNode: user_input is empty or missing"],
            }

        constraints = input_context.get("constraints", {}) if isinstance(input_context, dict) else {}
        envelope = json.dumps({"query": user_input.strip(), "constraints": constraints}, ensure_ascii=False)

        emit_trace_event(
            "input_validated",
            {"correlation_id": state.get("correlation_id"), "has_constraints": bool(constraints)},
            state,
        )

        return {
            "validated_input": envelope,
            "constraints": constraints,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        # S-2 domain check: never raise, always return a dict.
        user_input = state.get("user_input", "") or ""
        if self._CREDENTIAL_PATTERN.search(user_input):
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["S-2 input gate: credential/connection-string/endpoint pattern detected in query"],
            }
        return state
