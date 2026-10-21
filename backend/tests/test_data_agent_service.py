from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agents.data_agent_service import ask_data_agent


def test_agent_executes_both_tools():
    first_response = SimpleNamespace(
        id="response_123",
        output=[
            SimpleNamespace(
                type="function_call",
                name="get_delayed_orders",
                call_id="call_1",
            ),
            SimpleNamespace(
                type="function_call",
                name="get_open_support_tickets",
                call_id="call_2",
            ),
        ],
        output_text="",
    )

    final_response = SimpleNamespace(
        id="response_456",
        output=[],
        output_text="Alex Johnson has both a delayed order and an open ticket.",
    )

    mock_client = MagicMock()
    mock_client.responses.create.side_effect = [
        first_response,
        final_response,
    ]

    with (
        patch(
            "app.agents.data_agent_service.OpenAI",
            return_value=mock_client,
        ),
        patch(
            "app.agents.data_agent_service.get_delayed_orders",
            return_value=[{"order_id": 1}],
        ) as mock_orders,
        patch(
            "app.agents.data_agent_service.get_open_support_tickets",
            return_value=[{"ticket_id": 1}],
        ) as mock_tickets,
    ):
        answer = ask_data_agent(
            "Which customers have delayed orders and open support tickets?"
        )

    mock_orders.assert_called_once()
    mock_tickets.assert_called_once()

    assert "Alex Johnson" in answer

    assert mock_client.responses.create.call_count == 2

    tool_outputs = mock_client.responses.create.call_args.kwargs["input"]

    assert len(tool_outputs) == 2
    assert {item["call_id"] for item in tool_outputs} == {
        "call_1",
        "call_2",
    }


def test_agent_handles_multiple_rounds():
    first_response = SimpleNamespace(
        id="response_1",
        output=[
            SimpleNamespace(
                type="function_call",
                name="get_delayed_orders",
                call_id="call_1",
            )
        ],
        output_text="",
    )

    second_response = SimpleNamespace(
        id="response_2",
        output=[
            SimpleNamespace(
                type="function_call",
                name="get_open_support_tickets",
                call_id="call_2",
            )
        ],
        output_text="",
    )

    final_response = SimpleNamespace(
        id="response_3",
        output=[],
        output_text="Alex Johnson has a delayed order and an open ticket.",
    )

    mock_client = MagicMock()
    mock_client.responses.create.side_effect = [
        first_response,
        second_response,
        final_response,
    ]

    with (
        patch(
            "app.agents.data_agent_service.OpenAI",
            return_value=mock_client,
        ),
        patch(
            "app.agents.data_agent_service.get_delayed_orders",
            return_value=[{"order_id": 1}],
        ) as mock_orders,
        patch(
            "app.agents.data_agent_service.get_open_support_tickets",
            return_value=[{"ticket_id": 1}],
        ) as mock_tickets,
    ):
        answer = ask_data_agent(
            "Which customers have delayed orders and open support tickets?"
        )

    mock_orders.assert_called_once()
    mock_tickets.assert_called_once()

    assert mock_client.responses.create.call_count == 3
    assert "Alex Johnson" in answer

    calls = mock_client.responses.create.call_args_list

    assert calls[1].kwargs["previous_response_id"] == "response_1"
    assert calls[2].kwargs["previous_response_id"] == "response_2"