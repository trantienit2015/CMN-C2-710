"""AgentCore Platform v1.0"""

# Inner graph for the CMN-C2-710 vector-search advisory workflow.
# Instantiated by VectorSearchAdvisoryGraphNode.get_subgraph() in graph.py.
# Receives only the string user_input (JSON envelope) + ctx — NOT the outer
# state. Pipeline: START → query_classify → tech_retrieve → constraint_enrich
# → architecture_generate → END.

from typing import Any
from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from src.nodes.architecture_generate_node import ArchitectureGenerateNode
from src.nodes.constraint_enrich_node import ConstraintEnrichNode
from src.nodes.query_classify_node import QueryClassifyNode
from src.nodes.tech_retrieve_node import TechRetrieveNode
from src.schemas.state import State
from src.services.kb_retrieval_service import KBRetrievalService


class VectorSearchAdvisoryWorkflowGraph(BaseGraph):
    """Inner graph: classify → retrieve → enrich → generate."""

    @property
    def name(self) -> str:
        return "vector_search_advisory_workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        pass  # no mandatory config keys; llm/top_k are optional overrides

    def register_nodes(self) -> None:
        # No super() call — BaseGraph.register_nodes() is abstract.
        llm = self.config.get("llm") if hasattr(self, "config") else None
        top_k = self.config.get("top_k", 3) if hasattr(self, "config") else 3

        self._nodes["query_classify"] = QueryClassifyNode()
        self._nodes["tech_retrieve"] = TechRetrieveNode(kb_service=KBRetrievalService(top_k=top_k))
        self._nodes["constraint_enrich"] = ConstraintEnrichNode()
        self._nodes["architecture_generate"] = ArchitectureGenerateNode(llm=llm)

    def add_edges(self) -> None:
        self._sg.add_edge(START, "query_classify")
        self._sg.add_edge("query_classify", "tech_retrieve")
        self._sg.add_edge("tech_retrieve", "constraint_enrich")
        self._sg.add_edge("constraint_enrich", "architecture_generate")
        self._sg.add_edge("architecture_generate", END)

    def route(self, state: AgentState) -> str:
        # Required by BaseGraph ABC; linear topology never triggers this.
        return END if state.get("status") == AgentStatus.ERROR.value else "architecture_generate"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "query_domain": state.get("query_domain"),
            "retrieved_passages": state.get("retrieved_passages", []),
            "external_refs": state.get("external_refs", []),
            "draft_answer": state.get("draft_answer"),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
