# tests/test_api.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, run_migrations  # ← импортируем функцию миграции

# Применяем миграции один раз перед всеми тестами
@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    run_migrations()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

def test_create_subscription(client):
    response = client.post(
        '/subscriptions',
        json={
            "user_id": 1,
            "name": "TestSub",
            "amount": 9.99,
            "periodicity": "monthly",
            "start_date": "2025-12-18",
            "next_charge_date": "2025-12-18"
        }
    )
    assert response.status_code == 201
    assert "id" in response.get_json()