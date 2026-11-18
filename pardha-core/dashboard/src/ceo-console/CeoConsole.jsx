import {
  AlertTriangle, ArrowUpRight, Bot, CheckCircle2, ChevronRight, CircleGauge,
  ClipboardCheck, Database, ListTodo, RefreshCw, Send, ShieldCheck, Sparkles,
} from "lucide-react";
import { useState } from "react";
import { ApprovalDrawer } from "./ApprovalDrawer";
import { ExecutionTimeline } from "./ExecutionTimeline";
import { useCeoWorkspace } from "./useCeoWorkspace";
import { VoiceInput } from "./VoiceInput";

function Stat({ icon: Icon, label, value, detail, tone = "text-cyan-300" }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
      <div className="flex items-center justify-between"><p className="text-xs font-semibold text-slate-500">{label}</p><Icon size={17} className={tone} /></div>
      <p className="mt-4 text-3xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function Empty({ children }) {
  return <p className="rounded-lg border border-dashed border-slate-700 p-4 text-sm text-slate-500">{children}</p>;
}

function ResponsePanel({ result, onDelegate, disabled }) {
  const payload = result?.response || result?.assistant_message?.response_payload;
  if (!payload) return <Empty>Run an executive command to create a response from the live conversation engine.</Empty>;
  const provider = payload.reasoning_provider || "deterministic";
  const metadata = payload.reasoning_metadata || {};
  const fallback = metadata.fallback_used === true || metadata.fallback === true;
  return (
    <div className="space-y-4" data-testid="executive-response">
      <div className="rounded-lg border border-cyan-400/20 bg-cyan-400/10 p-4">
        <p className="text-sm leading-7 text-cyan-50">{payload.executive_summary || result.assistant_message?.content}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-900 p-3 text-xs"><p className="text-slate-500">Provider</p><p className="mt-1 font-semibold text-white">{provider}</p></div>
        <div className="rounded-lg bg-slate-900 p-3 text-xs"><p className="text-slate-500">Model</p><p className="mt-1 font-semibold text-white">{metadata.model || "not reported"}</p></div>
        <div className="rounded-lg bg-slate-900 p-3 text-xs"><p className="text-slate-500">Fallback</p><p className={`mt-1 font-semibold ${fallback ? "text-amber-300" : "text-emerald-300"}`}>{fallback ? "used" : "not reported"}</p></div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white"><Database size={16} className="text-emerald-300" />Source evidence</h3>
          <div className="mt-2 space-y-2">
            {(payload.evidence || []).length === 0 && <Empty>No evidence was reported. Treat this response as unsupported.</Empty>}
            {(payload.evidence || []).map((item, index) => <div key={item.source || index} className="rounded-lg bg-slate-900 p-3 text-xs text-slate-300"><strong>{item.source || item.type || "Source"}</strong><p className="mt-1 leading-5 text-slate-500">{item.detail || item.summary || JSON.stringify(item)}</p></div>)}
          </div>
        </section>
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-white"><Bot size={16} className="text-violet-300" />Capabilities used</h3>
          <div className="mt-2 space-y-2">
            {(payload.capabilities_used || []).length === 0 && <Empty>No capability invocation was reported.</Empty>}
            {(payload.capabilities_used || []).map((item, index) => <div key={item.capability_id || index} className="rounded-lg bg-slate-900 p-3 text-xs"><p className="font-semibold text-slate-200">{item.name || item.capability_id || "Capability"}</p><p className="mt-1 text-slate-500">{item.status || item.reason || "invoked"}</p></div>)}
          </div>
        </section>
      </div>
      <section>
        <h3 className="text-sm font-semibold text-white">Recommended actions</h3>
        <div className="mt-2 space-y-2">
          {(payload.next_recommended_actions || []).map((action, index) => <div key={`${action.label}-${index}`} className="flex items-center gap-2 rounded-lg bg-slate-900 p-3 text-sm text-slate-300"><ChevronRight size={16} className="text-cyan-300" />{action.label}</div>)}
        </div>
      </section>
      <button disabled={disabled} onClick={onDelegate} className="inline-flex h-11 items-center gap-2 rounded-lg bg-emerald-400 px-4 text-sm font-bold text-slate-950 disabled:opacity-40"><ArrowUpRight size={17} />Delegate as internal tasks</button>
      <p className="text-xs text-slate-500">Delegation writes only to Pardha objectives and tasks. It does not write to Jira, email, CRM, or other external systems.</p>
    </div>
  );
}

export default function CeoConsole({ businesses, initialBusinessId, token }) {
  const [approvalsOpen, setApprovalsOpen] = useState(false);
  const vm = useCeoWorkspace({ businesses, initialBusinessId, token });
  const busy = !["idle", "error"].includes(vm.status);
  const blockedTasks = vm.workspace.tasks.filter((task) => task.status === "BLOCKED" || task.status === "blocked");
  const activeGoals = vm.workspace.goals.filter((goal) => !["completed", "COMPLETED"].includes(goal.current_status));

  return (
    <section className="space-y-5" data-testid="ceo-console">
      <header className="flex flex-col gap-4 rounded-lg border border-slate-800 bg-[#0b111b] p-5 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-xs font-semibold text-cyan-300">CEO AGENT / LIVE WORKSPACE</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Founder command console</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Ask, inspect evidence, delegate internal work, and review approval gates for one business at a time.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs font-semibold text-slate-500" htmlFor="ceo-business">Business</label>
          <select id="ceo-business" data-testid="business-switcher" value={vm.businessId} onChange={(event) => vm.setBusinessId(event.target.value)} className="h-11 min-w-48 rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm font-semibold text-white">
            {businesses.map((business) => <option key={business.business_id} value={business.business_id}>{business.business_name}</option>)}
          </select>
          <button onClick={() => vm.refresh()} disabled={busy} aria-label="Refresh CEO workspace" className="grid h-11 w-11 place-items-center rounded-lg border border-slate-700 text-slate-300 disabled:opacity-40"><RefreshCw size={17} /></button>
          <button onClick={() => setApprovalsOpen(true)} className="inline-flex h-11 items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 text-sm font-semibold text-amber-100"><ClipboardCheck size={17} />Approvals <span className="rounded bg-amber-300 px-1.5 py-0.5 text-xs text-slate-950">{vm.workspace.approvals.length}</span></button>
        </div>
      </header>

      {vm.error && <div role="alert" data-testid="ceo-error" className="flex gap-3 rounded-lg border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-100"><AlertTriangle size={18} className="mt-0.5 shrink-0" /><div><strong>{vm.error.code}</strong><p className="mt-1">{vm.error.message}</p></div></div>}
      {vm.notice && <div className="flex gap-3 rounded-lg border border-emerald-400/25 bg-emerald-400/10 p-4 text-sm text-emerald-100"><CheckCircle2 size={18} />{vm.notice}</div>}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={CircleGauge} label="Active goals" value={activeGoals.length} detail="live planning records" />
        <Stat icon={ListTodo} label="Open tasks" value={vm.workspace.tasks.filter((task) => task.status !== "completed").length} detail={`${blockedTasks.length} blocked`} tone="text-amber-300" />
        <Stat icon={Sparkles} label="Executions" value={vm.workspace.executions.length} detail="current business only" tone="text-violet-300" />
        <Stat icon={vm.approvalEnabled ? ShieldCheck : AlertTriangle} label="Approval policy" value={vm.approvalEnabled ? "Verified" : "Locked"} detail={vm.approvalEnabled ? "server-attested identity" : "identity attestation missing"} tone={vm.approvalEnabled ? "text-emerald-300" : "text-rose-300"} />
      </div>

      <div className="grid gap-5 2xl:grid-cols-[minmax(0,1.45fr)_minmax(20rem,0.55fr)]">
        <div className="space-y-5">
          <section className="rounded-lg border border-slate-800 bg-slate-950/80 p-5">
            <div className="flex items-center justify-between gap-3"><div><h2 className="text-base font-semibold text-white">Executive command</h2><p className="mt-1 text-xs text-slate-500">Voice is opt-in. Review and edit the transcript before sending.</p></div><span className="rounded bg-slate-900 px-2 py-1 text-xs font-semibold text-cyan-300">{vm.status}</span></div>
            <textarea data-testid="executive-command" value={vm.command} onChange={(event) => vm.setCommand(event.target.value)} rows={5} className="mt-4 w-full resize-y rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm leading-6 text-white outline-none focus:border-cyan-400" />
            <div className="mt-3 flex flex-wrap items-start gap-2">
              <button data-testid="send-command" onClick={vm.send} disabled={busy || !vm.command.trim() || !vm.businessId} className="inline-flex h-11 items-center gap-2 rounded-lg bg-cyan-300 px-4 text-sm font-bold text-slate-950 disabled:opacity-40"><Send size={17} />Run command</button>
              <VoiceInput disabled={busy} onTranscript={vm.setCommand} />
            </div>
          </section>
          <section className="rounded-lg border border-slate-800 bg-slate-950/80 p-5">
            <h2 className="text-base font-semibold text-white">Executive response</h2>
            <p className="mt-1 text-xs text-slate-500">Provider, model, fallback state, source evidence, capabilities, and errors are shown when reported.</p>
            <div className="mt-4"><ResponsePanel result={vm.response} onDelegate={vm.delegate} disabled={busy} /></div>
          </section>
        </div>
        <div className="space-y-5">
          <ExecutionTimeline timeline={vm.timeline} executions={vm.workspace.executions} />
          <section className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
            <h2 className="text-sm font-semibold text-white">Goals and delegation</h2>
            <div className="mt-4 space-y-2">
              {activeGoals.length === 0 && <Empty>No goals returned by the live API.</Empty>}
              {activeGoals.slice(0, 5).map((goal) => <article key={goal.goal_id} className="rounded-lg bg-slate-900 p-3"><div className="flex justify-between gap-3"><p className="text-sm font-semibold text-slate-200">{goal.title}</p><span className="text-xs text-cyan-300">{goal.progress}%</span></div><p className="mt-2 text-xs text-slate-500">{goal.department} / {goal.risk_level} risk / {goal.current_status}</p></article>)}
            </div>
          </section>
          <section className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
            <h2 className="text-sm font-semibold text-white">Recent delegated tasks</h2>
            <div className="mt-4 space-y-2">
              {vm.workspace.tasks.length === 0 && <Empty>No tasks returned by the live API.</Empty>}
              {vm.workspace.tasks.slice(0, 6).map((task) => <article key={task.task_id} className="rounded-lg bg-slate-900 p-3"><p className="text-sm font-semibold text-slate-200">{task.title}</p><p className="mt-1 text-xs text-slate-500">{task.assigned_agent || "unassigned"} / {task.status}</p></article>)}
            </div>
          </section>
        </div>
      </div>

      <ApprovalDrawer approvals={vm.workspace.approvals} enabled={vm.approvalEnabled} open={approvalsOpen} onClose={() => setApprovalsOpen(false)} onDecide={vm.decide} />
    </section>
  );
}
