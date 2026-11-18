import { expect, test } from "@playwright/test";

const businesses = [
  { business_id: "business-a", business_name: "DP360" },
  { business_id: "business-b", business_name: "EatOnTime" },
];

function scopedRecords(businessId) {
  return {
    goals: [{ goal_id: `goal-${businessId}`, business_id: businessId, title: businessId === "business-a" ? "Acquire pilot customers" : "Launch three schools", current_status: "active", department: "CEO", risk_level: "medium", progress: 40 }],
    tasks: [{ task_id: `task-${businessId}`, business_id: businessId, title: businessId === "business-a" ? "Prepare pilot brief" : "Confirm school onboarding", status: "open", assigned_agent: "PM" }],
    executions: [{ execution_id: `execution-${businessId}`, business_id: businessId, status: "completed", current_stage: "verified", progress: 100 }],
    approvals: [{ approval_id: `approval-${businessId}`, plan_id: `plan-${businessId}`, business_id: businessId, title: "Publish external campaign", detail: "External write preview", risk_level: "high", approval_type: "external_write", status: "pending" }],
    conversations: [],
  };
}

async function installApi(page, options = {}) {
  let commandCalls = 0;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api/, "");
    const businessId = url.searchParams.get("business_id") || "business-a";
    const records = scopedRecords(businessId);
    const json = (payload, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(payload) });

    if (path === "/auth/session") return json({ authenticated: true, user: { user_id: "founder-1", email: "founder@example.test", full_name: "Founder", role: "Founder", status: "active" } });
    if (path === "/auth/security") return json({ password_hashing: "pbkdf2", authorization_enforced: false, authenticated_approval_identity: false });
    if (path === "/businesses") return json(businesses);
    if (path === "/context/current") return json({ active_business: businesses[0], counts: {} });
    if (path === "/planning/goals") return json(records.goals);
    if (path === "/tasks") return json(options.mixedBusinessTasks ? [...records.tasks, scopedRecords("business-b").tasks[0]] : records.tasks);
    if (path === "/runtime/executions") return json(records.executions);
    if (path === "/planning/approvals") return json(records.approvals);
    if (path === "/conversations" && request.method() === "GET") return json(records.conversations);
    if (path === "/conversations/stream") {
      commandCalls += 1;
      if (options.providerFailure) return json({ detail: "Reasoning provider unavailable; no fallback configured." }, 503);
      if (options.commandDelay) await new Promise((resolve) => setTimeout(resolve, options.commandDelay));
      const body = request.postDataJSON();
      const result = {
        conversation: { conversation_id: "conversation-1", business_id: body.business_id, title: body.message },
        user_message: { message_id: "message-user", business_id: body.business_id, role: "user", content: body.message },
        assistant_message: { message_id: "message-assistant", business_id: body.business_id, role: "assistant", content: "Prioritize pilot conversion and close the evidence gap." },
        timeline: [{ timeline_event_id: "timeline-1", event_type: "completed", title: "Response verified", detail: "Business-scoped response completed." }],
        response: {
          executive_summary: "Prioritize pilot conversion and close the evidence gap.",
          reasoning_provider: "openai",
          reasoning_metadata: { model: "gpt-test", fallback_used: false },
          evidence: [{ source: "live_goals", detail: "1 active goal for DP360" }],
          capabilities_used: [{ capability_id: "ceo.executive-review", name: "Executive Review", status: "completed" }],
          next_recommended_actions: [{ label: "Delegate pilot brief", intent: "create_objective" }],
        },
      };
      return route.fulfill({ status: 200, contentType: "application/x-ndjson", body: `${JSON.stringify({ phase: "thinking", message: "Analyzing" })}\n${JSON.stringify({ phase: "completed", result })}\n` });
    }
    return json([]);
  });
  return { commandCalls: () => commandCalls };
}

async function openConsole(page) {
  await page.goto("/ceo-agent?session=test-session");
  await expect(page.getByTestId("ceo-console")).toBeVisible();
}

test("switches business context without leaking the previous workspace", async ({ page }) => {
  await installApi(page);
  await openConsole(page);
  await expect(page.getByText("Acquire pilot customers")).toBeVisible();
  await page.getByTestId("business-switcher").selectOption("business-b");
  await expect(page.getByText("Launch three schools")).toBeVisible();
  await expect(page.getByText("Acquire pilot customers")).not.toBeVisible();
});

test("fails closed when an API returns cross-business records", async ({ page }) => {
  await installApi(page, { mixedBusinessTasks: true });
  await openConsole(page);
  await expect(page.getByTestId("ceo-error")).toContainText("cross_business_response");
  await expect(page.getByText("Confirm school onboarding")).not.toBeVisible();
});

test("does not submit a forgeable approval", async ({ page }) => {
  await installApi(page);
  await openConsole(page);
  await page.getByRole("button", { name: /Approvals/ }).click();
  await expect(page.getByText(/does not attest authenticated approval identity/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Reject" })).toBeDisabled();
});

test("deduplicates an in-flight executive command", async ({ page }) => {
  const api = await installApi(page, { commandDelay: 250 });
  await openConsole(page);
  await page.getByTestId("send-command").dblclick();
  await expect(page.getByTestId("executive-response")).toBeVisible();
  expect(api.commandCalls()).toBe(1);
});

test("surfaces provider failure without fabricating a response", async ({ page }) => {
  await installApi(page, { providerFailure: true });
  await openConsole(page);
  await page.getByTestId("send-command").click();
  await expect(page.getByTestId("ceo-error")).toContainText("Reasoning provider unavailable");
  await expect(page.getByTestId("executive-response")).not.toBeVisible();
});

test("renders evidence and provider metadata and captures critical viewports", async ({ page }) => {
  await installApi(page);
  await openConsole(page);
  await page.getByTestId("send-command").click();
  await expect(page.getByTestId("executive-response")).toContainText("gpt-test");
  await expect(page.getByTestId("executive-response")).toContainText("live_goals");
  await page.screenshot({ path: "../../docs/screenshots/ceo-console-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("executive-command")).toBeVisible();
  await page.screenshot({ path: "../../docs/screenshots/ceo-console-mobile.png", fullPage: true });
});
