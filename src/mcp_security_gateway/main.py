from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mcp_security_gateway.api import router as api_router
from mcp_security_gateway.config import Settings
from mcp_security_gateway.repository import GatewayRepository
from mcp_security_gateway.web import ASSET_ROOT
from mcp_security_gateway.web import router as web_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    repository = GatewayRepository(settings.database_path)
    repository.ensure_seeded()
    app = FastAPI(title="MCP Security Gateway", version="0.1.0")
    app.state.repository = repository
    app.mount("/static", StaticFiles(directory=ASSET_ROOT), name="static")
    app.include_router(web_router)
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("mcp_security_gateway.main:app", host="127.0.0.1", port=8050, reload=False)
