from fastapi.testclient import TestClient

from mcp_security_gateway.config import Settings
from mcp_security_gateway.main import create_app


def client(tmp_path):
    return TestClient(create_app(Settings(database_path=tmp_path / "test.sqlite3")))


def test_summary_and_requests(tmp_path):
    c = client(tmp_path)
    assert c.get("/api/health").json() == {"status": "ok"}
    summary = c.get("/api/summary").json()
    assert summary["request_count"] == 4
    assert summary["block_count"] == 1
    assert summary["approval_count"] == 2
    requests = c.get("/api/requests").json()
    assert len(requests) == 4


def test_request_detail_and_reset(tmp_path):
    c = client(tmp_path)
    detail = c.get("/api/requests/req_secret_dump").json()
    assert detail["decision"]["decision"] == "block"
    assert detail["decision"]["requires_human_review"] is True
    assert c.get("/api/requests/missing").status_code == 404
    assert c.post("/api/demo/reset").json()["request_count"] == 4
