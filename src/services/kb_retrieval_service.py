"""AgentCore Platform v1.0"""

# Service layer: Tier-2 curated KB retrieval + Tier-1 external doc references.
# Must NOT contain business logic routing or credentials.
# Deterministic term-overlap scoring (BM25-lite) — a placeholder for the real
# dense+BM25 hybrid retriever; swap the scoring function when the embedding
# client is wired up in Phase 3 KB curation, keeping the same interface.

from __future__ import annotations

from typing import Any

# Tier-2 KB: curated internal config-guide + APPI on-premise patterns + tuning
# recipes, keyed by domain tag. Version-stamped, NOT auto-synced from OSS docs.
_TIER2_KB: dict[str, list[dict[str, Any]]] = {
    "index_config": [
        {
            "id": "idx-001",
            "title": "HNSW parameter tuning",
            "content": (
                "HNSW M and efConstruction control the recall/latency tradeoff. "
                "Increasing M improves recall at higher memory cost; efSearch "
                "tunes query-time recall vs latency."
            ),
        },
        {
            "id": "idx-002",
            "title": "IVF cluster sizing",
            "content": (
                "IVF nlist should scale roughly with sqrt(N) records; nprobe "
                "trades recall for query latency at search time."
            ),
        },
    ],
    "ann_algorithm": [
        {
            "id": "ann-001",
            "title": "ANN algorithm selection",
            "content": (
                "HNSW favors low-latency high-recall in-memory search; IVF-PQ "
                "favors memory-constrained large-scale deployments; FAISS "
                "supports both under one library."
            ),
        },
    ],
    "latency_tuning": [
        {
            "id": "lat-001",
            "title": "p95/p99 latency tuning",
            "content": (
                "Reduce efSearch/nprobe for latency at recall cost; shard the "
                "index across replicas to parallelize query fan-out; cap "
                "top_k to the minimum the downstream ranker needs."
            ),
        },
    ],
    "hybrid_search": [
        {
            "id": "hyb-001",
            "title": "Dense + BM25 hybrid retrieval",
            "content": (
                "Combine dense vector similarity with BM25 lexical scoring "
                "via reciprocal rank fusion; hybrid search improves recall "
                "on exact-match / rare-term queries that dense-only retrieval misses."
            ),
        },
    ],
    "onprem_appi": [
        {
            "id": "appi-001",
            "title": "Japan on-premise APPI-safe deployment",
            "content": (
                "On-premise vector-search deployment for APPI-regulated data "
                "requires data residency within Japan, encryption at rest, "
                "and audit logging of query access; confirm data classification "
                "with the DPO before deployment."
            ),
        },
    ],
    "benchmark_interpretation": [
        {
            "id": "bench-001",
            "title": "Reading recall/throughput tradeoff curves",
            "content": (
                "Compare recall@k against queries-per-second at matched "
                "hardware; a config is only comparable to a published "
                "benchmark when index size, dimensionality, and hardware match."
            ),
        },
    ],
}

# Tier-1: live public OSS doc references (URLs only, not ingested/snapshotted —
# they drift with upstream projects and must stay current, not cached).
_TIER1_REFS: dict[str, list[str]] = {
    "index_config": ["https://github.com/facebookresearch/faiss/wiki"],
    "ann_algorithm": ["https://github.com/facebookresearch/faiss/wiki/Index-Selection"],
    "latency_tuning": ["https://github.com/facebookresearch/faiss/wiki/Faster-search"],
    "hybrid_search": ["https://qdrant.tech/documentation/concepts/hybrid-queries/"],
    "onprem_appi": ["https://www.ppc.go.jp/en/legal/"],
    "benchmark_interpretation": ["https://github.com/erikbern/ann-benchmarks"],
}


class KBRetrievalService:
    """Tier-2 curated KB retrieval with Tier-1 external doc references."""

    def __init__(
        self,
        kb: dict[str, list[dict[str, Any]]] | None = None,
        tier1_refs: dict[str, list[str]] | None = None,
        top_k: int = 3,
    ) -> None:
        self._kb = kb if kb is not None else _TIER2_KB
        self._tier1_refs = tier1_refs if tier1_refs is not None else _TIER1_REFS
        self._top_k = top_k

    def retrieve(self, query: str, domain: str) -> tuple[list[dict[str, Any]], list[str]]:
        """Return (top_k Tier-2 passages, Tier-1 external ref URLs) for a domain."""
        candidates = self._kb.get(domain, [])
        query_terms = set(query.lower().split())
        scored = []
        for entry in candidates:
            entry_terms = set((entry["title"] + " " + entry["content"]).lower().split())
            score = len(query_terms & entry_terms)
            scored.append((score, entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        top = [entry for _, entry in scored[: self._top_k]]
        refs = list(self._tier1_refs.get(domain, []))
        return top, refs
