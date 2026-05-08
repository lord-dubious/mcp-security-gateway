# Demo Guide

Run the app locally:

```bash
uv run mcp-security-gateway
```

Open `http://127.0.0.1:8050` and click through the seeded allowed, approval-required, and blocked requests. Each request includes the matched policy, risk level, decision reasons, and audit events.

## Try a Live Evaluation

Use the dashboard evaluation panel or call the API directly:

```bash
curl -s http://127.0.0.1:8050/api/requests/evaluate \
  -H 'content-type: application/json' \
  -d '{
    "agent_name": "Release Agent",
    "tool_name": "shell.run",
    "input_summary": "Deploy the latest policy bundle to production",
    "metadata": {"environment": "production", "change_ticket": "SEC-1842"}
  }' | python -m json.tool
```

The expected result is `require_approval` with high risk. Change the `tool_name` to `repo.search` and the input to a read-only repository lookup to see an allowed low-risk decision. Change the request to `secret.read` or mention an API token/password to see a critical block.

## What To Point Out

- The gateway persists newly evaluated requests, not just demo fixtures.
- Decisions are deterministic and explainable.
- Audit events make the policy decision reviewable.
- The project intentionally does not execute the tool call; it models the security gate before execution.
