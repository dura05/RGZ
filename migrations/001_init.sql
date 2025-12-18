CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    periodicity VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    next_charge_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(20) NOT NULL,
    subscription_id INTEGER NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW()
);