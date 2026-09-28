"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict (see ADR-005 for the prohibited
# alternatives). LangGraph checkpoints use msgpack serialization, so only
# plain serializable fields are allowed. Do NOT add credentials or secrets.

from typing import NotRequired

from framework.schemas.agent_state import AgentState


# Type-check note: the wheel ships no py.typed, so mypy resolves AgentState to Any
# and reports every NotRequired below as valid-type. The fields are correct (the state
# contract requires NotRequired) -- the report is a packaging artifact, suppressed per field.
# Drop these ignores once the wheel ships py.typed.
class State(AgentState):
    """Vector-search architecture/tuning advisory agent state.

    All shared fields (user_input, status, session_id, node_history,
    error_log, hitl_*, enriched_context, validated_input, result,
    formatted_output, etc.) are inherited from AgentState.

    Agent-specific fields below are all NotRequired: they are absent from
    state until the node that produces them runs, and checkpoint resume
    must not require them to already exist.
    """

    query_text: NotRequired[str]  # type: ignore[valid-type]
    query_domain: NotRequired[str]  # type: ignore[valid-type]
    constraints: NotRequired[dict]  # type: ignore[valid-type]
    retrieved_passages: NotRequired[list[dict]]  # type: ignore[valid-type]
    external_refs: NotRequired[list[str]]  # type: ignore[valid-type]
    draft_answer: NotRequired[str]  # type: ignore[valid-type]
