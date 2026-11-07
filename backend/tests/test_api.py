
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "QuantTrader API running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_strategies_endpoint():
    response = client.get("/api/v1/strategies")

    assert response.status_code == 200
    assert "trend_following" in response.json()["strategies"]


def test_missing_stock_data():
    response = client.get("/api/v1/signals/trend/UNKNOWNSTOCK")

    assert response.status_code == 404



def test_invalid_symbol():
    response = client.get("/api/v1/signals/trend/RELIANCE@")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid stock symbol"


import pandas as pd


def test_market_data_endpoint(tmp_path, monkeypatch):
    from app.api import routes

    file_path = tmp_path / "RELIANCE.csv"

    pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "open": [100, 105],
        "high": [110, 115],
        "low": [95, 100],
        "close": [105, 110],
        "volume": [1000, 1200],
    }).to_csv(file_path, index=False)

    monkeypatch.setattr(routes, "DATA_DIR", tmp_path)

    response = client.get("/api/v1/market-data/RELIANCE")

    assert response.status_code == 200
    assert response.json()["symbol"] == "RELIANCE"
    assert response.json()["count"] == 2
    assert response.json()["data"][-1]["close"] == 110
