CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    periodicity VARCHAR(20) NOT NULL CHECK (periodicity IN ('monthly', 'yearly')),
    start_date DATE NOT NULL,
    next_charge_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);