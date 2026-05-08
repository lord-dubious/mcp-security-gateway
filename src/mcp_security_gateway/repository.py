from __future__ import annotations

import fnmatch
import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from mcp_security_gateway import demo_data
from mcp_security_gateway.models import (
    AuditEvent,
    Decision,
    GatewayDecision,
    GatewayDetail,
    GatewaySummary,
    RiskLevel,
    ToolPolicy,
    ToolRequest,
    ToolRequestEvaluation,
    utcnow,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class GatewayRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            for table in ["policies", "requests", "decisions", "audit_events"]:
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
                )

    def reset_demo_data(self) -> None:
        self.initialize()
        with self._connect() as conn:
            for table in ["audit_events", "decisions", "requests", "policies"]:
                conn.execute(f"DELETE FROM {table}")
            self._insert_many(conn, "policies", demo_data.demo_policies())
            self._insert_many(conn, "requests", demo_data.demo_requests())
            self._insert_many(conn, "decisions", demo_data.demo_decisions())
            self._insert_many(conn, "audit_events", demo_data.demo_audit_events())

    def ensure_seeded(self) -> None:
        self.initialize()
        with self._connect() as conn:
            if conn.execute("SELECT COUNT(*) FROM policies").fetchone()[0] == 0:
                self.reset_demo_data()

    def list_policies(self) -> list[ToolPolicy]:
        return self._load_all("policies", ToolPolicy)

    def list_requests(self) -> list[ToolRequest]:
        return sorted(self._load_all("requests", ToolRequest), key=lambda row: row.requested_at)

    def detail(self, request_id: str) -> GatewayDetail | None:
        request = self._load_one("requests", request_id, ToolRequest)
        if request is None:
            return None
        decisions = [
            d for d in self._load_all("decisions", GatewayDecision) if d.request_id == request_id
        ]
        if not decisions:
            return None
        events = [
            e for e in self._load_all("audit_events", AuditEvent) if e.request_id == request_id
        ]
        return GatewayDetail(request=request, decision=decisions[0], audit_events=events)

    def evaluate_request(self, payload: ToolRequestEvaluation) -> GatewayDetail:
        self.initialize()
        request = ToolRequest(
            id=payload.id or self._next_request_id(),
            agent_name=payload.agent_name,
            tool_name=payload.tool_name,
            input_summary=payload.input_summary,
            requested_at=utcnow(),
            metadata=payload.metadata,
        )
        decision = self._evaluate(request)
        events = self._audit_events_for(request, decision)

        with self._connect() as conn:
            conn.execute(
                "DELETE FROM audit_events WHERE json_extract(payload, '$.request_id') = ?",
                (request.id,),
            )
            conn.execute(
                "DELETE FROM decisions WHERE json_extract(payload, '$.request_id') = ?",
                (request.id,),
            )
            conn.execute(
                "INSERT OR REPLACE INTO requests (id, payload) VALUES (?, ?)",
                (request.id, request.model_dump_json()),
            )
            self._insert_many(conn, "decisions", [decision])
            self._insert_many(conn, "audit_events", events)

        return GatewayDetail(request=request, decision=decision, audit_events=events)

    def summary(self) -> GatewaySummary:
        decisions = self._load_all("decisions", GatewayDecision)
        return GatewaySummary(
            request_count=len(decisions),
            allow_count=sum(d.decision == Decision.ALLOW for d in decisions),
            approval_count=sum(d.decision == Decision.REQUIRE_APPROVAL for d in decisions),
            block_count=sum(d.decision == Decision.BLOCK for d in decisions),
            high_risk_count=sum(
                d.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} for d in decisions
            ),
        )

    def _insert_many(self, conn: sqlite3.Connection, table: str, rows: Sequence[BaseModel]) -> None:
        conn.executemany(
            f"INSERT INTO {table} (id, payload) VALUES (?, ?)",
            [(str(row.model_dump()["id"]), row.model_dump_json()) for row in rows],
        )

    def _next_request_id(self) -> str:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        return f"req_live_{count + 1:03d}"

    def _evaluate(self, request: ToolRequest) -> GatewayDecision:
        policy = self._match_policy(request.tool_name)
        decision = policy.default_decision if policy else Decision.REQUIRE_APPROVAL
        risk = policy.max_risk if policy else RiskLevel.MEDIUM
        matched_policy = policy.id if policy else "policy_unmatched_tool"
        reasons = [policy.rationale if policy else "No exact policy matched this tool name."]

        lowered_input = request.input_summary.lower()
        lowered_tool = request.tool_name.lower()
        metadata_text = json.dumps(request.metadata, sort_keys=True).lower()
        sensitive_markers = {"secret", "token", "credential", "password", "api key", "private key"}
        destructive_markers = {"delete", "rm ", "drop", "deploy", "production", "push", "write"}

        if any(
            marker in lowered_input or marker in lowered_tool or marker in metadata_text
            for marker in sensitive_markers
        ):
            decision = Decision.BLOCK
            risk = RiskLevel.CRITICAL
            matched_policy = "policy_secrets"
            reasons.append("Secret or credential access detected in the request boundary.")

        environment = str(request.metadata.get("environment", "")).lower()
        if environment in {"prod", "production"}:
            if decision != Decision.BLOCK:
                decision = Decision.REQUIRE_APPROVAL
                risk = RiskLevel.HIGH
            reasons.append("Production environment metadata requires human review.")

        if request.tool_name.startswith("shell.") and any(
            marker in lowered_input for marker in destructive_markers
        ):
            if decision != Decision.BLOCK:
                decision = Decision.REQUIRE_APPROVAL
                risk = RiskLevel.HIGH
            reasons.append(
                "Shell command contains mutation, deployment, or destructive-operation language."
            )

        if decision == Decision.ALLOW:
            reasons.append("Allowed because matched policy is low-risk and read-only.")
        elif decision == Decision.REQUIRE_APPROVAL:
            reasons.append("Human approval required before execution.")
        else:
            reasons.append("Execution blocked before tool invocation.")

        return GatewayDecision(
            id=f"dec_{request.id}",
            request_id=request.id,
            decision=decision,
            risk_level=risk,
            matched_policy=matched_policy,
            reasons=list(dict.fromkeys(reasons)),
            requires_human_review=decision != Decision.ALLOW,
        )

    def _match_policy(self, tool_name: str) -> ToolPolicy | None:
        for policy in self.list_policies():
            if fnmatch.fnmatch(tool_name, policy.tool_pattern) or tool_name == policy.tool_pattern:
                return policy
        return None

    def _audit_events_for(
        self, request: ToolRequest, decision: GatewayDecision
    ) -> list[AuditEvent]:
        created_at = utcnow()
        return [
            AuditEvent(
                id=f"audit_{request.id}_received",
                request_id=request.id,
                message="Received live MCP tool request for policy evaluation.",
                created_at=created_at,
                metadata={"tool_name": request.tool_name, "agent_name": request.agent_name},
            ),
            AuditEvent(
                id=f"audit_{request.id}_decision",
                request_id=request.id,
                message=f"Returned {decision.decision} with {decision.risk_level} risk.",
                created_at=created_at,
                metadata={"matched_policy": decision.matched_policy, "reasons": decision.reasons},
            ),
        ]

    def _load_one(self, table: str, row_id: str, model: type[ModelT]) -> ModelT | None:
        with self._connect() as conn:
            row = conn.execute(f"SELECT payload FROM {table} WHERE id = ?", (row_id,)).fetchone()
        return model.model_validate(json.loads(row["payload"])) if row else None

    def _load_all(self, table: str, model: type[ModelT]) -> list[ModelT]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT payload FROM {table} ORDER BY id").fetchall()
        return [model.model_validate(json.loads(row["payload"])) for row in rows]
