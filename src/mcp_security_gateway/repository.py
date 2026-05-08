from __future__ import annotations

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

    def _load_one(self, table: str, row_id: str, model: type[ModelT]) -> ModelT | None:
        with self._connect() as conn:
            row = conn.execute(f"SELECT payload FROM {table} WHERE id = ?", (row_id,)).fetchone()
        return model.model_validate(json.loads(row["payload"])) if row else None

    def _load_all(self, table: str, model: type[ModelT]) -> list[ModelT]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT payload FROM {table} ORDER BY id").fetchall()
        return [model.model_validate(json.loads(row["payload"])) for row in rows]
