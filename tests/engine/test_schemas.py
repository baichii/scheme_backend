import pytest
from pydantic import ValidationError

from backend.common.enums import EngineRequestType
from backend.engine.schemas import (
    EngineCreateRequest,
    EngineQueryRequest,
    EngineStopRequest,
    EngineTaskDefinition,
)


def test_request_type_values_match_matrix_protocol():
    assert EngineRequestType.CREATE == 1
    assert EngineRequestType.UPDATE == 2
    assert EngineRequestType.QUERY == 3
    assert EngineRequestType.STOP == 4


def test_create_request_serializes_complete_matrix_payload():
    request = EngineCreateRequest(
        name="create example",
        body=[
            EngineTaskDefinition(
                id="task-1",
                envConfig={
                    "envType": "pysim",
                    "envInstanceConfig": {"ip": "127.0.0.1", "port": 10001},
                },
                agentConfig={
                    "deduceId": "deduction-1",
                    "taskId": "task-1",
                    "agentInstanceConfig": {"new_parameter": [1, 2]},
                },
                bizValue={"customBizField": "preserved"},
                customTaskField={"enabled": True},
            )
        ],
    )

    wire = request.model_dump(mode="json", by_alias=True)

    assert wire["requestType"] == 1
    assert wire["body"][0] == {
        "isRoot": True,
        "isBox": False,
        "id": "task-1",
        "envConfig": {
            "envType": "pysim",
            "envInstanceConfig": {"ip": "127.0.0.1", "port": 10001},
        },
        "agentLoad": "",
        "agentUrl": "",
        "agentConfig": {
            "deduceId": "deduction-1",
            "taskId": "task-1",
            "taskName": "",
            "agentInstanceConfig": {"new_parameter": [1, 2]},
        },
        "bizValue": {
            "dispatchQueue": {"name": "", "durable": True, "needToDeclare": True},
            "simTimeQueue": {"name": "", "durable": True, "needToDeclare": True},
            "deduceID": None,
            "deduceTaskID": None,
            "customBizField": "preserved",
        },
        "pin": {"activate": None, "end": None, "delay": None, "cancel": None},
        "agentRequire": {},
        "father": None,
        "customTaskField": {"enabled": True},
    }
    assert "agent_requires" not in wire["body"][0]


def test_query_and_stop_requests_use_matrix_aliases_and_defaults():
    query_wire = EngineQueryRequest(body=["task-1"]).model_dump(mode="json", by_alias=True)
    stop_wire = EngineStopRequest(body=["task-1"]).model_dump(mode="json", by_alias=True)

    assert query_wire == {"name": "query", "requestType": 3, "body": ["task-1"]}
    assert stop_wire == {
        "name": "stop",
        "requestType": 4,
        "body": ["task-1"],
        "dispatchQueue": {"name": "info", "durable": True},
    }


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (EngineCreateRequest, {"requestType": 3}),
        (EngineQueryRequest, {"requestType": 4}),
        (EngineStopRequest, {"requestType": 2}),
    ],
)
def test_request_models_reject_wrong_request_type(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_task_definition_requires_non_empty_id():
    with pytest.raises(ValidationError):
        EngineTaskDefinition.model_validate({})
    with pytest.raises(ValidationError):
        EngineTaskDefinition(id="")
