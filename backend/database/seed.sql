
-- Add a fictional customer
INSERT INTO customers (name, email)
VALUES ('Alex Johnson', 'alex@example.com')
ON CONFLICT (email) DO NOTHING;

-- Add an order for Alex
INSERT INTO orders (customer_id, product, amount, status)
SELECT id, 'Wireless Headphones', 79.99, 'delayed'
FROM customers
WHERE email = 'alex@example.com'
AND NOT EXISTS (
    SELECT 1 FROM orders
    WHERE customer_id = customers.id
    AND product = 'Wireless Headphones'
);

-- Add a support ticket for Alex
INSERT INTO support_tickets (
    customer_id, subject, priority, status
)
SELECT id, 'Order has not arrived', 'high', 'open'
FROM customers
WHERE email = 'alex@example.com'
AND NOT EXISTS (
    SELECT 1 FROM support_tickets
    WHERE customer_id = customers.id
    AND subject = 'Order has not arrived'
);
