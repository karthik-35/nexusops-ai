from unittest.mock import MagicMock, patch

from app.agents.data_agent import (
    get_delayed_orders,
    get_open_support_tickets,
)


def fake_connection(rows):
    connection = MagicMock()
    connection.execute.return_value = rows

    context = MagicMock()
    context.__enter__.return_value = connection
    return context


def test_get_delayed_orders():
    order = MagicMock()
    order.id = 1
    order.customer_name = "Alex Johnson"
    order.product = "Wireless Headphones"
    order.status = "delayed"

    with patch(
        "app.agents.data_agent.engine.connect",
        return_value=fake_connection([order]),
    ):
        result = get_delayed_orders()

    assert len(result) == 1
    assert result[0]["customer_name"] == "Alex Johnson"
    assert result[0]["status"] == "delayed"


def test_get_open_support_tickets():
    ticket = MagicMock()
    ticket.id = 1
    ticket.customer_name = "Alex Johnson"
    ticket.subject = "Order has not arrived"
    ticket.priority = "high"
    ticket.status = "open"

    with patch(
        "app.agents.data_agent.engine.connect",
        return_value=fake_connection([ticket]),
    ):
        result = get_open_support_tickets()

    assert len(result) == 1
    assert result[0]["customer_name"] == "Alex Johnson"
    assert result[0]["priority"] == "high"