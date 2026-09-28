"""AgentCore Platform v1.0"""

# Inner subgraph node — Step 2 QueryClassify.
# Trust authenticated once at the outer backbone (InputValidateNode); this
# inner node runs at ANONYMOUS per the inner-vs-outer trust rule.

import json
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "index_config": ["index", "hnsw", "ivf", "m", "efconstruction", "efsearch", "nlist", "nprobe"],
    "ann_algorithm": ["ann", "algorithm", "faiss", "approximate", "nearest", "neighbor"],
    "latency_tuning": ["latency", "p95", "p99", "throughput", "qps", "speed", "slow"],
    "hybrid_search": ["hybrid", "bm25", "dense", "sparse", "rerank", "fusion"],
    "onprem_appi": ["on-premise", "on premise", "onprem", "appi", "japan", "compliance", "residency"],
    "benchmark_interpretation": ["benchmark", "recall", "tradeoff", "compare", "comparison"],
}
_DEFAULT_DOMAIN = "index_config"


class QueryClassifyNode(FunctionNode):
    """Classify the question into one of six vector-search domains."""

    # S-1: inner subgraph node — trust authenticated at outer backbone.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        raw = state.get("user_input", "")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            payload = None

        query = (payload or {}).get("query", "") if isinstance(payload, dict) else ""
        constraints = (payload or {}).get("constraints", {}) if isinstance(payload, dict) else {}

        if not query or not query.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["QueryClassifyNode: empty or unparseable query"],
            }

        domain = self._classify(query)

        emit_trace_event(
            "query_classified",
            {"correlation_id": state.get("correlation_id"), "domain": domain},
            state,
        )

        return {
            "query_text": query.strip(),
            "query_domain": domain,
            "constraints": constraints if isinstance(constraints, dict) else {},
            "status": AgentStatus.SUCCESS.value,
        }

    @staticmethod
    def _classify(query: str) -> str:
        terms = query.lower()
        best_domain, best_score = _DEFAULT_DOMAIN, 0
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in terms)
            if score > best_score:
                best_domain, best_score = domain, score
        return best_domain
