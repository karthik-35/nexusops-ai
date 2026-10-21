
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def fake_database(rows):
    """Create a fake database connection."""
    connection = MagicMock()
    connection.execute.return_value = rows

    context = MagicMock()
    context.__enter__.return_value = connection
    return context


def test_get_orders():
    # Pretend PostgreSQL returns one order
    order = MagicMock()
    order.id = 1
    order.customer_id = 1
    order.product = "Wireless Headphones"
    order.amount = 79.99
    order.status = "delayed"

    with patch("app.main.engine.connect", return_value=fake_database([order])):
        response = client.get("/api/v1/orders")

    assert response.status_code == 200
    assert response.json()[0]["product"] == "Wireless Headphones"
    assert response.json()[0]["status"] == "delayed"


def test_get_customers():
    # Pretend PostgreSQL returns one customer
    customer = MagicMock()
    customer.id = 1
    customer.name = "Alex Johnson"
    customer.email = "alex@example.com"

    with patch("app.main.engine.connect", return_value=fake_database([customer])):
        response = client.get("/api/v1/customers")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Alex Johnson"


def test_get_tickets():
    # Pretend PostgreSQL returns one ticket
    ticket = MagicMock()
    ticket.id = 1
    ticket.customer_id = 1
    ticket.subject = "Order has not arrived"
    ticket.priority = "high"
    ticket.status = "open"

    with patch("app.main.engine.connect", return_value=fake_database([ticket])):
        response = client.get("/api/v1/tickets")

    assert response.status_code == 200
    assert response.json()[0]["priority"] == "high"
    assert response.json()[0]["status"] == "open"
