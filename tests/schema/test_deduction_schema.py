import pytest
from pydantic import ValidationError

from backend.app.deduction.schema.deduction import (
    CreateDeductionParam,
    DeductionGraph,
    UpdateDeductionParam,
    get_default_deduction_graph,
    validate_ready_deduction_graph,
)
from tests.deduction_v2.helpers import ready_graph


def test_create_schema_trims_fields_and_uses_frontend_names() -> None:
    request = CreateDeductionParam.model_validate(
        {"name": "  联合推演  ", "description": "  描述  ", "scenarioTypeKey": " zc "}
    )

    assert request.model_dump(by_alias=True) == {
        "name": "联合推演",
        "description": "描述",
        "scenarioTypeKey": "zc",
    }


def test_default_graph_contains_one_start_and_end() -> None:
    graph = get_default_deduction_graph()
    assert [(node.id, node.kind) for node in graph.nodes] == [("start", "start"), ("end", "end")]
    assert graph.edges == []


def test_ready_graph_requires_two_connected_branches() -> None:
    with pytest.raises(ValueError, match="至少需要两个分支方案"):
        validate_ready_deduction_graph(get_default_deduction_graph())


def test_update_rejects_explicit_null() -> None:
    with pytest.raises(ValidationError):
        UpdateDeductionParam.model_validate({"name": None})


def test_graph_requires_unique_terminal_nodes() -> None:
    with pytest.raises(ValidationError, match="唯一的开始节点和结束节点"):
        DeductionGraph.model_validate({"nodes": [], "edges": []})


def test_branch_nodes_require_an_exact_revision() -> None:
    graph = ready_graph()
    branch = next(node for node in graph["nodes"] if node["kind"] == "branch-scheme")
    branch.pop("branchSchemeRevisionId")

    with pytest.raises(ValidationError, match="branchSchemeRevisionId"):
        DeductionGraph.model_validate(graph)
