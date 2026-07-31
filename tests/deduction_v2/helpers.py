def branch(node_id: str, scheme_id: str) -> dict:
    revision_ids = {"101": "1001", "102": "1002"}
    return {
        "id": node_id,
        "kind": "branch-scheme",
        "branchSchemeId": scheme_id,
        "branchSchemeName": f"方案 {scheme_id}",
        "branchSchemeRevisionId": revision_ids.get(scheme_id, f"{scheme_id}-revision-1"),
        "revisionNumber": 1,
        "position": {"x": 200, "y": 200},
    }


def ready_graph() -> dict:
    return {
        "nodes": [
            {"id": "start", "kind": "start", "name": "开始节点", "position": {"x": 0, "y": 0}},
            branch("branch-1", "101"),
            branch("branch-2", "102"),
            {"id": "end", "kind": "end", "name": "结束节点", "position": {"x": 600, "y": 0}},
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "start",
                "target": "branch-1",
                "sourceHandle": "right-out",
                "targetHandle": "left-in",
            },
            {"id": "edge-2", "source": "branch-1", "target": "branch-2"},
            {
                "id": "edge-3",
                "source": "branch-2",
                "target": "end",
                "sourceHandle": "right-out",
                "targetHandle": "left-in",
            },
        ],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }
