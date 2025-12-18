# tests/test_api.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

def test_create_subscription(client):
    response = client.post(
        '/subscriptions',
        json={
            "user_id": 1,
            "name": "Netflix",
            "amount": 15.99,
            "periodicity": "monthly",
            "start_date": "2025-12-18",
            "next_charge_date": "2025-12-18"
        }
    )
    assert response.status_code == 201
    data = response.get_json()
    assert "id" in data