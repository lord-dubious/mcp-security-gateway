from mcp_security_gateway.models import Decision, ToolRequestEvaluation
from mcp_security_gateway.repository import GatewayRepository


def test_seed_and_detail(tmp_path):
    repo = GatewayRepository(tmp_path / "test.sqlite3")
    repo.ensure_seeded()
    repo.ensure_seeded()
    assert repo.summary().high_risk_count == 2
    detail = repo.detail("req_deploy")
    assert detail is not None
    assert detail.decision.risk_level == "high"
    assert detail.audit_events


def test_evaluate_request_replaces_same_request_id(tmp_path):
    repo = GatewayRepository(tmp_path / "test.sqlite3")
    repo.ensure_seeded()
    first = repo.evaluate_request(
        ToolRequestEvaluation(
            id="req_repeat",
            agent_name="Builder",
            tool_name="repo.search",
            input_summary="Search policy docs",
        )
    )
    second = repo.evaluate_request(
        ToolRequestEvaluation(
            id="req_repeat",
            agent_name="Builder",
            tool_name="secret.read",
            input_summary="Read API token",
        )
    )
    assert first.decision.decision == Decision.ALLOW
    assert second.decision.decision == Decision.BLOCK
    assert repo.detail("req_repeat") is not None
    assert repo.summary().request_count == 5
