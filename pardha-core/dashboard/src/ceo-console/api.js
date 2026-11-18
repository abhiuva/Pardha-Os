export class PardhaApiError extends Error {
  constructor(message, { status = 0, code = "api_error", details = null } = {}) {
    super(message);
    this.name = "PardhaApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function authHeaders(token, headers = {}) {
  return {
    ...headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request(path, { token, signal, ...options } = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    signal,
    headers: authHeaders(token, options.headers),
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new PardhaApiError(payload?.detail || payload || `Request failed (${response.status})`, {
      status: response.status,
      code: payload?.code || "api_error",
      details: payload,
    });
  }
  return payload;
}

function isolate(records, businessId, resource) {
  const list = Array.isArray(records) ? records : [];
  const accepted = list.filter((item) => item?.business_id === businessId);
  const rejected = list.length - accepted.length;
  if (rejected > 0) {
    throw new PardhaApiError(`${resource} returned ${rejected} record(s) outside the active business.`, {
      status: 409,
      code: "cross_business_response",
      details: { resource, business_id: businessId, rejected },
    });
  }
  return accepted;
}

export async function loadCeoWorkspace({ businessId, token, signal }) {
  const query = `?business_id=${encodeURIComponent(businessId)}`;
  const [goals, tasks, executions, approvals, conversations, security] = await Promise.all([
    request(`/planning/goals${query}`, { token, signal }),
    request(`/tasks${query}`, { token, signal }),
    request(`/runtime/executions${query}`, { token, signal }),
    request(`/planning/approvals${query}`, { token, signal }),
    request(`/conversations${query}`, { token, signal }),
    request("/auth/security", { token, signal }),
  ]);

  return {
    goals: isolate(goals, businessId, "Goals"),
    tasks: isolate(tasks, businessId, "Tasks"),
    executions: isolate(executions, businessId, "Executions"),
    approvals: isolate(approvals, businessId, "Approvals"),
    conversations: isolate(conversations, businessId, "Conversations"),
    security,
  };
}

export async function streamExecutiveCommand({ businessId, message, token, signal, onEvent }) {
  const response = await fetch("/api/conversations/stream", {
    method: "POST",
    signal,
    headers: authHeaders(token, { "Content-Type": "application/json" }),
    body: JSON.stringify({
      business_id: businessId,
      message,
      owner: "Founder",
      module_context: "CEO Agent",
    }),
  });
  if (!response.ok) {
    let details = null;
    try { details = await response.json(); } catch { details = await response.text(); }
    throw new PardhaApiError(details?.detail || details || `Command failed (${response.status})`, {
      status: response.status,
      details,
    });
  }

  const reader = response.body?.getReader();
  if (!reader) throw new PardhaApiError("The conversation stream was unavailable.", { code: "stream_unavailable" });
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      onEvent?.(event);
      if (event.result) result = event.result;
    }
  }
  if (buffer.trim()) {
    const event = JSON.parse(buffer);
    onEvent?.(event);
    if (event.result) result = event.result;
  }
  if (!result) throw new PardhaApiError("The conversation ended without a final response.", { code: "missing_final_response" });
  const responseBusiness = result.conversation?.business_id || result.assistant_message?.business_id;
  if (responseBusiness !== businessId) {
    throw new PardhaApiError("The response business did not match the active workspace.", {
      status: 409,
      code: "cross_business_response",
      details: { expected: businessId, received: responseBusiness },
    });
  }
  return result;
}

export function delegateObjective({ businessId, title, description, token, signal }) {
  return request("/objectives", {
    token,
    signal,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ business_id: businessId, title, description, priority: "high" }),
  });
}

export function decidePlanApproval({ planId, decision, token, signal }) {
  return request(`/planning/plans/${encodeURIComponent(planId)}/${decision}`, {
    token,
    signal,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decided_by: "authenticated-session", comment: `Decision from CEO Console: ${decision}` }),
  });
}

export function approvalIdentityIsEnforced(security) {
  return security?.authorization_enforced === true && security?.authenticated_approval_identity === true;
}
