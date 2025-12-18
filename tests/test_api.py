import os
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'subscription_test'
os.environ['DB_USER'] = 'postgres'
os.environ.setdefault('DB_PASSWORD', 'testpass')

import pytest
import json
from app import app, run_migrations, get_db_connection

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    run_migrations()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
            cur.execute("DELETE FROM subscriptions")
            cur.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

def _create_user(email="test@example.com"):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (email) VALUES (%s) ON CONFLICT (email) DO NOTHING", (email,))
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            return cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

def test_full_subscription_lifecycle(client):
    user_id = _create_user("lifecycle@example.com")

    # Создание
    resp = client.post('/subscriptions', json={
        'user_id': user_id,
        'name': 'TestService',
        'amount': 9.99,
        'periodicity': 'monthly',
        'start_date': '2025-01-01'
    })
    if resp.status_code != 201:
        raise AssertionError(f"Expected 201 on creation, got {resp.status_code}")

    # Чтение
    resp = client.get(f'/subscriptions?user_id={user_id}')
    if resp.status_code != 200:
        raise AssertionError(f"Expected 200 on GET, got {resp.status_code}")
    subs = json.loads(resp.data)
    if len(subs) != 1:
        raise AssertionError(f"Expected 1 subscription, got {len(subs)}")

    # Обновление
    sub_id = subs[0]['id']
    resp = client.put(f'/subscriptions/{sub_id}', json={'amount': 19.99})
    if resp.status_code != 200:
        raise AssertionError(f"Expected 200 on update, got {resp.status_code}")

    # Удаление
    resp = client.delete(f'/subscriptions/{sub_id}')
    if resp.status_code != 200:
        raise AssertionError(f"Expected 200 on deletion, got {resp.status_code}")

    # Проверка удаления
    resp = client.get(f'/subscriptions?user_id={user_id}')
    subs_after = json.loads(resp.data)
    if len(subs_after) != 0:
        raise AssertionError(f"Expected 0 subscriptions after deletion, got {len(subs_after)}")