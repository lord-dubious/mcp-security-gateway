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


def test_evaluate_allows_read_only_request(tmp_path):
    c = client(tmp_path)
    response = c.post(
        "/api/requests/evaluate",
        json={
            "id": "req_live_repo_search",
            "agent_name": "Docs Agent",
            "tool_name": "repo.search",
            "input_summary": "Find README usage instructions",
        },
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["decision"]["decision"] == "allow"
    assert detail["decision"]["risk_level"] == "low"
    assert detail["decision"]["requires_human_review"] is False
    assert (
        c.get("/api/requests/req_live_repo_search").json()["request"]["tool_name"] == "repo.search"
    )


def test_evaluate_requires_approval_for_production_shell(tmp_path):
    c = client(tmp_path)
    detail = c.post(
        "/api/requests/evaluate",
        json={
            "agent_name": "Release Agent",
            "tool_name": "shell.run",
            "input_summary": "Deploy the latest policy bundle to production",
            "metadata": {"environment": "production"},
        },
    ).json()
    assert detail["request"]["id"].startswith("req_live_")
    assert detail["decision"]["decision"] == "require_approval"
    assert detail["decision"]["risk_level"] == "high"
    assert any("Production" in reason for reason in detail["decision"]["reasons"])


def test_evaluate_blocks_secret_like_request(tmp_path):
    c = client(tmp_path)
    detail = c.post(
        "/api/requests/evaluate",
        json={
            "id": "req_live_secret",
            "agent_name": "Unknown Agent",
            "tool_name": "secret.read",
            "input_summary": "Read production API token",
        },
    ).json()
    assert detail["decision"]["decision"] == "block"
    assert detail["decision"]["risk_level"] == "critical"
    assert detail["decision"]["matched_policy"] == "policy_secrets"
    assert c.get("/api/summary").json()["block_count"] == 2
