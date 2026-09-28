"""TC-01..08 Framework Compliance Tests (docs/03_test_spec.md) — CMN-C2-710.

Covers the mandatory framework-compliance checks that are not already exercised
per-node in the other tests/unit/test_*.py files. See docs/03_test_spec.md for
the full TC-ID -> expected-result mapping.
"""

import inspect

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.architecture_generate_node import ArchitectureGenerateNode
from src.nodes.constraint_enrich_node import ConstraintEnrichNode
from src.nodes.input_validate_node import InputValidateNode
from src.nodes.output_validate_node import OutputValidateNode
from src.nodes.query_classify_node import QueryClassifyNode
from src.nodes.tech_retrieve_node import TechRetrieveNode
from src.schemas.state import State

ALL_NODE_CLASSES = [
    InputValidateNode,
    OutputValidateNode,
    QueryClassifyNode,
    TechRetrieveNode,
    ConstraintEnrichNode,
    ArchitectureGenerateNode,
]


def test_tc01_state_is_flat_typeddict_not_pydantic():
    # TypedDict subclasses are plain dicts at runtime — no BaseModel/dataclass machinery.
    assert not hasattr(State, "__fields__")  # a Pydantic model would have this
    assert not hasattr(State, "__dataclass_fields__")
    instance: State = {"user_input": "x", "status": AgentStatus.SUCCESS.value}
    assert isinstance(instance, dict)


def test_tc02_business_validation_returns_error_dict_not_raise():
    node = InputValidateNode()
    state = {"user_input": "", "correlation_id": "c", "execution_time": {}}

    result = node.execute(state)  # must not raise

    assert result["status"] == AgentStatus.ERROR
    assert result["error_log"]


def test_tc03_no_os_environ_credential_reads_in_node_sources():
    for cls in ALL_NODE_CLASSES:
        source = inspect.getsource(cls)
        assert "os.environ" not in source, f"{cls.__name__} must not read os.environ directly"


def test_tc04_all_nodes_subclass_function_node():
    for cls in ALL_NODE_CLASSES:
        assert issubclass(cls, FunctionNode)


def test_tc05_no_duplicate_lifecycle_events_emitted_in_execute():
    for cls in ALL_NODE_CLASSES:
        source = inspect.getsource(cls)
        for forbidden_event in ("node_start", "node_complete", "node_error"):
            assert f'"{forbidden_event}"' not in source, (
                f"{cls.__name__}.execute() must not emit backbone lifecycle event {forbidden_event!r} "
                "— BaseNode.__call__() emits these automatically"
            )


def test_tc06_function_node_subclasses_do_not_override_final_security_gate_input():
    for cls in ALL_NODE_CLASSES:
        assert "_security_gate_input" not in cls.__dict__, (
            f"{cls.__name__} must not override the @final _security_gate_input(); "
            "use _extra_security_gate_input() instead"
        )


def test_tc07_function_node_subclasses_do_not_override_final_security_gate_output():
    for cls in ALL_NODE_CLASSES:
        assert "_security_gate_output" not in cls.__dict__, (
            f"{cls.__name__} must not override the @final _security_gate_output(); "
            "use _extra_security_gate_output() instead"
        )


def test_tc08_required_trust_level_declared_and_valid_enum():
    for cls in ALL_NODE_CLASSES:
        assert "required_trust_level" in cls.__dict__, f"{cls.__name__} must declare required_trust_level explicitly"
        assert isinstance(cls.required_trust_level, TrustLevel)
        assert cls.required_trust_level in (
            TrustLevel.ANONYMOUS,
            TrustLevel.VERIFIED_EXTERNAL,
            TrustLevel.INTERNAL,
        )
