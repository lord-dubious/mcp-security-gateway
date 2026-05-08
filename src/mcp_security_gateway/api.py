from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from mcp_security_gateway.models import GatewayDetail, GatewaySummary, ToolRequestEvaluation
from mcp_security_gateway.repository import GatewayRepository

router = APIRouter(prefix="/api")


def get_repository(request: Request) -> GatewayRepository:
    return request.app.state.repository


RepositoryDep = Annotated[GatewayRepository, Depends(get_repository)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/summary", response_model=GatewaySummary)
def summary(repository: RepositoryDep) -> GatewaySummary:
    return repository.summary()


@router.post("/demo/reset", response_model=GatewaySummary)
def reset_demo(repository: RepositoryDep) -> GatewaySummary:
    repository.reset_demo_data()
    return repository.summary()


@router.get("/policies")
def policies(repository: RepositoryDep):
    return repository.list_policies()


@router.get("/requests")
def requests(repository: RepositoryDep):
    return repository.list_requests()


@router.post("/requests/evaluate", response_model=GatewayDetail)
def evaluate_request(payload: ToolRequestEvaluation, repository: RepositoryDep) -> GatewayDetail:
    return repository.evaluate_request(payload)


@router.get("/requests/{request_id}", response_model=GatewayDetail)
def request_detail(request_id: str, repository: RepositoryDep) -> GatewayDetail:
    detail = repository.detail(request_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return detail
