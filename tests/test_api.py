import os
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'subscription_test'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'testpass'

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
    resp = client.post('/subscriptions', json={...})
    assert resp.status_code == 201

    # Чтение
    resp = client.get(f'/subscriptions?user_id={user_id}')
    assert resp.status_code == 200
    assert len(json.loads(resp.data)) == 1

    # Обновление
    sub_id = json.loads(resp.data)[0]['id']
    resp = client.put(f'/subscriptions/{sub_id}', json={'amount': 19.99})
    assert resp.status_code == 200

    # Удаление
    resp = client.delete(f'/subscriptions/{sub_id}')
    assert resp.status_code == 200

    # Проверка удаления
    resp = client.get(f'/subscriptions?user_id={user_id}')
    assert len(json.loads(resp.data)) == 0