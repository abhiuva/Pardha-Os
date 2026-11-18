import { CheckCircle2, Circle, LoaderCircle, TriangleAlert } from "lucide-react";

function EventIcon({ status }) {
  if (status === "error" || status === "failed") return <TriangleAlert size={16} className="text-rose-300" />;
  if (["thinking", "planning", "executing"].includes(status)) return <LoaderCircle size={16} className="animate-spin text-cyan-300" />;
  if (status === "completed") return <CheckCircle2 size={16} className="text-emerald-300" />;
  return <Circle size={16} className="text-slate-500" />;
}

export function ExecutionTimeline({ timeline, executions }) {
  const events = timeline.length ? timeline : executions.map((execution) => ({
    id: execution.execution_id,
    phase: execution.status,
    title: execution.current_stage || "Execution",
    detail: `${execution.progress}% complete`,
  }));
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
      <h2 className="text-sm font-semibold text-white">Live execution timeline</h2>
      <p className="mt-1 text-xs text-slate-500">Conversation phases and persisted runtime executions.</p>
      <ol className="mt-4 space-y-3" aria-live="polite">
        {events.length === 0 && <li className="rounded-lg border border-dashed border-slate-700 p-4 text-sm text-slate-500">No execution events returned by the live APIs.</li>}
        {events.slice(-10).map((event, index) => {
          const state = event.phase || event.event_type || event.status || "pending";
          return (
            <li key={event.timeline_event_id || event.id || `${state}-${index}`} className="flex gap-3 rounded-lg bg-slate-900/70 p-3">
              <span className="mt-0.5"><EventIcon status={state} /></span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-200">{event.title || state}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">{event.detail || event.message || state}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
