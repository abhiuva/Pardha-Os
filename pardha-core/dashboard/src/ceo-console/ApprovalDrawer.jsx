import { ShieldAlert, X } from "lucide-react";

export function ApprovalDrawer({ approvals, enabled, open, onClose, onDecide }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/55" role="dialog" aria-modal="true" aria-label="Approval center">
      <section className="h-full w-full max-w-lg overflow-y-auto border-l border-slate-700 bg-[#0b111b] p-5 shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <p className="text-xs font-semibold text-amber-300">HUMAN APPROVAL</p>
            <h2 className="mt-1 text-xl font-semibold text-white">Approval center</h2>
          </div>
          <button onClick={onClose} aria-label="Close approvals" className="grid h-10 w-10 place-items-center rounded-lg border border-slate-700 text-slate-300"><X size={18} /></button>
        </header>
        {!enabled && (
          <div className="mt-5 flex gap-3 rounded-lg border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
            <ShieldAlert className="mt-0.5 shrink-0" size={18} />
            <p>Decisions are locked because the current server does not attest authenticated approval identity. This UI will not submit a forgeable approval.</p>
          </div>
        )}
        <div className="mt-5 space-y-3">
          {approvals.length === 0 && <p className="rounded-lg border border-dashed border-slate-700 p-5 text-sm text-slate-400">No pending approvals returned by the live API.</p>}
          {approvals.map((approval) => (
            <article key={approval.approval_id} className="rounded-lg border border-slate-700 bg-slate-950 p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold text-white">{approval.title}</h3>
                <span className="rounded bg-amber-400/15 px-2 py-1 text-xs font-semibold text-amber-200">{approval.risk_level} risk</span>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-400">{approval.detail}</p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500">
                <div><dt>Type</dt><dd className="mt-1 text-slate-300">{approval.approval_type}</dd></div>
                <div><dt>Plan</dt><dd className="mt-1 truncate text-slate-300">{approval.plan_id}</dd></div>
              </dl>
              <div className="mt-4 flex gap-2">
                <button disabled={!enabled} onClick={() => onDecide(approval, "approve")} className="h-10 rounded-lg bg-emerald-400 px-4 text-xs font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-35">Approve</button>
                <button disabled={!enabled} onClick={() => onDecide(approval, "reject")} className="h-10 rounded-lg border border-rose-400/40 px-4 text-xs font-bold text-rose-200 disabled:cursor-not-allowed disabled:opacity-35">Reject</button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
