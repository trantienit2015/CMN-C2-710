"""AgentCore Platform v1.0"""

# Inner subgraph node — Step 4 ConstraintEnrich.
# Injects the caller's scale/latency/deployment constraints into the prompt
# context for the generation step.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class ConstraintEnrichNode(FunctionNode):
    """Enrich the retrieved context with caller-supplied deployment constraints."""

    # S-1: inner subgraph node — trust authenticated at outer backbone.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # Propagate an upstream failure rather than silently recovering to
        # SUCCESS — the inner subgraph's edges are unconditional linear, so
        # ERROR status from an earlier step does not stop dispatch on its own.
        if state.get("status") in (AgentStatus.ERROR.value, AgentStatus.ERROR.value):
            return {"status": AgentStatus.ERROR.value}

        constraints = state.get("constraints", {}) or {}
        query_domain = state.get("query_domain", "")

        enriched_context = {
            "domain": query_domain,
            "scale": constraints.get("scale"),
            "latency_target_ms": constraints.get("latency_target_ms"),
            "deployment": constraints.get("deployment"),
        }

        emit_trace_event(
            "constraints_enriched",
            {"correlation_id": state.get("correlation_id"), "constraint_keys": list(constraints.keys())},
            state,
        )

        return {
            "enriched_context": enriched_context,
            "status": AgentStatus.SUCCESS.value,
        }
