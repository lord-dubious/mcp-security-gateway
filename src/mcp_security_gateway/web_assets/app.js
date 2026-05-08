const state = { active: null };

const SAMPLE_REQUEST = {
  agent_name: "Release Agent",
  tool_name: "shell.run",
  input_summary: "Deploy the latest policy bundle to production",
  metadata: {
    environment: "production",
    change_ticket: "SEC-1842"
  }
};

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Request failed: ${res.status}`);
  }
  return res.json();
}

function metric(key, value) {
  return `<div class="metric"><span>${key}</span><b>${value}</b></div>`;
}

function requestCard(request) {
  return `<div class="request ${state.active === request.id ? "active" : ""}" data-id="${request.id}">
    <strong>${request.tool_name}</strong>
    <p>${request.agent_name} · ${request.input_summary}</p>
  </div>`;
}

async function load(id = null) {
  const [summary, requests] = await Promise.all([api("/api/summary"), api("/api/requests")]);
  const requestIds = requests.map((request) => request.id);
  state.active = id || (requestIds.includes(state.active) ? state.active : requests[0]?.id);

  document.querySelector("#hero").textContent = `${summary.request_count} tool requests inspected`;
  document.querySelector("#risk").textContent = `${summary.high_risk_count} high-risk`;
  document.querySelector("#metrics").innerHTML =
    metric("Allow", summary.allow_count) +
    metric("Approval", summary.approval_count) +
    metric("Blocked", summary.block_count) +
    metric("High risk", summary.high_risk_count) +
    metric("Total", summary.request_count);
  document.querySelector("#requests").innerHTML = requests.map(requestCard).join("");
  document.querySelectorAll("[data-id]").forEach((el) => {
    el.addEventListener("click", () => load(el.dataset.id));
  });

  if (state.active) {
    const detail = await api(`/api/requests/${state.active}`);
    document.querySelector("#decision").innerHTML = `<div class="card">
      <strong class="${detail.decision.decision}">${detail.decision.decision}</strong>
      <p>${detail.decision.reasons.join(" · ")}</p>
      <small>${detail.decision.matched_policy} · ${detail.decision.risk_level}</small>
    </div>`;
    document.querySelector("#audit").innerHTML = detail.audit_events
      .map((event) => `<div class="card"><strong>${event.message}</strong><p>${JSON.stringify(event.metadata)}</p></div>`)
      .join("");
  }
}

function initEvaluationForm() {
  const textarea = document.querySelector("#evaluate-json");
  const status = document.querySelector("#evaluate-status");
  textarea.value = JSON.stringify(SAMPLE_REQUEST, null, 2);
  document.querySelector("#evaluate").addEventListener("click", async () => {
    status.textContent = "Evaluating request...";
    status.className = "";
    try {
      const payload = JSON.parse(textarea.value);
      const detail = await api("/api/requests/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      status.textContent = `Saved ${detail.decision.decision} decision for ${detail.request.tool_name}.`;
      status.className = "success";
      await load(detail.request.id);
    } catch (error) {
      status.textContent = error.message;
      status.className = "error";
    }
  });
}

document.querySelector("#reset").addEventListener("click", async () => {
  await api("/api/demo/reset", { method: "POST" });
  state.active = null;
  await load();
});

initEvaluationForm();
load().catch((error) => {
  document.querySelector("#hero").textContent = error.message;
});
