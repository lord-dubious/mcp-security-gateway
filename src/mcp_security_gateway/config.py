from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path("mcp_gateway_demo.sqlite3")

    @classmethod
    def from_env(cls) -> Settings:
        return cls(database_path=Path(os.getenv("MCP_GATEWAY_DATABASE_PATH", cls.database_path)))
