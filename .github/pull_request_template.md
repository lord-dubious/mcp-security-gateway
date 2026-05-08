## Summary
- 

## Verification
- [ ] `uv run --extra dev ruff check src tests`
- [ ] `uv run --extra dev ruff format --check src tests`
- [ ] `uv run python -m compileall -q src tests`
- [ ] `uv run --extra dev pytest tests/ --cov=mcp_security_gateway --cov-report=term-missing`

## Review Notes
- Are blocked/approval-required MCP tool calls explained clearly?
- Are audit trails deterministic and free of real secrets?
