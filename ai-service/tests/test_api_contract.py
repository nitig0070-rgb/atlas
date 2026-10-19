from fastapi.testclient import TestClient

from app import main


def test_health_endpoint_returns_readiness_payload():
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert "mysql" in response.json()


def test_chat_requires_api_key(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "test-key")
    response = TestClient(main.app).post("/chat", json={"client_id": "C-01", "message": "hello"})
    assert response.status_code == 401


def test_chat_rejects_invalid_api_key(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "test-key")
    response = TestClient(main.app).post("/chat", headers={"X-API-Key": "wrong"},
                                        json={"client_id": "C-01", "message": "hello"})
    assert response.status_code == 401


def test_chat_rejects_invalid_request_shape(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "test-key")
    response = TestClient(main.app).post("/chat", headers={"X-API-Key": "test-key"}, json={"client_id": "bad"})
    assert response.status_code == 422


def test_ingest_requires_typed_report_id(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "test-key")
    response = TestClient(main.app).post("/ingest", headers={"X-API-Key": "test-key"}, json={"report_id": "../../clients"})
    assert response.status_code == 422


def test_chat_rejects_unknown_client(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "test-key")
    monkeypatch.setattr(main, "entitled_reports", lambda _client_id: None)
    response = TestClient(main.app).post("/chat", headers={"X-API-Key": "test-key"},
                                        json={"client_id": "C-99", "message": "hello"})
    assert response.status_code == 404
