"""TC-06/TC-07 Framework Compliance Tests (docs/03_test_spec.md) — CMN-C2-710.

Dedicated exact-name file required by gate-scaffold-integrity for stg-complete
repos (scaffold REQUIRED_STG_COMPLETE). Covers the S-2/S-3 @final non-bypass
checks; TC-01..05/08 remain in tests/unit/test_framework_compliance.py.
"""

from framework.nodes.function_node import FunctionNode

from src.nodes.architecture_generate_node import ArchitectureGenerateNode
from src.nodes.constraint_enrich_node import ConstraintEnrichNode
from src.nodes.input_validate_node import InputValidateNode
from src.nodes.output_validate_node import OutputValidateNode
from src.nodes.query_classify_node import QueryClassifyNode
from src.nodes.tech_retrieve_node import TechRetrieveNode

ALL_NODE_CLASSES = [
    InputValidateNode,
    OutputValidateNode,
    QueryClassifyNode,
    TechRetrieveNode,
    ConstraintEnrichNode,
    ArchitectureGenerateNode,
]


def test_tc06_function_node_security_gate_input_is_final_and_not_overridden():
    # @final on the base method — overriding it in a subclass would raise TypeError
    # at class-definition time (mypy/runtime @final contract on FunctionNode).
    assert hasattr(FunctionNode, "_security_gate_input")
    for cls in ALL_NODE_CLASSES:
        assert issubclass(cls, FunctionNode)
        assert "_security_gate_input" not in cls.__dict__, (
            f"{cls.__name__} must not override the @final _security_gate_input(); "
            "use _extra_security_gate_input() instead"
        )


def test_tc07_function_node_security_gate_output_is_final_and_not_overridden():
    assert hasattr(FunctionNode, "_security_gate_output")
    for cls in ALL_NODE_CLASSES:
        assert issubclass(cls, FunctionNode)
        assert "_security_gate_output" not in cls.__dict__, (
            f"{cls.__name__} must not override the @final _security_gate_output(); "
            "use _extra_security_gate_output() instead"
        )
