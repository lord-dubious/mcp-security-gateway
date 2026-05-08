from fastapi.testclient import TestClient

from mcp_security_gateway.config import Settings
from mcp_security_gateway.main import create_app


def test_dashboard_assets(tmp_path):
    c = TestClient(create_app(Settings(database_path=tmp_path / "test.sqlite3")))
    shell = c.get("/").text
    assert "MCP Security Gateway" in shell
    assert "Evaluate a tool request" in shell
    css = c.get("/static/styles.css")
    assert css.status_code == 200
    assert "evaluate-panel" in css.text
    app_js = c.get("/static/app.js").text
    assert "/api/summary" in app_js
    assert "/api/requests/evaluate" in app_js
    assert "SAMPLE_REQUEST" in app_js
