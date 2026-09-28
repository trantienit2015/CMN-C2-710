"""AgentCore Platform v1.0"""

# Outer post_process node — Step 6 OutputValidate.
# S-3 domain gate: reject fabricated benchmark figures not grounded in the
# retrieved Tier-2 passages; inject an APPI/DPO disclaimer on on-premise
# compliance claims. Deterministic regex scan, NOT an LLM self-check.

import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class OutputValidateNode(FunctionNode):
    """Validate and finalize the generated architecture recommendation."""

    # S-1: outer node — matches config/agent.yaml agent-level default.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    _BENCHMARK_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s?(?:ms\b|qps\b|ops/sec\b|%|x faster\b|gb/s\b)", re.IGNORECASE)
    _ONPREM_KEYWORDS = re.compile(r"on[- ]?premise|appi", re.IGNORECASE)
    _DISCLAIMER = (
        "Note: consult a qualified DPO/legal counsel to confirm APPI on-premise "
        "compliance requirements for your specific deployment."
    )

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # Propagate an upstream failure rather than silently recovering to
        # SUCCESS — the outer/inner pipeline edges are unconditional, so an
        # ERROR status from InputValidateNode or the inner subgraph does not
        # stop dispatch to main/post_process on its own.
        if state.get("status") in (AgentStatus.ERROR.value, AgentStatus.ERROR.value):
            return {"status": AgentStatus.ERROR.value}

        draft = state.get("draft_answer", "") or state.get("result", "")
        if not draft:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["OutputValidateNode: no draft_answer produced upstream"],
            }
        emit_trace_event(
            "output_validated",
            {"correlation_id": state.get("correlation_id"), "domain": state.get("query_domain")},
            state,
        )
        # The S-3 hook below receives only this returned dict (not graph state),
        # so the passages the answer must be grounded in travel with it. The
        # value is unchanged, so echoing it back does not alter state.
        passages = state.get("retrieved_passages", []) or []
        return {
            "formatted_output": draft,
            "retrieved_passages": passages,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        # S-3 domain check on the dict execute() returned (the framework passes
        # only that partial result, never graph state). The returned dict
        # replaces the node result, so every key execute() produced is kept.
        # Never raise, always return a dict.
        output = result.get("formatted_output", "") or ""
        retrieved = result.get("retrieved_passages", []) or []
        grounded_text = " ".join(str(passage.get("content", "")) for passage in retrieved if isinstance(passage, dict))

        fabricated = [
            match.group(0) for match in self._BENCHMARK_PATTERN.finditer(output) if match.group(0) not in grounded_text
        ]
        if fabricated:
            blocked = {key: value for key, value in result.items() if key != "formatted_output"}
            return {
                **blocked,
                "status": AgentStatus.ERROR.value,
                "error_log": [
                    f"S-3 output gate: fabricated benchmark figure(s) not grounded in retrieved KB: {fabricated}"
                ],
            }

        if self._ONPREM_KEYWORDS.search(output) and self._DISCLAIMER not in output:
            return {**result, "formatted_output": f"{output}\n\n{self._DISCLAIMER}"}

        return result
