from fastapi.testclient import TestClient
from app.main import app

def test_mcp_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_mcp_context():
    client = TestClient(app)
    response = client.post("/mcp/context", json={"query": "test"})
    assert response.status_code == 200
    assert "source" in response.json()
    assert "context" in response.json()
