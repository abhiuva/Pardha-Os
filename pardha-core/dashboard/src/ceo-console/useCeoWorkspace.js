import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  approvalIdentityIsEnforced,
  decidePlanApproval,
  delegateObjective,
  loadCeoWorkspace,
  PardhaApiError,
  streamExecutiveCommand,
} from "./api";

const emptyWorkspace = {
  goals: [], tasks: [], executions: [], approvals: [], conversations: [], security: null,
};

function errorView(error) {
  return {
    message: error?.message || "The request failed.",
    code: error?.code || "unknown_error",
    status: error?.status || 0,
  };
}

export function useCeoWorkspace({ businesses, initialBusinessId, token }) {
  const [businessId, setBusinessId] = useState(initialBusinessId || businesses[0]?.business_id || "");
  const [workspace, setWorkspace] = useState(emptyWorkspace);
  const [command, setCommand] = useState("What should I focus on today?");
  const [response, setResponse] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState("");
  const requestGeneration = useRef(0);
  const inFlight = useRef(new Set());

  useEffect(() => {
    if (!businessId && businesses[0]?.business_id) setBusinessId(businesses[0].business_id);
  }, [businessId, businesses]);

  const refresh = useCallback(async (signal) => {
    if (!businessId) return;
    const generation = ++requestGeneration.current;
    setStatus("loading");
    setError(null);
    try {
      const next = await loadCeoWorkspace({ businessId, token, signal });
      if (generation === requestGeneration.current) {
        setWorkspace(next);
        setStatus("idle");
      }
    } catch (nextError) {
      if (nextError.name !== "AbortError" && generation === requestGeneration.current) {
        setWorkspace(emptyWorkspace);
        setError(errorView(nextError));
        setStatus("error");
      }
    }
  }, [businessId, token]);

  useEffect(() => {
    setResponse(null);
    setTimeline([]);
    setNotice("");
    const controller = new AbortController();
    refresh(controller.signal);
    return () => controller.abort();
  }, [businessId, refresh]);

  const send = useCallback(async () => {
    const message = command.trim();
    if (!businessId || !message) return;
    const executionKey = `${businessId}:${message.toLowerCase()}`;
    if (inFlight.current.has(executionKey)) {
      setError(errorView(new PardhaApiError("This command is already running.", { status: 409, code: "duplicate_execution" })));
      return;
    }
    inFlight.current.add(executionKey);
    setStatus("thinking");
    setError(null);
    setNotice("");
    setTimeline([]);
    try {
      const result = await streamExecutiveCommand({
        businessId,
        message,
        token,
        onEvent: (event) => {
          setTimeline((current) => [...current, event]);
          if (event.phase) setStatus(event.phase === "completed" ? "idle" : event.phase);
        },
      });
      setResponse(result);
      setTimeline(result.timeline || []);
      setStatus("idle");
      setNotice("Executive response completed from the live conversation API.");
      await refresh();
    } catch (nextError) {
      setError(errorView(nextError));
      setStatus("error");
    } finally {
      inFlight.current.delete(executionKey);
    }
  }, [businessId, command, refresh, token]);

  const delegate = useCallback(async () => {
    const summary = response?.response?.executive_summary || response?.assistant_message?.content;
    if (!summary || !businessId) return;
    setStatus("executing");
    setError(null);
    try {
      const result = await delegateObjective({
        businessId,
        token,
        title: command.trim().slice(0, 120),
        description: summary,
      });
      if (result.objective?.business_id !== businessId || result.tasks?.some((task) => task.business_id !== businessId)) {
        throw new PardhaApiError("Delegation returned data outside the active business.", { status: 409, code: "cross_business_response" });
      }
      setNotice(`Delegated ${result.tasks?.length || 0} internal task(s). No external write was performed.`);
      await refresh();
      setStatus("idle");
    } catch (nextError) {
      setError(errorView(nextError));
      setStatus("error");
    }
  }, [businessId, command, refresh, response, token]);

  const decide = useCallback(async (approval, decision) => {
    if (!approvalIdentityIsEnforced(workspace.security)) {
      setError(errorView(new PardhaApiError("Approval is disabled because the server does not attest authenticated approval identity.", { status: 403, code: "approval_identity_unverified" })));
      return;
    }
    if (approval.business_id !== businessId) {
      setError(errorView(new PardhaApiError("Approval does not belong to the active business.", { status: 403, code: "cross_business_approval" })));
      return;
    }
    setStatus("executing");
    try {
      await decidePlanApproval({ planId: approval.plan_id, decision, token });
      setNotice(`Approval ${decision} recorded by the authenticated session.`);
      await refresh();
      setStatus("idle");
    } catch (nextError) {
      setError(errorView(nextError));
      setStatus("error");
    }
  }, [businessId, refresh, token, workspace.security]);

  const activeBusiness = useMemo(
    () => businesses.find((business) => business.business_id === businessId) || null,
    [businessId, businesses],
  );

  return {
    activeBusiness, businessId, setBusinessId, workspace, command, setCommand,
    response, timeline, status, error, notice, refresh, send, delegate, decide,
    approvalEnabled: approvalIdentityIsEnforced(workspace.security),
  };
}
