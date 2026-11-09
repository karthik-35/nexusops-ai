import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.agents.routing import ClassifiedRequest, plan_request
from app.agents.supervisor import build_supervisor, run_supervisor, supervisor
from app.main import app
from app.schemas import RoutingPlan

client = TestClient(app)
CASES = json.loads((Path(__file__).parent / "fixtures" / "routing.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["message"])
def test_routing_evaluation_without_model_calls(case):
    with patch("app.agents.routing.OpenAI") as llm:
        plan = plan_request(case["message"])
    assert [task.agent for task in plan.tasks] == case["agents"]
    llm.assert_not_called()


def test_ambiguous_business_request_uses_one_structured_call():
    llm = MagicMock()
    llm.responses.parse.return_value = SimpleNamespace(output_parsed=ClassifiedRequest(
        data_request="Which customers have delayed orders?", research_request=None,
        action_request=None, unsupported_request=None,
    ))
    with patch("app.agents.routing.OpenAI") as factory:
        factory.return_value.__enter__.return_value = llm
        plan = plan_request("Which customers are still waiting for their purchases?")
    assert plan.method == "model"
    assert [task.agent for task in plan.tasks] == ["data"]
    assert llm.responses.parse.call_count == 1
    assert llm.responses.parse.call_args.kwargs["store"] is False
    assert llm.responses.parse.call_args.kwargs["max_output_tokens"] == 1000
    assert factory.call_args.kwargs["max_retries"] == 0


def test_data_route_runs_existing_agent_and_records_state():
    with patch("app.agents.supervisor.ask_data_agent", return_value="One delayed order.") as data:
        result = run_supervisor("  Which orders are delayed?  ")
    assert result.status == "completed"
    assert isinstance(result.workflow_id, UUID)
    assert result.results[0].answer == "One delayed order."
    assert [event.node for event in result.events] == ["route", "execute", "finalize"]
    assert [event.sequence for event in result.events] == [1, 2, 3]
    data.assert_called_once()


def test_mixed_request_does_only_available_work_and_is_partial():
    with patch("app.agents.supervisor.ask_data_agent", return_value="Alex has a delayed order.") as data:
        result = run_supervisor(
            "Find customers with delayed orders, check the refund policy, and prepare apology emails."
        )
    assert result.status == "partial"
    assert [(r.agent, r.status) for r in result.results] == [
        ("data", "completed"), ("research", "unavailable"), ("action", "unavailable")
    ]
    assert "not implemented" in result.answer
    assert "refund" not in data.call_args.args[0]
    assert "email" not in data.call_args.args[0]
    assert len(result.events) == 5


@pytest.mark.parametrize("message", [
    "What is our refund policy for delayed orders?", "Send an apology email.", "Tell me a joke."
])
def test_unavailable_or_unsupported_requests_never_call_data(message):
    with patch("app.agents.supervisor.ask_data_agent") as data:
        result = run_supervisor(message)
    assert result.status == "unsupported"
    data.assert_not_called()


def test_agent_failure_is_sanitized_in_response_and_logs(caplog):
    with patch("app.agents.supervisor.ask_data_agent", side_effect=RuntimeError("secret-canary")):
        result = run_supervisor("Which orders are delayed?")
    assert result.status == "failed"
    assert result.results[0].error_code == "agent_failed"
    assert "secret-canary" not in result.model_dump_json() + caplog.text
    assert str(result.workflow_id) in caplog.text


@pytest.mark.parametrize("answer", [None, "", "  "])
def test_empty_agent_results_fail(answer):
    with patch("app.agents.supervisor.ask_data_agent", return_value=answer):
        assert run_supervisor("Which orders are delayed?").status == "failed"


def test_planner_failure_stops_before_any_execution(caplog):
    handler = Mock()
    graph = build_supervisor({"data": handler}, planner=Mock(side_effect=RuntimeError("secret-canary")))
    result = graph.invoke({"message": "Find customers."})
    assert result["status"] == "failed"
    assert result["results"] == []
    assert [e.node for e in result["events"]] == ["route", "finalize"]
    handler.assert_not_called()
    assert "secret-canary" not in str(result) + caplog.text


def test_model_refusal_is_a_safe_failure():
    llm = MagicMock()
    llm.responses.parse.return_value = SimpleNamespace(output_parsed=None)
    with patch("app.agents.routing.OpenAI") as factory:
        factory.return_value.__enter__.return_value = llm
        result = run_supervisor("Investigate our customers.")
    assert result.status == "failed"
    assert result.results == []


def test_missing_key_has_safe_failure_and_no_sdk_call(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with patch("app.agents.routing.OpenAI") as factory:
        result = run_supervisor("Investigate our customers.")
    assert result.status == "failed"
    factory.assert_not_called()


def test_model_can_report_supported_and_unsupported_parts():
    llm = MagicMock()
    llm.responses.parse.return_value = SimpleNamespace(output_parsed=ClassifiedRequest(
        data_request="List delayed orders.", research_request=None, action_request=None,
        unsupported_request="Revenue is not available through the current data tools.",
    ))
    with (
        patch("app.agents.routing.OpenAI") as factory,
        patch("app.agents.supervisor.ask_data_agent", return_value="One delayed order."),
    ):
        factory.return_value.__enter__.return_value = llm
        result = run_supervisor("Show delayed orders and total revenue.")
    assert result.status == "partial"
    assert "Revenue is not available" in result.answer


def test_registry_supports_shared_results_without_changing_graph():
    # Fake handlers exercise extension contracts; they are not production agents.
    seen = []
    def handler(task, evidence):
        seen.append((task.agent, [r.agent for r in evidence]))
        return f"Synthetic {task.agent} result"

    graph = build_supervisor({"data": handler, "research": handler, "action": handler})
    result = graph.invoke({"message": "Find delayed orders, check policy, prepare apology emails."})
    assert result["status"] == "completed"
    assert seen == [("data", []), ("research", ["data"]), ("action", ["data", "research"])]
    assert result["next_task"] == 3


def test_dependency_failure_blocks_action_and_preserves_independent_results():
    action = Mock()
    graph = build_supervisor({
        "data": Mock(side_effect=RuntimeError("database offline")),
        "research": Mock(return_value="Synthetic policy evidence."), "action": action,
    })
    result = graph.invoke({"message": "Find delayed orders, check policy, prepare apology emails."})
    assert result["status"] == "partial"
    assert [r.status for r in result["results"]] == ["failed", "completed", "blocked"]
    action.assert_not_called()


@pytest.mark.parametrize("tasks", [
    [{"agent": "shell", "request": "execute"}],
    [{"agent": "data", "request": "read", "depends_on": ["data"]}],
    [{"agent": "data", "request": "read"}] * 2,
    [{"agent": "data", "request": "read"}] * 4,
])
def test_invalid_plans_are_rejected(tasks):
    with pytest.raises(ValidationError):
        RoutingPlan(method="model", explanation="Invalid plan", tasks=tasks)


def test_graph_state_does_not_leak_across_requests():
    with patch("app.agents.supervisor.ask_data_agent", return_value="private-test-record"):
        first = supervisor.invoke({"message": "Which orders are delayed?"})
        second = supervisor.invoke({"message": "Hello"})
    assert first["workflow_id"] != second["workflow_id"]
    assert second["results"] == []
    assert "private-test-record" not in second["answer"]


@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": " \n\t"},
                                     {"message": "x" * 2001}, {"message": 123},
                                     {"message": "Hi", "agent": "action"}])
def test_supervisor_api_validates_request(body):
    assert client.post("/api/v1/agents/supervisor/chat", json=body).status_code == 422


def test_supervisor_api_returns_structured_workflow():
    with patch("app.agents.supervisor.ask_data_agent", return_value="One delayed order."):
        response = client.post("/api/v1/agents/supervisor/chat", json={"message": "List delayed orders."})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["results"][0]["agent"] == "data"
    assert response.json()["events"][-1]["node"] == "finalize"


def test_supervisor_api_returns_trace_on_upstream_failure():
    with patch("app.agents.supervisor.ask_data_agent", side_effect=RuntimeError("secret-canary")):
        response = client.post("/api/v1/agents/supervisor/chat", json={"message": "List delayed orders."})
    assert response.status_code == 502
    assert response.json()["status"] == "failed"
    assert "secret-canary" not in response.text


def test_unexpected_graph_failure_is_sanitized():
    with patch("app.api.supervisor.run_supervisor", side_effect=RuntimeError("secret-canary")):
        response = client.post("/api/v1/agents/supervisor/chat", json={"message": "Hi"})
    assert response.status_code == 502
    assert response.json() == {"detail": "Supervisor request failed"}


def test_full_api_graph_agent_tool_path_with_mocked_external_boundaries():
    llm = MagicMock()
    llm.responses.create.side_effect = [
        SimpleNamespace(id="r1", output_text="", output=[SimpleNamespace(
            type="function_call", name="get_delayed_orders", arguments="{}", call_id="c1"
        )]),
        SimpleNamespace(id="r2", output=[], output_text="Alex Johnson has a delayed order."),
    ]
    connection = MagicMock()
    connection.execute.return_value = [SimpleNamespace(
        id=1, customer_name="Alex Johnson", product="Wireless Headphones", status="delayed"
    )]
    with (
        patch("app.agents.data_agent_service.OpenAI", return_value=llm),
        patch("app.agents.data_agent.engine.connect") as connect,
    ):
        connect.return_value.__enter__.return_value = connection
        response = client.post("/api/v1/agents/supervisor/chat", json={"message": "Which orders are delayed?"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "Alex Johnson" in response.json()["answer"]
    connection.execute.assert_called_once()
    assert "WHERE orders.status = 'delayed'" in str(connection.execute.call_args.args[0])
    outputs = llm.responses.create.call_args.kwargs["input"]
    assert json.loads(outputs[0]["output"])[0]["order_id"] == 1


def test_direct_graph_invalid_message_is_rejected():
    with pytest.raises(ValidationError):
        supervisor.invoke({"message": "   "})


def test_schema_documents_supervisor_and_preserves_existing_data_endpoint():
    paths = app.openapi()["paths"]
    assert "/api/v1/agents/data/chat" in paths
    assert "/api/v1/agents/supervisor/chat" in paths
    schema = paths["/api/v1/agents/supervisor/chat"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("SupervisorResponse")
