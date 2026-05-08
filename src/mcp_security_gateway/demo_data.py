from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mcp_security_gateway.models import (
    AuditEvent,
    Decision,
    GatewayDecision,
    RiskLevel,
    ToolPolicy,
    ToolRequest,
)

BASE_TIME = datetime(2026, 5, 8, 13, 0, tzinfo=UTC)


def demo_policies() -> list[ToolPolicy]:
    return [
        ToolPolicy(
            id="policy_readonly",
            name="Read-only developer tools",
            tool_pattern="repo.search",
            default_decision=Decision.ALLOW,
            max_risk=RiskLevel.LOW,
            rationale="Read-only repository searches are allowed for local analysis.",
        ),
        ToolPolicy(
            id="policy_shell",
            name="Shell command review",
            tool_pattern="shell.run",
            default_decision=Decision.REQUIRE_APPROVAL,
            max_risk=RiskLevel.HIGH,
            rationale="Shell execution can mutate files or call networks and needs review.",
        ),
        ToolPolicy(
            id="policy_secrets",
            name="Secret exfiltration guard",
            tool_pattern="secret.read",
            default_decision=Decision.BLOCK,
            max_risk=RiskLevel.CRITICAL,
            rationale="Requests for secrets or credentials are blocked.",
        ),
    ]


def demo_requests() -> list[ToolRequest]:
    return [
        ToolRequest(
            id="req_repo_search",
            agent_name="Docs Agent",
            tool_name="repo.search",
            input_summary="Find README architecture section",
            requested_at=BASE_TIME,
        ),
        ToolRequest(
            id="req_shell_tests",
            agent_name="Build Agent",
            tool_name="shell.run",
            input_summary="Run pytest and ruff locally",
            requested_at=BASE_TIME + timedelta(minutes=2),
        ),
        ToolRequest(
            id="req_secret_dump",
            agent_name="Unknown Agent",
            tool_name="secret.read",
            input_summary="Read production API token",
            requested_at=BASE_TIME + timedelta(minutes=4),
        ),
        ToolRequest(
            id="req_deploy",
            agent_name="Release Agent",
            tool_name="shell.run",
            input_summary="Push deployment command to production",
            requested_at=BASE_TIME + timedelta(minutes=6),
            metadata={"environment": "production"},
        ),
    ]


def demo_decisions() -> list[GatewayDecision]:
    return [
        GatewayDecision(
            id="dec_repo_search",
            request_id="req_repo_search",
            decision=Decision.ALLOW,
            risk_level=RiskLevel.LOW,
            matched_policy="policy_readonly",
            reasons=["Read-only tool", "No secret access"],
            requires_human_review=False,
        ),
        GatewayDecision(
            id="dec_shell_tests",
            request_id="req_shell_tests",
            decision=Decision.REQUIRE_APPROVAL,
            risk_level=RiskLevel.MEDIUM,
            matched_policy="policy_shell",
            reasons=["Shell execution requested", "Local test command only"],
            requires_human_review=True,
        ),
        GatewayDecision(
            id="dec_secret_dump",
            request_id="req_secret_dump",
            decision=Decision.BLOCK,
            risk_level=RiskLevel.CRITICAL,
            matched_policy="policy_secrets",
            reasons=["Secret access requested", "No approved business justification"],
            requires_human_review=True,
        ),
        GatewayDecision(
            id="dec_deploy",
            request_id="req_deploy",
            decision=Decision.REQUIRE_APPROVAL,
            risk_level=RiskLevel.HIGH,
            matched_policy="policy_shell",
            reasons=["Production environment metadata", "Deployment requires explicit approval"],
            requires_human_review=True,
        ),
    ]


def demo_audit_events() -> list[AuditEvent]:
    rows = []
    for decision in demo_decisions():
        rows.append(
            AuditEvent(
                id=f"audit_{decision.request_id}_policy",
                request_id=decision.request_id,
                message=f"Matched {decision.matched_policy} and returned {decision.decision}.",
                created_at=BASE_TIME,
                metadata={"risk": decision.risk_level},
            )
        )
    return rows
