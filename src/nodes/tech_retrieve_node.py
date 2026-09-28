"""AgentCore Platform v1.0"""

# Inner subgraph node — Step 3 TechRetrieve.
# Hybrid (dense+BM25) retrieval over the curated Tier-2 KB, filtered by
# domain; Tier-1 OSS docs referenced as external URLs (not ingested).

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.kb_retrieval_service import KBRetrievalService


class TechRetrieveNode(FunctionNode):
    """Retrieve grounding passages from the Tier-2 KB + Tier-1 external refs."""

    # S-1: inner subgraph node — trust authenticated at outer backbone.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, kb_service: KBRetrievalService | None = None):
        self._kb_service = kb_service or KBRetrievalService()

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        query_text = state.get("query_text", "")
        query_domain = state.get("query_domain", "")

        if not query_text:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["TechRetrieveNode: missing query_text from QueryClassifyNode"],
            }

        passages, external_refs = self._kb_service.retrieve(query_text, query_domain)

        emit_trace_event(
            "kb_retrieved",
            {
                "correlation_id": state.get("correlation_id"),
                "domain": query_domain,
                "passage_count": len(passages),
                "ref_count": len(external_refs),
            },
            state,
        )

        return {
            "retrieved_passages": passages,
            "external_refs": external_refs,
            "status": AgentStatus.SUCCESS.value,
        }
