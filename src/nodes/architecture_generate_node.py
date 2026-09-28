"""AgentCore Platform v1.0"""

# Inner subgraph node — Step 5 ArchitectureGenerate.
# LLM generates the configuration recommendation + YAML example + tradeoff
# analysis from the retrieved passages and enriched constraint context.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class ArchitectureGenerateNode(FunctionNode):
    """Generate the vector-search architecture/tuning recommendation."""

    # S-1: inner subgraph node — trust authenticated at outer backbone.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # Propagate an upstream failure rather than silently recovering to
        # SUCCESS — the inner subgraph's edges are unconditional linear, so
        # ERROR status from an earlier step does not stop dispatch on its own.
        if state.get("status") in (AgentStatus.ERROR.value, AgentStatus.ERROR.value):
            return {"status": AgentStatus.ERROR.value}

        query_text = state.get("query_text", "")
        query_domain = state.get("query_domain", "")
        passages = state.get("retrieved_passages", []) or []
        external_refs = state.get("external_refs", []) or []
        enriched_context = state.get("enriched_context", {}) or {}

        if not query_text:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["ArchitectureGenerateNode: missing query_text"],
            }

        if self._llm is None:
            # No LLM client configured (the standalone entry point injects one only
            # when an API key is available). Return a deterministic retrieval-only
            # answer built from the knowledge-base passages, labelled as such, so the
            # pipeline stays usable; it is not a generated recommendation.
            draft_answer = self._retrieval_only_answer(query_domain, passages, external_refs)
            emit_trace_event(
                "architecture_generated",
                {"correlation_id": state.get("correlation_id"), "domain": query_domain, "method": "retrieval_only"},
                state,
            )
            return {
                "draft_answer": draft_answer,
                "status": AgentStatus.SUCCESS.value,
            }

        passage_text = "\n".join(f"- {p.get('title', '')}: {p.get('content', '')}" for p in passages)
        ref_text = "\n".join(f"- {ref}" for ref in external_refs)
        prompt = (
            f"Question ({query_domain}): {query_text}\n\n"
            f"Grounding passages:\n{passage_text}\n\n"
            f"Constraints: {enriched_context}\n\n"
            f"External references:\n{ref_text}\n\n"
            "Produce a config recommendation with a YAML example and tradeoff analysis, "
            "grounded strictly in the passages above."
        )

        completion = self._llm.complete([{"role": "user", "content": prompt}])
        draft_answer = self._completion_text(completion)
        if not draft_answer:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["ArchitectureGenerateNode: LLM returned no text content"],
            }

        emit_trace_event(
            "architecture_generated",
            {"correlation_id": state.get("correlation_id"), "domain": query_domain},
            state,
        )

        return {
            "draft_answer": draft_answer,
            "status": AgentStatus.SUCCESS.value,
        }

    @staticmethod
    def _completion_text(completion: Any) -> str:
        """Normalise a ``BaseLLM.complete()`` result to plain text.

        The canonical completion is a dict whose ``content`` holds the text (a
        string, or a list of content blocks for some providers). A plain string
        is accepted as-is so simple test doubles keep working.
        """
        if isinstance(completion, str):
            return completion
        content = completion.get("content", "") if isinstance(completion, dict) else getattr(completion, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            return "".join(parts)
        return ""

    @staticmethod
    def _retrieval_only_answer(query_domain: str, passages: list[Any], external_refs: list[Any]) -> str:
        """Deterministic answer used when no LLM is configured: the retrieved passages verbatim."""
        lines = [
            f"Retrieval-only answer (no language model configured) for a {query_domain or 'general'} question.",
            "Relevant knowledge-base guidance:",
        ]
        if passages:
            lines.extend(f"- {p.get('title', '')}: {p.get('content', '')}" for p in passages)
        else:
            lines.append("- No matching knowledge-base passage was found.")
        if external_refs:
            lines.append("External references:")
            lines.extend(f"- {ref}" for ref in external_refs)
        lines.append("Configure an LLM client for a tailored recommendation with a YAML example and tradeoff analysis.")
        return "\n".join(lines)
