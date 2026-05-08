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
