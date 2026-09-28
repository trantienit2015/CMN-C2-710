"""AgentCore Platform v1.0"""

# CMN-C2-710 — Enterprise High-Performance Vector Search & Knowledge Retrieval Q&A
# Cat 2: outer AgentBaseGraph (fixed 5-node backbone) + GraphNode in the `main`
# slot wrapping the inner domain-workflow subgraph (QueryClassify → TechRetrieve
# → ConstraintEnrich → ArchitectureGenerate).
#
# GraphNode wrapper class lives HERE (same file as the outer graph), not under
# src/nodes/ — PB-6 (test_pb_invoke_order.py) auto-discovers BaseNode subclasses
# under src/nodes/ and asserts the standard S-1..S-4 lifecycle, which GraphNode
# intentionally does not run (it delegates gating to the inner subgraph).

from typing import Any, ClassVar, cast

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.nodes.input_validate_node import InputValidateNode
from src.nodes.output_validate_node import OutputValidateNode
from src.schemas.state import State


class VectorSearchAdvisoryGraphNode(GraphNode):
    """Wraps the inner vector-search advisory workflow; assigned to the `main` slot."""

    # S-1: outer main-slot wrapper — first node in outer backbone receiving caller
    # input; matches config/agent.yaml required_trust_level + sibling outer nodes
    # (InputValidateNode/OutputValidateNode).
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL
    error_strategy: ClassVar[str] = "propagate"
    propagate_hitl: ClassVar[bool] = False

    def __init__(self, llm: Any = None, top_k: int = 3):
        super().__init__()
        self._llm = llm
        self._top_k = top_k

    def get_subgraph(self) -> Any:
        from src.graph.domain_workflow_graph import VectorSearchAdvisoryWorkflowGraph

        graph = VectorSearchAdvisoryWorkflowGraph(config=self._parent_config())
        graph.compile()
        return graph

    def extract_input(self, state: AgentState) -> str:
        # S-4: runs inside GraphNode.execute() — audit the dispatch into the inner subgraph.
        emit_trace_event(
            "vector_search_advisory_dispatched",
            {"correlation_id": state.get("correlation_id")},
            state,
        )
        return cast(str, state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        # S-4: runs inside GraphNode.execute() — audit the subgraph outcome merged back out.
        emit_trace_event(
            "vector_search_advisory_completed",
            {"correlation_id": state.get("correlation_id"), "domain": sub_result.get("query_domain")},
            state,
        )
        return {
            "query_domain": sub_result.get("query_domain"),
            "retrieved_passages": sub_result.get("retrieved_passages", []),
            "external_refs": sub_result.get("external_refs", []),
            "draft_answer": sub_result.get("draft_answer"),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {"llm": self._llm, "top_k": self._top_k}


class VectorSearchAdvisoryGraph(AgentBaseGraph):
    """Outer graph for the vector-search architecture/tuning advisory agent."""

    @property
    def name(self) -> str:
        return "cmn-c2-710"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects InitializeNode + FinalizeNode

        llm = self.config.get("llm") if hasattr(self, "config") else None
        top_k = self.config.get("top_k", 3) if hasattr(self, "config") else 3

        self._nodes["pre_process"] = InputValidateNode()
        self._nodes["main"] = VectorSearchAdvisoryGraphNode(llm=llm, top_k=top_k)
        self._nodes["post_process"] = OutputValidateNode()

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.


Graph = VectorSearchAdvisoryGraph  # alias for agent.yaml module:"src.graph"
