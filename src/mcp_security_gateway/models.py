from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


class Decision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolPolicy(BaseModel):
    id: str
    name: str
    tool_pattern: str
    default_decision: Decision
    max_risk: RiskLevel
    rationale: str


class ToolRequest(BaseModel):
    id: str
    agent_name: str
    tool_name: str
    input_summary: str
    requested_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewayDecision(BaseModel):
    id: str
    request_id: str
    decision: Decision
    risk_level: RiskLevel
    matched_policy: str
    reasons: list[str]
    requires_human_review: bool


class AuditEvent(BaseModel):
    id: str
    request_id: str
    message: str
    created_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewayDetail(BaseModel):
    request: ToolRequest
    decision: GatewayDecision
    audit_events: list[AuditEvent]


class GatewaySummary(BaseModel):
    request_count: int
    allow_count: int
    approval_count: int
    block_count: int
    high_risk_count: int
