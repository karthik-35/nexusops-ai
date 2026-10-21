from sqlalchemy import text
from app.database import engine


def get_delayed_orders():
    query = text("""
        SELECT
            orders.id,
            customers.name AS customer_name,
            orders.product,
            orders.status
        FROM orders
        JOIN customers
            ON orders.customer_id = customers.id
        WHERE orders.status = 'delayed'
        ORDER BY orders.id
    """)

    with engine.connect() as connection:
        result = connection.execute(query)

        return [
            {
                "order_id": row.id,
                "customer_name": row.customer_name,
                "product": row.product,
                "status": row.status,
            }
            for row in result
        ]

def get_open_support_tickets():
    query = text("""
        SELECT
            support_tickets.id,
            customers.name AS customer_name,
            support_tickets.subject,
            support_tickets.priority,
            support_tickets.status
        FROM support_tickets
        JOIN customers
            ON support_tickets.customer_id = customers.id
        WHERE support_tickets.status = 'open'
        ORDER BY support_tickets.id
    """)

    with engine.connect() as connection:
        result = connection.execute(query)

        return [
            {
                "ticket_id": row.id,
                "customer_name": row.customer_name,
                "subject": row.subject,
                "priority": row.priority,
                "status": row.status,
            }
            for row in result
        ]