from fastapi.testclient import TestClient

from mcp_security_gateway.config import Settings
from mcp_security_gateway.main import create_app


def test_dashboard_assets(tmp_path):
    c = TestClient(create_app(Settings(database_path=tmp_path / "test.sqlite3")))
    assert "MCP Security Gateway" in c.get("/").text
    assert c.get("/static/styles.css").status_code == 200
    assert "/api/summary" in c.get("/static/app.js").text
