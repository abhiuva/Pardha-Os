import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const REFRESH_MS = 15_000;

const endpoints = {
  health: "/api/",
  diagnostics: "/api/system/database/status",
  ollama: "/api/system/ollama/status",
  voiceValidation: "/api/conversations/voice-validation",
  systemHealth: "/api/commercial/system/health",
  connectors: "/api/commercial/connectors/status",
  founder: "/api/commercial/founder-dashboard",
  journey: "/api/commercial/demo/journey",
  businesses: "/api/businesses",
  currentContext: "/api/context/current",
  agents: "/api/agents",
  ceo: "/api/agents/ceo/brief",
  cto: "/api/agents/cto/brief",
  pm: "/api/agents/pm/brief",
  objectives: "/api/objectives",
  collaborations: "/api/collaborations",
  tasks: "/api/tasks",
  projects: "/api/projects",
  knowledge: "/api/knowledge",
  knowledgeImports: "/api/knowledge/imports",
  events: "/api/events",
  executions: "/api/agents/executions",
  salesSummary: "/api/sales/summary",
  salesLeads: "/api/sales/leads",
  salesPipeline: "/api/sales/pipeline",
  salesDemos: "/api/sales/demos",
  salesDashboard: "/api/sales/dashboard",
  marketingSummary: "/api/marketing/summary",
  marketingCampaigns: "/api/marketing/campaigns",
  marketingAnalytics: "/api/marketing/analytics",
  marketingContent: "/api/marketing/content",
  marketingDashboard: "/api/marketing/dashboard",
  businessIntelligence: "/api/copilot/business-intelligence",
  customerWorkspace: "/api/copilot/customer-workspace",
  executiveBriefs: "/api/copilot/executive-briefs",
  businessHealth: "/api/copilot/health-dashboard",
  demoLibrary: "/api/copilot/demo-library",
  presentation: "/api/copilot/presentation",
  commercialReadiness: "/api/copilot/commercial-readiness",
  chiefConversations: "/api/chief/conversations",
  conversations: "/api/conversations",
  conversationStatus: "/api/conversations/status",
  founderGoals: "/api/chief/goals",
  executiveCommand: "/api/chief/executive-command",
  chiefHelp: "/api/chief/help",
  capabilities: "/api/capabilities",
  capabilityHealth: "/api/capabilities/health",
  capabilityGraph: "/api/capabilities/graph",
  capabilityValidation: "/api/capabilities/validation",
  planningGoals: "/api/planning/goals",
  executionPlans: "/api/planning/plans",
  planApprovals: "/api/planning/approvals",
  runtimeDashboard: "/api/runtime/dashboard",
  runtimeExecutions: "/api/runtime/executions",
  runtimeQueue: "/api/runtime/queue",
  runtimeNotifications: "/api/runtime/notifications",
  runtimeDepartments: "/api/runtime/departments",
  softwareFactoryDeliveries: "/api/software-factory/requirements",
  softwareFactoryDashboard: "/api/software-factory/dashboard",
  softwareFactoryValidation: "/api/software-factory/validation",
  enterpriseTenants: "/api/enterprise/tenants",
  enterpriseUsers: "/api/enterprise/users",
  enterpriseRbac: "/api/enterprise/rbac",
  enterpriseAudit: "/api/enterprise/audit",
  enterpriseObservability: "/api/enterprise/observability",
  enterpriseBilling: "/api/enterprise/billing",
  enterpriseIntegrations: "/api/enterprise/integrations",
  enterpriseDeployment: "/api/enterprise/deployment/profiles",
  enterpriseGovernance: "/api/enterprise/governance",
  enterpriseFlags: "/api/enterprise/feature-flags",
  enterpriseSecurity: "/api/enterprise/security",
  enterpriseDashboard: "/api/enterprise/dashboard",
  enterpriseAdmin: "/api/enterprise/admin",
  enterpriseValidation: "/api/enterprise/validation",
  jiraStatus: "/api/jira/status",
  jiraProjects: "/api/jira/projects",
  jiraIssues: "/api/jira/issues",
};

const modelManagerEndpoints = {
  start: "/api/system/ollama/start",
  stop: "/api/system/ollama/stop",
  switch: "/api/system/ollama/switch",
};

const businessScoped = new Set(["founder", "journey", "ceo", "cto", "pm", "objectives", "collaborations", "tasks", "projects", "knowledge", "events", "executions", "businessIntelligence", "customerWorkspace", "executiveBriefs", "businessHealth", "presentation", "chiefConversations", "conversations", "founderGoals", "executiveCommand", "planningGoals", "executionPlans", "planApprovals", "runtimeDashboard", "runtimeExecutions", "runtimeQueue", "runtimeNotifications", "runtimeDepartments", "softwareFactoryDeliveries", "softwareFactoryDashboard", "softwareFactoryValidation"]);

const initialData = {
  health: null,
  diagnostics: null,
  ollama: null,
  voiceValidation: null,
  systemHealth: null,
  connectors: [],
  founder: null,
  journey: null,
  businesses: [],
  currentContext: null,
  agents: [],
  ceo: null,
  cto: null,
  pm: null,
  objectives: [],
  collaborations: [],
  tasks: [],
  projects: [],
  knowledge: [],
  knowledgeImports: [],
  events: [],
  executions: [],
  salesSummary: null,
  salesLeads: [],
  salesPipeline: null,
  salesDemos: null,
  salesDashboard: null,
  marketingSummary: null,
  marketingCampaigns: [],
  marketingAnalytics: [],
  marketingContent: [],
  marketingDashboard: null,
  businessIntelligence: null,
  customerWorkspace: null,
  executiveBriefs: null,
  businessHealth: null,
  demoLibrary: null,
  presentation: null,
  commercialReadiness: null,
  chiefConversations: [],
  conversations: [],
  conversationStatus: null,
  founderGoals: [],
  executiveCommand: null,
  chiefHelp: null,
  capabilities: [],
  capabilityHealth: null,
  capabilityGraph: null,
  capabilityValidation: null,
  planningGoals: [],
  executionPlans: [],
  planApprovals: [],
  runtimeDashboard: null,
  runtimeExecutions: [],
  runtimeQueue: [],
  runtimeNotifications: [],
  runtimeDepartments: [],
  softwareFactoryDeliveries: [],
  softwareFactoryDashboard: null,
  softwareFactoryValidation: null,
  enterpriseTenants: [],
  enterpriseUsers: [],
  enterpriseRbac: null,
  enterpriseAudit: [],
  enterpriseObservability: null,
  enterpriseBilling: [],
  enterpriseIntegrations: [],
  enterpriseDeployment: [],
  enterpriseGovernance: [],
  enterpriseFlags: [],
  enterpriseSecurity: null,
  enterpriseDashboard: null,
  enterpriseAdmin: null,
  enterpriseValidation: null,
  jiraStatus: null,
  jiraProjects: [],
  jiraIssues: [],
};

const icons = {
  command: "M4 17l6-6-6-6M12 19h8",
  refresh: "M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5",
  check: "m5 12 4 4L19 6",
  warning: "M12 9v4M12 17h.01M10.3 3.6l-8.2 14.2A2 2 0 0 0 3.8 21h16.4a2 2 0 0 0 1.7-3.2L13.7 3.6a2 2 0 0 0-3.4 0Z",
  arrow: "M5 12h14M13 6l6 6-6 6",
  plus: "M12 5v14M5 12h14",
  home: "M3 11l9-8 9 8M5 10v10h14V10M9 20v-6h6v6",
  chat: "M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z",
  business: "M4 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16M3 21h18M9 7h1M9 11h1M9 15h1M14 7h1M14 11h1M14 15h1",
  agents: "M12 2v4M6.5 4.5l2.8 2.8M17.5 4.5l-2.8 2.8M5 11h14v8a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-8ZM9 15h.01M15 15h.01",
  knowledge: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15Z",
  marketing: "M3 11l18-6-6 18-3.5-7.5L3 11Z",
  sales: "M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7H14a3.5 3.5 0 0 1 0 7H6",
  factory: "M3 21h18M5 21V9l5 3V9l5 3V5h4v16M8 16h1M12 16h1M16 16h1",
  operations: "M4 6h16M4 12h16M4 18h16M8 6v12M16 6v12",
  integrations: "M8 12h8M9 7H7a5 5 0 0 0 0 10h2M15 7h2a5 5 0 0 1 0 10h-2",
  analytics: "M4 19V5M4 19h16M8 16v-5M12 16V8M16 16v-9",
  founder: "M12 3l3 6 6 .8-4.5 4.3 1.2 6.1L12 17l-5.7 3.2 1.2-6.1L3 9.8 9 9l3-6Z",
  settings: "M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5ZM19.4 15a1.8 1.8 0 0 0 .36 1.98l.05.05a2 2 0 0 1-2.83 2.83l-.05-.05A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 1.6V21a2 2 0 0 1-4 0v-.08a1.8 1.8 0 0 0-1-1.6 1.8 1.8 0 0 0-1.98.36l-.05.05a2 2 0 0 1-2.83-2.83l.05-.05A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-1.6-1H3a2 2 0 0 1 0-4h.08a1.8 1.8 0 0 0 1.6-1 1.8 1.8 0 0 0-.36-1.98l-.05-.05a2 2 0 0 1 2.83-2.83l.05.05A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-1.6V3a2 2 0 0 1 4 0v.08a1.8 1.8 0 0 0 1 1.6 1.8 1.8 0 0 0 1.98-.36l.05-.05a2 2 0 0 1 2.83 2.83l-.05.05A1.8 1.8 0 0 0 19.4 9c.2.6.8 1 1.6 1H21a2 2 0 0 1 0 4h-.08a1.8 1.8 0 0 0-1.52 1Z",
  mic: "M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3ZM19 11a7 7 0 0 1-14 0M12 18v4",
  search: "m21 21-4.3-4.3M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z",
};

function Icon({ name, className = "h-4 w-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={icons[name]} />
    </svg>
  );
}

function label(value = "") {
  return String(value).replaceAll("_", " ").replaceAll(".", " / ");
}

function short(value = "", length = 150) {
  return value && value.length > length ? `${value.slice(0, length).trim()}...` : value;
}

function relativeTime(value) {
  if (!value) return "No activity";
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

function statusClass(ok) {
  return ok ? "bg-green-50 text-green-700 border-green-100" : "bg-coral/10 text-coral border-coral/15";
}

function ShellButton({ children, onClick, disabled, dark = false, type }) {
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 text-sm font-bold transition disabled:opacity-50 ${dark ? "bg-violet-500 text-white hover:bg-violet-400" : "border border-slate-800 bg-slate-900 text-slate-200 hover:border-violet-400/40"}`}>
      {children}
    </button>
  );
}

function Metric({ title, value, detail }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">{title}</p>
      <p className="mt-5 font-display text-4xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function StateCard({ title, ok, value, detail }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-slate-100">{title}</p>
        <span className={`rounded-full border px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider ${statusClass(ok)}`}>{value}</span>
      </div>
      {detail && <p className="mt-3 text-xs leading-5 text-slate-500">{detail}</p>}
    </div>
  );
}

function EmptyState({ children }) {
  return <div className="rounded-xl border border-dashed border-slate-800 px-4 py-8 text-center text-sm text-slate-500">{children}</div>;
}

function List({ items, empty, render }) {
  if (!items?.length) return <EmptyState>{empty}</EmptyState>;
  return <div className="space-y-3">{items.map(render)}</div>;
}

function Panel({ title, subtitle, children, action }) {
  return (
    <section className="panel p-5">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow">{title}</p>
          {subtitle && <p className="mt-2 text-sm text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function BriefPanel({ title, badge, items, risks }) {
  return (
    <Panel title={title} subtitle="Executive brief" action={<span className="rounded-full bg-ink px-3 py-1.5 text-[0.65rem] font-bold uppercase tracking-wider text-white">{badge}</span>}>
      <List
        items={(items || []).slice(0, 5)}
        empty="No brief items yet. Load DP360 Demo or create an objective."
        render={(item, index) => <p key={`${title}-${index}`} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm leading-6 text-ink/70">{typeof item === "string" ? item : item.title}</p>}
      />
      <div className="mt-5 border-t border-ink/10 pt-4">
        <p className="eyebrow mb-3">Open risks</p>
        <List
          items={(risks || []).slice(0, 4)}
          empty="No immediate risks detected."
          render={(item, index) => <p key={`${title}-risk-${index}`} className="flex gap-2 rounded-xl bg-coral/10 px-4 py-3 text-sm text-coral"><Icon name="warning" />{typeof item === "string" ? item : item.title}</p>}
        />
      </div>
    </Panel>
  );
}

function LoginPage({ onLogin, error }) {
  const [email, setEmail] = useState("founder@pardha.local");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    await onLogin({ email, password, rememberMe });
    setSubmitting(false);
  };
  return (
    <main className="grid min-h-screen bg-ink px-4 py-8 text-white lg:grid-cols-[1.05fr_0.95fr]">
      <section className="mx-auto flex w-full max-w-3xl flex-col justify-between rounded-3xl border border-white/10 bg-white/[0.04] p-8">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-acid text-ink"><Icon name="command" /></span>
          <div>
            <p className="font-display text-2xl font-bold">Pardha</p>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/40">AI Business Operating System</p>
          </div>
        </div>
        <div className="py-16">
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.18em] text-acid">DP360 v1.0 Release Candidate</p>
          <h1 className="font-display text-5xl font-semibold leading-tight md:text-6xl">Founder command center for customer pilots.</h1>
          <p className="mt-6 max-w-2xl text-sm leading-7 text-white/60">Log in, select a business, upload knowledge, generate executive briefs, and manage execution from one commercial dashboard.</p>
        </div>
        <div className="grid gap-3 text-sm text-white/55 md:grid-cols-3">
          <p>Secure sessions</p>
          <p>Business-scoped data</p>
          <p>No automatic reasoning</p>
        </div>
      </section>
      <section className="mx-auto grid w-full max-w-md place-items-center">
        <form onSubmit={submit} className="w-full rounded-3xl bg-white p-6 text-ink shadow-card">
          <p className="eyebrow">Enterprise Login</p>
          <h2 className="mt-4 font-display text-3xl font-semibold">Welcome back</h2>
          <label className="mt-6 block text-xs font-bold uppercase tracking-wider text-ink/40">Email</label>
          <input value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 min-h-11 w-full rounded-xl border border-ink/10 px-4 text-sm outline-none" autoComplete="email" />
          <label className="mt-4 block text-xs font-bold uppercase tracking-wider text-ink/40">Password</label>
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" className="mt-2 min-h-11 w-full rounded-xl border border-ink/10 px-4 text-sm outline-none" autoComplete="current-password" />
          <label className="mt-4 flex items-center gap-2 text-sm font-semibold text-ink/60">
            <input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} />
            Remember me
          </label>
          {error && <p className="mt-4 rounded-xl bg-coral/10 px-4 py-3 text-sm text-coral">{error}</p>}
          <button disabled={submitting} className="mt-6 min-h-11 w-full rounded-xl bg-ink px-4 text-sm font-bold text-white disabled:opacity-60">{submitting ? "Signing in..." : "Sign in"}</button>
        </form>
      </section>
    </main>
  );
}

function MissionLanding({ user, data, activeBusiness, onBrief, onOpenConversation, voiceState }) {
  const highPriority = data.planningGoals?.filter((goal) => goal.priority === "high" || goal.risk_level === "high").length || 0;
  const completedExecutions = data.runtimeExecutions?.filter((execution) => execution.status === "completed").length || 0;
  const prospects = data.salesSummary?.prospects || 0;
  const notifications = data.runtimeNotifications?.filter((item) => item.status === "unread").length || 0;
  return (
    <section className="mission-surface mb-6 min-h-[calc(100vh-6rem)] rounded-[2rem] p-6 text-white md:p-8">
      <div className="grid h-full min-h-[42rem] gap-8 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="flex flex-col justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.24em] text-acid">PARDHA</p>
            <h1 className="mt-6 font-display text-6xl font-semibold leading-none md:text-7xl">Chief of Staff</h1>
            <p className="mt-4 text-2xl font-semibold text-white/70">Ready.</p>
          </div>
          <div className="max-w-2xl">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/40">Good Morning {user.full_name}</p>
            <p className="mt-4 font-display text-4xl font-semibold leading-tight">{activeBusiness?.business_name || "Your company"} has {highPriority} high-priority item{highPriority === 1 ? "" : "s"} and {notifications} unread notification{notifications === 1 ? "" : "s"}.</p>
            <p className="mt-4 text-sm leading-7 text-white/55">Runtime completed {completedExecutions} execution{completedExecutions === 1 ? "" : "s"}. Sales currently tracks {prospects} prospects. Would you like today's executive briefing?</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <ShellButton onClick={onBrief}>Executive Briefing</ShellButton>
              <ShellButton onClick={onOpenConversation}>Open Conversation</ShellButton>
            </div>
          </div>
        </div>
        <div className="grid content-center gap-5 text-ink">
          <div className="place-self-center"><IntelligenceOrb state={voiceState} /></div>
          <div className="grid gap-4 md:grid-cols-2">
            <StateCard title="Business Health" ok={(data.businessHealth?.customer_health?.score || 0) >= 70} value={data.businessHealth?.customer_health?.score || 0} detail="customer health score" />
            <StateCard title="Approvals" ok={(data.planApprovals?.length || 0) === 0} value={data.planApprovals?.length || 0} detail="waiting for founder" />
            <StateCard title="Departments" ok={(data.runtimeDepartments?.length || 0) > 0} value={data.runtimeDepartments?.length || 0} detail="orchestrated teams" />
            <StateCard title="Connectors" ok={(data.connectors || []).length > 0 && (data.connectors || []).every((item) => item.connected)} value={`${(data.connectors || []).filter((item) => item.connected).length}/${data.connectors?.length || 0}`} detail="connected accounts" />
          </div>
        </div>
      </div>
    </section>
  );
}

const navItems = [
  ["Executive Dashboard", "home"],
  ["Ask Pardha", "chat"],
  ["Businesses", "business"],
  ["Agents", "agents"],
  ["Knowledge", "knowledge"],
  ["Marketing", "marketing"],
  ["Sales", "sales"],
  ["Product Factory", "factory"],
  ["Operations", "operations"],
  ["Integrations", "integrations"],
  ["Analytics", "analytics"],
  ["Founder", "founder"],
  ["Settings", "settings"],
];

function WorkspaceShell({ user, activePage, setActivePage, activeBusinessId, businesses, onSwitchBusiness, onRefresh, onLogout, onLoadDemo, working, notice, failures, lastUpdated, children, voiceState, onVoiceStart, onVoiceStop, continuousVoice, onToggleContinuousVoice, voiceError, interimTranscript, ollama, voiceValidation, onModelStart, onModelStop, onModelSwitch, pageOwnsVoice = false }) {
  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[18.75rem] border-r border-slate-800/90 bg-[#0b111b] px-3 py-6 lg:block">
        <div className="mb-10 flex items-center gap-4 px-2">
          <span className="grid h-14 w-14 place-items-center rounded-2xl bg-violet-500 text-cyan-300 shadow-[0_0_34px_rgba(139,92,246,0.45)]"><Icon name="command" className="h-6 w-6" /></span>
          <div>
            <p className="font-display text-xl font-bold tracking-wide text-white">PARDHA</p>
            <p className="text-[0.68rem] font-bold uppercase tracking-[0.18em] text-slate-500">Agentic OS</p>
          </div>
        </div>
        <p className="mb-3 px-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Workspace</p>
        <nav className="space-y-2">
          {navItems.map(([name, icon]) => (
            <button key={name} onClick={() => setActivePage(name)} className={`group flex min-h-12 w-full items-center gap-4 rounded-2xl px-3 text-left text-sm font-bold transition ${activePage === name ? "border border-violet-400/30 bg-violet-500/20 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-white"}`}>
              <span className={`grid h-9 w-9 place-items-center rounded-xl ${activePage === name ? "bg-violet-500/35 text-white" : "bg-slate-900 text-slate-500 group-hover:text-cyan-300"}`}><Icon name={icon} /></span>
              <span>{name}</span>
            </button>
          ))}
        </nav>
        <div className="absolute inset-x-3 bottom-5 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm font-bold text-emerald-300">
          <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />System live
        </div>
      </aside>

      <main className="min-h-screen lg:pl-[18.75rem]">
        <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-[#070b12]/88 backdrop-blur">
          <div className="flex min-h-[6.25rem] items-center gap-4 px-4 md:px-8">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{new Intl.DateTimeFormat("en", { weekday: "long", day: "2-digit", month: "long" }).format(new Date())}</p>
              <h1 className="mt-2 truncate font-display text-3xl font-semibold text-white md:text-4xl">{activePage}</h1>
            </div>
            <label className="hidden min-h-12 w-full max-w-sm items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 px-4 text-slate-500 xl:flex">
              <Icon name="search" />
              <span className="text-sm">Search Pardha...</span>
            </label>
            <select value={activeBusinessId} onChange={(event) => onSwitchBusiness(event.target.value)} className="hidden min-h-12 max-w-[13rem] rounded-2xl border border-slate-800 bg-slate-950 px-4 text-sm font-bold text-slate-200 outline-none md:block">
              {businesses.map((business) => <option key={business.business_id} value={business.business_id}>{business.business_name}</option>)}
            </select>
            <button onClick={onLoadDemo} disabled={working} className="hidden min-h-12 rounded-2xl border border-slate-800 bg-slate-950 px-4 text-sm font-bold text-slate-300 disabled:opacity-50 md:block">Load demo</button>
            <button onClick={onRefresh} className="grid h-12 w-12 place-items-center rounded-2xl border border-slate-800 bg-slate-950 text-slate-300" aria-label="Refresh dashboard"><Icon name="refresh" /></button>
            <button onClick={onLogout} className="hidden items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-2 text-left md:flex">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-violet-500 text-sm font-bold text-white">{(user.full_name || "F").split(" ").map((part) => part[0]).join("").slice(0, 2)}</span>
              <span><span className="block text-sm font-bold text-white">{user.full_name}</span><span className="block text-xs text-slate-500">{user.role || "Founder"}</span></span>
            </button>
          </div>
        </header>
        <div className={`px-4 py-6 md:px-8 ${pageOwnsVoice ? "pb-8" : "pb-96 xl:pr-[25rem]"}`}>
          {failures.length > 0 && <div className="mb-5 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm font-semibold text-amber-200">{failures.length} live endpoint{failures.length === 1 ? "" : "s"} need attention. Review Integrations or Settings.</div>}
          {notice && <div className="mb-5 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm font-semibold text-emerald-200">{notice}</div>}
          {children}
          <p className="mt-8 text-xs text-slate-600">{lastUpdated ? `Updated ${relativeTime(lastUpdated)}` : "Waiting for first refresh"}</p>
        </div>
      </main>
      {!pageOwnsVoice && (
        <ExecutiveVoiceRuntime
          state={voiceState}
          moduleContext={activePage}
          onStart={onVoiceStart}
          onStop={onVoiceStop}
          continuous={continuousVoice}
          onToggleContinuous={onToggleContinuousVoice}
          error={voiceError}
          transcript={interimTranscript}
          ollama={ollama}
          validation={voiceValidation}
          onModelStart={onModelStart}
          onModelStop={onModelStop}
          onModelSwitch={onModelSwitch}
        />
      )}
    </div>
  );
}

function DarkPanel({ title, subtitle, children, action, className = "" }) {
  return (
    <section className={`rounded-[1.75rem] border border-slate-800 bg-slate-950/70 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.22)] ${className}`}>
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{title}</p>
          {subtitle && <p className="mt-2 text-sm leading-6 text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function DarkEmpty({ children }) {
  return <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-8 text-center text-sm text-slate-500">{children}</div>;
}

function DarkList({ items, empty, render }) {
  if (!items?.length) return <DarkEmpty>{empty}</DarkEmpty>;
  return <div className="space-y-3">{items.map(render)}</div>;
}

function WorkItem({ title, detail, accent = "violet", action }) {
  const accents = {
    violet: "border-violet-400/25 bg-violet-400/10 text-violet-200",
    cyan: "border-cyan-400/25 bg-cyan-400/10 text-cyan-200",
    green: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    amber: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    red: "border-rose-400/25 bg-rose-400/10 text-rose-200",
  };
  return (
    <article className="flex items-start justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/55 px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-bold text-slate-100">{title}</p>
        {detail && <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>}
      </div>
      {action || <span className={`rounded-full border px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider ${accents[accent] || accents.violet}`}>Open</span>}
    </article>
  );
}

function ExecutiveVoiceRuntime({ state, moduleContext, onStart, onStop, continuous, onToggleContinuous, error, transcript, ollama, validation, onModelStart, onModelStop, onModelSwitch }) {
  const active = !["idle", "completed"].includes(state);
  const model = ollama?.model || "qwen3:8b";
  return (
    <div className="fixed bottom-5 right-5 z-50 w-[22rem] max-w-[calc(100vw-2rem)] rounded-[1.5rem] border border-violet-300/25 bg-slate-950/95 p-4 text-slate-100 shadow-[0_0_60px_rgba(139,92,246,0.28)] backdrop-blur">
      <div className="flex items-start gap-3">
        <button onClick={active ? onStop : onStart} className={`grid h-16 w-16 shrink-0 place-items-center rounded-full border border-violet-300/30 bg-violet-500 text-white shadow-[0_0_46px_rgba(139,92,246,0.55)] voice-orb-${state}`} aria-label="Executive voice assistant">
          <Icon name="mic" className="h-6 w-6" />
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Executive Voice</p>
            <span className="rounded-full bg-violet-400/15 px-2.5 py-1 text-[0.62rem] font-bold uppercase text-violet-200">{label(state)}</span>
          </div>
          <p className="mt-2 truncate text-sm font-bold text-white">{moduleContext}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{error || transcript || "Push to talk, or enable continuous mode."}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <button onClick={onStart} disabled={active} className="min-h-9 rounded-xl bg-cyan-400 px-3 text-xs font-bold text-slate-950 disabled:opacity-40">Talk</button>
        <button onClick={onStop} className="min-h-9 rounded-xl border border-slate-800 bg-slate-900 px-3 text-xs font-bold text-slate-200">Interrupt</button>
        <button onClick={onToggleContinuous} className={`min-h-9 rounded-xl px-3 text-xs font-bold ${continuous ? "bg-emerald-400 text-slate-950" : "border border-slate-800 bg-slate-900 text-slate-200"}`}>Continuous</button>
      </div>
      <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-bold text-white">{model}</p>
          <select value={model} onChange={(event) => onModelSwitch(event.target.value)} className="rounded-lg border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-200 outline-none">
            {["qwen3:8b", "llama3.2:3b", ...(ollama?.available_models || [])].filter((item, index, all) => item && all.indexOf(item) === index).map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[0.68rem] text-slate-500">
          <p>Reasoning: <span className="text-slate-300">{ollama?.reasoning_status || "unknown"}</span></p>
          <p>Latency: <span className="text-slate-300">{ollama?.latency_ms ?? "n/a"}ms</span></p>
          <p>Tokens: <span className="text-slate-300">{ollama?.tokens ?? "n/a"}</span></p>
          <p>Context: <span className="text-slate-300">{ollama?.context_size || 0}</span></p>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <button onClick={() => onModelStart(model)} className="min-h-8 rounded-lg bg-violet-500 px-3 text-xs font-bold text-white">Start model</button>
          <button onClick={() => onModelStop(model)} className="min-h-8 rounded-lg border border-slate-800 px-3 text-xs font-bold text-slate-300">Stop</button>
        </div>
        <p className="mt-3 text-[0.68rem] text-slate-500">Validation: {validation?.scenarios_run || 0} scenarios / score {validation?.score ?? "n/a"}</p>
      </div>
    </div>
  );
}

function VoiceCore({ state }) {
  return (
    <div className="relative grid aspect-square min-h-[18rem] place-items-center overflow-hidden rounded-[1.75rem] border border-violet-400/20 bg-[radial-gradient(circle_at_50%_50%,rgba(139,92,246,0.25),rgba(6,10,18,0.12)_40%,transparent_70%)]">
      <div className="absolute h-[24rem] w-[24rem] rounded-full border border-violet-400/12" />
      <div className="absolute h-[15rem] w-[15rem] rounded-full border border-cyan-400/12" />
      <div className={`grid h-36 w-36 place-items-center rounded-full bg-violet-600 shadow-[0_0_80px_rgba(139,92,246,0.72)] orb-${state}`}>
        <div className="flex h-16 items-center gap-2">
          {[30, 48, 70, 92, 64, 42].map((height, index) => <span key={index} className="w-2 rounded-full bg-cyan-300" style={{ height }} />)}
        </div>
      </div>
    </div>
  );
}

function ExecutiveDashboardPage({ user, data, activeBusiness, onAsk, onVoice, onApprove, onReject, working, voiceState }) {
  const name = (user.full_name || "Founder").split(" ")[0];
  const brief = data.founder?.ceo_summary || data.executiveCommand?.summary || data.ceo?.summary;
  const todayGoal = data.founderGoals?.[0] || data.planningGoals?.[0] || data.objectives?.[0];
  const approvals = [...(data.planApprovals || []), ...((data.softwareFactoryDashboard?.pending_approvals || []))].slice(0, 5);
  const recommendations = [
    ...(data.founder?.todays_priorities || []),
    ...(data.executiveCommand?.quick_actions || []),
    ...(data.businessHealth?.ai_recommendations || []),
  ].filter(Boolean).slice(0, 6);
  const healthScore = data.businessHealth?.customer_health?.score ?? data.businessHealth?.business_health_score ?? data.commercialReadiness?.overall_score;
  return (
    <section className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1fr_0.55fr]">
        <DarkPanel title="Good Morning" subtitle={activeBusiness?.business_name ? `Current business: ${activeBusiness.business_name}` : "Select a business to load operating context."} className="min-h-[28rem]">
          <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
            <div>
              <span className="inline-flex rounded-full border border-emerald-400/25 bg-emerald-400/10 px-4 py-2 text-xs font-bold uppercase tracking-wider text-emerald-300">Admin verified</span>
              <h2 className="mt-8 max-w-4xl font-display text-5xl font-semibold leading-tight text-white md:text-6xl">Good morning, {name}.</h2>
              <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-400">Pardha is organized around your founder workflow: executive brief, conversation, business context, then operations.</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <button onClick={() => onAsk("Generate today's executive briefing.")} className="min-h-12 rounded-2xl bg-violet-500 px-6 text-sm font-bold text-white">Ask Pardha</button>
                <button onClick={() => onAsk("Open daily briefing.")} className="min-h-12 rounded-2xl border border-slate-800 bg-slate-900 px-6 text-sm font-bold text-slate-200">Open daily briefing</button>
              </div>
            </div>
            <VoiceCore state={voiceState} />
          </div>
        </DarkPanel>
        <DarkPanel title="Today's Goal" subtitle={todayGoal?.title || "No active goal has been created yet."}>
          {todayGoal ? <WorkItem title={todayGoal.title} detail={`${label(todayGoal.status || todayGoal.current_status || "active")} / ${todayGoal.owner || todayGoal.department || "Founder"}`} accent="cyan" /> : <DarkEmpty>Create a goal from Ask Pardha or Founder.</DarkEmpty>}
          <div className="mt-4">
            <DarkPanel title="Voice Assistant" subtitle="Visible everywhere and scoped to the current page." className="bg-slate-900/45">
              <button onClick={onVoice} className="min-h-11 w-full rounded-2xl bg-cyan-400 px-4 text-sm font-bold text-slate-950">Start voice</button>
            </DarkPanel>
          </div>
        </DarkPanel>
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <DarkPanel title="Today's Executive Brief" subtitle="Business-level summary from live founder and agent data.">
          {brief ? <p className="text-xl leading-9 text-slate-200">{brief}</p> : <DarkEmpty>No executive brief is available yet. Ask Pardha to generate one for the current business.</DarkEmpty>}
        </DarkPanel>
        <DarkPanel title="Business Health" subtitle="Founder-facing health only, no infrastructure metrics.">
          {healthScore !== undefined ? (
            <div className="grid gap-3">
              <p className="font-display text-5xl font-semibold text-white">{healthScore}</p>
              <p className="text-sm text-slate-500">Current business health score from business context.</p>
              <DarkList items={(data.businessHealth?.ai_recommendations || []).slice(0, 3)} empty="No health recommendations yet." render={(item, index) => <WorkItem key={index} title={item} accent="green" />} />
            </div>
          ) : <DarkEmpty>Business health is not available for the current context.</DarkEmpty>}
        </DarkPanel>
      </div>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr_0.8fr]">
        <DarkPanel title="Pending Approvals" subtitle="Founder decisions required before work proceeds.">
          <DarkList items={approvals} empty="No approvals are waiting." render={(approval) => (
            <WorkItem key={approval.approval_id || approval.plan_id} title={approval.title || approval.approval_type} detail={`${label(approval.risk_level || "review")} / ${label(approval.status || "pending")}`} accent={approval.risk_level === "high" ? "red" : "amber"} action={<div className="flex gap-2"><button disabled={working || !approval.plan_id} onClick={() => approval.plan_id && onApprove(approval.plan_id)} className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-bold text-emerald-300 disabled:opacity-40">Approve</button><button disabled={working || !approval.plan_id} onClick={() => approval.plan_id && onReject(approval.plan_id)} className="rounded-full bg-rose-400/15 px-3 py-1 text-xs font-bold text-rose-300 disabled:opacity-40">Reject</button></div>} />
          )} />
        </DarkPanel>
        <DarkPanel title="Current Recommendations" subtitle="Recommended next actions from executive, health, and command surfaces.">
          <DarkList items={recommendations} empty="No recommendations yet." render={(item, index) => <WorkItem key={index} title={typeof item === "string" ? item : item.title} detail={typeof item === "string" ? "" : item.detail} accent="violet" />} />
        </DarkPanel>
        <DarkPanel title="Quick Actions" subtitle="Conversation-first entry points.">
          <div className="grid gap-3">
            {["What should I do next?", "Review pending approvals.", "Create a product factory package.", "Show integration gaps."].map((prompt) => <button key={prompt} onClick={() => onAsk(prompt)} className="min-h-11 rounded-2xl border border-slate-800 bg-slate-900 px-4 text-left text-sm font-bold text-slate-200">{prompt}</button>)}
          </div>
        </DarkPanel>
      </div>
    </section>
  );
}

function BusinessesPage({ data, activeBusiness, businessName, setBusinessName, createBusiness, switchBusiness, working }) {
  return (
    <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
      <DarkPanel title="Businesses" subtitle="Business is the second-level context after conversation.">
        <form onSubmit={createBusiness} className="mb-5 flex gap-3">
          <input value={businessName} onChange={(event) => setBusinessName(event.target.value)} className="min-h-11 flex-1 rounded-2xl border border-slate-800 bg-slate-900 px-4 text-sm text-white outline-none" placeholder="New business name" />
          <button disabled={working} className="rounded-2xl bg-violet-500 px-5 text-sm font-bold text-white">Create</button>
        </form>
        <DarkList items={data.businesses} empty="No businesses available." render={(business) => <button key={business.business_id} onClick={() => switchBusiness(business.business_id)} className={`w-full rounded-2xl border px-4 py-3 text-left ${activeBusiness?.business_id === business.business_id ? "border-violet-400/40 bg-violet-400/15" : "border-slate-800 bg-slate-900/55"}`}><span className="block text-sm font-bold text-white">{business.business_name}</span><span className="text-xs text-slate-500">{business.business_type || "workspace"}</span></button>} />
      </DarkPanel>
      <DarkPanel title="Current Business" subtitle={activeBusiness?.business_name || "No business selected."}>
        {activeBusiness ? (
          <div className="grid gap-4 md:grid-cols-2">
            <WorkItem title="Objectives" detail={`${data.objectives.length} active records`} accent="cyan" />
            <WorkItem title="Knowledge" detail={`${data.knowledge.length} context records`} accent="violet" />
            <WorkItem title="Open Tasks" detail={`${data.tasks.filter((task) => task.status !== "completed").length} tasks waiting`} accent="amber" />
            <WorkItem title="Recent Conversations" detail={`${data.conversations.length} saved threads`} accent="green" />
          </div>
        ) : <DarkEmpty>Select or create a business to view context.</DarkEmpty>}
      </DarkPanel>
    </section>
  );
}

function AgentsPage({ data }) {
  const canonical = ["CEO", "CTO", "PM", "Marketing", "Sales", "Finance", "HR", "QA", "Knowledge", "Operations", "Engineering"];
  const executionByAgent = (data.executions || []).reduce((acc, item) => ({ ...acc, [item.agent_name]: item }), {});
  return (
    <section className="grid gap-6">
      <DarkPanel title="Agents" subtitle="Every AI operator, its current work, memory, capabilities, history, and performance in one place.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {canonical.map((name) => {
            const registered = (data.agents || []).find((agent) => agent.name?.toLowerCase().includes(name.toLowerCase()));
            const latest = executionByAgent[name] || (data.executions || []).find((execution) => execution.agent_name?.toLowerCase().includes(name.toLowerCase()));
            const capabilities = (data.capabilities || []).filter((capability) => capability.agent_type?.toLowerCase?.().includes(name.toLowerCase()) || capability.name?.toLowerCase().includes(name.toLowerCase())).slice(0, 3);
            return (
              <article key={name} className="rounded-[1.5rem] border border-slate-800 bg-slate-950/70 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div><p className="text-lg font-bold text-white">{name}</p><p className="text-xs text-slate-500">{registered?.role || "Business operator"}</p></div>
                  <span className={`rounded-full px-2.5 py-1 text-[0.65rem] font-bold uppercase ${registered?.status === "active" || latest ? "bg-emerald-400/10 text-emerald-300" : "bg-slate-800 text-slate-500"}`}>{registered?.status || (latest ? "active" : "idle")}</span>
                </div>
                <div className="mt-5 space-y-3">
                  <WorkItem title="Current Task" detail={latest?.objective || latest?.task_title || latest?.status || "No active task"} accent="cyan" />
                  <WorkItem title="Capabilities" detail={capabilities.map((item) => item.name).join(", ") || "No mapped capabilities returned"} accent="violet" />
                  <WorkItem title="Memory" detail={`${(data.knowledge || []).filter((item) => `${item.category} ${item.tags}`.toLowerCase().includes(name.toLowerCase())).length} related knowledge records`} accent="green" />
                  <WorkItem title="History" detail={latest ? `${label(latest.status)} ${relativeTime(latest.completed_at || latest.started_at)}` : "No execution history"} accent="amber" />
                  <WorkItem title="Performance" detail={latest?.duration_ms ? `${latest.duration_ms}ms last run` : "No performance sample"} accent="violet" />
                </div>
              </article>
            );
          })}
        </div>
      </DarkPanel>
    </section>
  );
}

function IntegrationsPage({ connectors, enterpriseIntegrations, jiraStatus, onTest }) {
  const providers = ["GitHub", "Jira", "Gmail", "Calendar", "WhatsApp", "Meta", "Instagram", "LinkedIn", "VS Code", "Filesystem", "PostgreSQL", "MCP Runtime"];
  return (
    <section className="grid gap-6">
      <DarkPanel title="Integrations" subtitle="Health, authentication, capabilities, latency, and logs for every operating connector.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {providers.map((provider) => {
            const key = provider.toLowerCase().replaceAll(" ", "_");
            const connector = (connectors || []).find((item) => item.provider === key || item.name?.toLowerCase().includes(provider.toLowerCase()));
            const enterprise = (enterpriseIntegrations || []).find((item) => item.provider === key);
            const connected = connector?.connected || enterprise?.status === "connected" || (provider === "Jira" && jiraStatus?.connected);
            return (
              <article key={provider} className="rounded-[1.5rem] border border-slate-800 bg-slate-950/70 p-5">
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div><p className="text-lg font-bold text-white">{provider}</p><p className="text-xs text-slate-500">{connector?.message || enterprise?.auth_type || "Connector not configured in this environment"}</p></div>
                  <span className={`rounded-full px-2.5 py-1 text-[0.65rem] font-bold uppercase ${connected ? "bg-emerald-400/10 text-emerald-300" : "bg-rose-400/10 text-rose-300"}`}>{connected ? "healthy" : "needs auth"}</span>
                </div>
                <div className="space-y-3">
                  <WorkItem title="Authentication" detail={connector?.authentication_status || enterprise?.status || "not connected"} accent={connected ? "green" : "red"} />
                  <WorkItem title="Capabilities" detail={(connector?.capabilities || enterprise?.scopes || []).join(", ") || "No capabilities reported"} accent="violet" />
                  <WorkItem title="Latency" detail={connector?.latency_ms ? `${connector.latency_ms}ms` : "No latency sample"} accent="cyan" />
                  <WorkItem title="Logs" detail={connector?.last_sync ? `Last sync ${relativeTime(connector.last_sync)}` : "No log events returned"} accent="amber" />
                </div>
                {connector && <button onClick={() => onTest(connector.provider)} className="mt-4 min-h-10 w-full rounded-2xl border border-slate-800 bg-slate-900 px-4 text-sm font-bold text-slate-200">Test connection</button>}
              </article>
            );
          })}
        </div>
      </DarkPanel>
    </section>
  );
}

function AnalyticsPage({ data }) {
  const rows = [
    ["Business health", data.businessHealth?.customer_health?.score ?? data.commercialReadiness?.overall_score, "Current business health"],
    ["Pipeline", data.salesSummary?.pipeline_value ? `$${data.salesSummary.pipeline_value}` : undefined, "Sales pipeline value"],
    ["Marketing leads", data.marketingSummary?.leads, "Marketing generated leads"],
    ["Open tasks", data.tasks.filter((task) => task.status !== "completed").length, "Work not completed"],
    ["Approvals", data.planApprovals.length, "Founder decisions waiting"],
    ["Conversations", data.conversations.length, "Saved operating threads"],
  ].filter(([, value]) => value !== undefined && value !== null);
  return (
    <section className="grid gap-6">
      <DarkPanel title="Analytics" subtitle="Founder-facing operating analytics from live dashboard data.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map(([title, value, detail]) => <article key={title} className="rounded-[1.5rem] border border-slate-800 bg-slate-900/55 p-5"><p className="text-xs font-bold uppercase tracking-wider text-slate-500">{title}</p><p className="mt-5 font-display text-4xl font-semibold text-white">{value}</p><p className="mt-2 text-sm text-slate-500">{detail}</p></article>)}
        </div>
        {!rows.length && <DarkEmpty>No analytics are available until a business context returns data.</DarkEmpty>}
      </DarkPanel>
    </section>
  );
}

function FounderPage({ data, onAsk }) {
  return (
    <section className="grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
      <DarkPanel title="Founder" subtitle="Personal workspace for high-level decisions and operating cadence.">
        <div className="grid gap-3">
          {["Generate founder brief.", "Show risks I should decide today.", "Prepare customer meeting notes.", "Summarize this week's progress."].map((prompt) => <button key={prompt} onClick={() => onAsk(prompt)} className="min-h-11 rounded-2xl border border-slate-800 bg-slate-900 px-4 text-left text-sm font-bold text-slate-200">{prompt}</button>)}
        </div>
      </DarkPanel>
      <DarkPanel title="Founder Operating Log" subtitle="Recent conversations, goals, and approvals.">
        <div className="grid gap-4 md:grid-cols-3">
          <DarkList items={(data.conversations || []).slice(0, 5)} empty="No conversations yet." render={(item) => <WorkItem key={item.conversation_id} title={item.title} detail={relativeTime(item.updated_at)} accent="violet" />} />
          <DarkList items={(data.founderGoals || []).slice(0, 5)} empty="No founder goals yet." render={(item) => <WorkItem key={item.goal_id} title={item.title} detail={label(item.status)} accent="cyan" />} />
          <DarkList items={(data.planApprovals || []).slice(0, 5)} empty="No approvals waiting." render={(item) => <WorkItem key={item.approval_id} title={item.title} detail={label(item.risk_level)} accent="amber" />} />
        </div>
      </DarkPanel>
    </section>
  );
}

function SettingsPage({ data, diagnostics, failures }) {
  return (
    <section className="grid gap-6 xl:grid-cols-3">
      <DarkPanel title="Settings" subtitle="Administration is last in the IA.">
        <WorkItem title="Database" detail={diagnostics?.database_name || "Unknown database"} accent={diagnostics?.connected ? "green" : "red"} />
        <div className="mt-3"><WorkItem title="Scheduler" detail={diagnostics?.scheduler_status || "unknown"} accent="cyan" /></div>
        <div className="mt-3"><WorkItem title="API Failures" detail={`${failures.length} failed dashboard requests`} accent={failures.length ? "red" : "green"} /></div>
      </DarkPanel>
      <DarkPanel title="Security" subtitle="Auth, RBAC, and enterprise controls.">
        <WorkItem title="Users" detail={`${data.enterpriseUsers?.length || data.enterpriseDashboard?.users?.count || 0} users`} accent="violet" />
        <div className="mt-3"><WorkItem title="Tenants" detail={`${data.enterpriseTenants?.length || data.enterpriseDashboard?.tenant_health?.tenants || 0} tenants`} accent="cyan" /></div>
        <div className="mt-3"><WorkItem title="Audit" detail={`${data.enterpriseAudit?.length || data.enterpriseDashboard?.audit_activity?.events || 0} events`} accent="amber" /></div>
      </DarkPanel>
      <DarkPanel title="Migration Plan" subtitle="How the redesign maps old modules into Founder workflows.">
        {["Executive Dashboard replaces module-count homepage.", "Ask Pardha becomes the primary creation and command surface.", "Business context sits before administration.", "Agents, Marketing, Sales, Product Factory, Operations, Integrations, Analytics, Founder, and Settings are dedicated responsibilities."].map((item) => <WorkItem key={item} title={item} accent="green" />)}
      </DarkPanel>
    </section>
  );
}

function App() {
  const initialParams = new URLSearchParams(window.location.search);
  const initialUrlToken = initialParams.get("session");
  const initialPage = initialParams.get("page") || "Executive Dashboard";
  const [data, setData] = useState(initialData);
  const [apiStates, setApiStates] = useState({});
  const [authToken, setAuthToken] = useState(() => initialUrlToken || localStorage.getItem("pardha_session") || "");
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activeTab, setActiveTab] = useState(initialPage);
  const [activeBusinessId, setActiveBusinessId] = useState("");
  const [prompt, setPrompt] = useState("Improve customer retention by 15%");
  const [businessName, setBusinessName] = useState("");
  const [knowledgeTitle, setKnowledgeTitle] = useState("Customer Retention Context");
  const [knowledgeContent, setKnowledgeContent] = useState("Customers need clearer repeat purchase journeys, campaign follow-up, and support visibility.");
  const [knowledgeFiles, setKnowledgeFiles] = useState([]);
  const [knowledgeSearch, setKnowledgeSearch] = useState("");
  const [selectedKnowledge, setSelectedKnowledge] = useState(null);
  const [chatInput, setChatInput] = useState("What should I do next?");
  const [chatMessages, setChatMessages] = useState([]);
  const [conversationId, setConversationId] = useState("");
  const [conversationTimeline, setConversationTimeline] = useState([]);
  const [voiceState, setVoiceState] = useState("idle");
  const [voiceError, setVoiceError] = useState("");
  const [continuousVoice, setContinuousVoice] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [streamingEvents, setStreamingEvents] = useState([]);
  const recognitionRef = useRef(null);
  const startVoiceRef = useRef(null);
  const voiceTranscriptRef = useRef("");
  const voiceSubmittedRef = useRef(false);
  const continuousVoiceRef = useRef(false);
  const [goalTitle, setGoalTitle] = useState("Acquire 5 eCommerce Pilot Customers");
  const [factoryRequirement, setFactoryRequirement] = useState("We need QR tracking.");
  const [copilot, setCopilot] = useState(null);
  const [salesRequest, setSalesRequest] = useState("I want 50 eCommerce prospects");
  const [marketingRequest, setMarketingRequest] = useState("Launch campaign for cloud kitchens.");
  const [notice, setNotice] = useState("");
  const [authError, setAuthError] = useState("");
  const [theme, setTheme] = useState(() => localStorage.getItem("pardha_theme") || "light");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const activeBusiness = data.businesses.find((business) => business.business_id === activeBusinessId) || data.currentContext?.active_business;

  useEffect(() => {
    continuousVoiceRef.current = continuousVoice;
  }, [continuousVoice]);

  useEffect(() => {
    if (initialUrlToken) {
      localStorage.setItem("pardha_session", initialUrlToken);
      const next = new URL(window.location.href);
      next.searchParams.delete("session");
      window.history.replaceState({}, "", `${next.pathname}${next.search}`);
    }
  }, [initialUrlToken]);

  useEffect(() => {
    localStorage.setItem("pardha_theme", theme);
  }, [theme]);

  useEffect(() => {
    async function checkSession() {
      if (!authToken) {
        setAuthChecked(true);
        return;
      }
      try {
        const response = await fetch("/api/auth/session", { headers: { Authorization: `Bearer ${authToken}` } });
        const result = await response.json();
        if (result.authenticated) {
          setUser(result.user);
        } else {
          localStorage.removeItem("pardha_session");
          setAuthToken("");
        }
      } finally {
        setAuthChecked(true);
      }
    }
    checkSession();
  }, [authToken]);

  const refresh = useCallback(async () => {
    if (!authToken) return;
    const scopedId = activeBusinessId || data.currentContext?.active_business?.business_id || "";
    const results = await Promise.all(Object.entries(endpoints).map(async ([key, endpoint]) => {
      if (businessScoped.has(key) && !scopedId) {
        return { key, endpoint, value: initialData[key], state: "deferred", status: "waiting_for_business" };
      }
      const url = scopedId && businessScoped.has(key) ? `${endpoint}?business_id=${encodeURIComponent(scopedId)}` : endpoint;
      try {
        const response = await fetch(url);
        const value = await response.json();
        if (!response.ok) throw Object.assign(new Error(value?.detail || response.statusText), { status: response.status });
        return { key, endpoint: url, value, state: "success", status: response.status };
      } catch (error) {
        return { key, endpoint: url, value: initialData[key], state: "error", status: error.status || "network", message: error.message };
      }
    }));
    setData((current) => ({ ...current, ...Object.fromEntries(results.filter((item) => item.state === "success").map((item) => [item.key, item.value])) }));
    setApiStates(Object.fromEntries(results.map(({ key, endpoint, state, status, message }) => [key, { endpoint, state, status, message }])));
    const context = results.find((item) => item.key === "currentContext" && item.state === "success")?.value;
    if (!activeBusinessId && context?.active_business?.business_id) setActiveBusinessId(context.active_business.business_id);
    setLoading(false);
    setLastUpdated(new Date());
  }, [activeBusinessId, authToken, data.currentContext?.active_business?.business_id]);

  useEffect(() => {
    if (!authChecked || !authToken) return undefined;
    refresh();
    const interval = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(interval);
  }, [authChecked, authToken, refresh]);

  const loginUser = useCallback(async ({ email, password, rememberMe }) => {
    setAuthError("");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    });
    const result = await response.json();
    if (!response.ok) {
      setAuthError(result.detail || "Login failed.");
      return;
    }
    localStorage.setItem("pardha_session", result.token);
    setAuthToken(result.token);
    setUser(result.user);
    setAuthChecked(true);
    setNotice(`Good morning, ${result.user.full_name}.`);
  }, []);

  const logoutUser = useCallback(async () => {
    if (authToken) await fetch("/api/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${authToken}` } });
    localStorage.removeItem("pardha_session");
    setAuthToken("");
    setUser(null);
    setData(initialData);
  }, [authToken]);

  const loadDP360Demo = useCallback(async () => {
    setWorking(true);
    setNotice("");
    const response = await fetch("/api/commercial/demo/dp360", { method: "POST" });
    const result = await response.json();
    setActiveBusinessId(result.business_id);
    setNotice(`DP360 Demo loaded: ${result.counts.knowledge} knowledge records, ${result.counts.objectives} objectives, ${result.counts.tasks} tasks.`);
    await refresh();
    setWorking(false);
  }, [refresh]);

  const createBusiness = useCallback(async (event) => {
    event.preventDefault();
    if (!businessName.trim()) return;
    setWorking(true);
    const response = await fetch("/api/businesses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ business_name: businessName.trim(), business_type: "customer", description: `${businessName.trim()} customer workspace.` }),
    });
    const business = await response.json();
    setActiveBusinessId(business.business_id);
    await fetch("/api/context/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ business_id: business.business_id }),
    });
    setBusinessName("");
    setNotice(`Business created: ${business.business_name}`);
    await refresh();
    setWorking(false);
  }, [businessName, refresh]);

  const switchBusiness = useCallback(async (businessId) => {
    setActiveBusinessId(businessId);
    await fetch("/api/context/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ business_id: businessId }),
    });
    await refresh();
  }, [refresh]);

  const addKnowledge = useCallback(async (event) => {
    event.preventDefault();
    if (!activeBusiness || !knowledgeTitle.trim() || !knowledgeContent.trim()) return;
    setWorking(true);
    await fetch("/api/knowledge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        business_id: activeBusiness.business_id,
        business_name: activeBusiness.business_name,
        category: "company",
        title: knowledgeTitle.trim(),
        content: knowledgeContent.trim(),
        tags: ["customer-upload"],
        source: "dashboard-v1",
      }),
    });
    setNotice(`Knowledge added for ${activeBusiness.business_name}`);
    await refresh();
    setWorking(false);
  }, [activeBusiness, knowledgeContent, knowledgeTitle, refresh]);

  const uploadKnowledgeFiles = useCallback(async (reimport = false) => {
    if (!activeBusiness || knowledgeFiles.length === 0) return;
    setWorking(true);
    const form = new FormData();
    form.append("business_id", activeBusiness.business_id);
    form.append("business_name", activeBusiness.business_name);
    form.append("category", "company");
    form.append("reimport", reimport ? "true" : "false");
    knowledgeFiles.forEach((file) => form.append("files", file));
    const response = await fetch("/api/knowledge/upload", { method: "POST", body: form });
    const result = await response.json();
    setNotice(response.ok ? `Knowledge upload complete: ${result.uploaded} imported, ${result.duplicates} duplicates, ${result.failed} failed.` : result.detail || "Knowledge upload failed.");
    setKnowledgeFiles([]);
    await refresh();
    setWorking(false);
  }, [activeBusiness, knowledgeFiles, refresh]);

  const deleteKnowledgeItem = useCallback(async (knowledgeId) => {
    setWorking(true);
    const response = await fetch(`/api/knowledge/${knowledgeId}`, { method: "DELETE" });
    const result = await response.json();
    setNotice(response.ok ? "Knowledge deleted." : result.detail || "Unable to delete knowledge.");
    setSelectedKnowledge(null);
    await refresh();
    setWorking(false);
  }, [refresh]);

  const runCopilot = useCallback(async (event) => {
    event.preventDefault();
    if (!activeBusiness) return;
    setWorking(true);
    const response = await fetch("/api/copilot/founder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, business_name: activeBusiness.business_name, priority: "high" }),
    });
    const result = await response.json();
    setCopilot(result);
    setNotice(`Objective created for ${result.business_name}: ${result.workflow.objective.title}`);
    await refresh();
    setActiveTab("Objectives");
    setWorking(false);
  }, [activeBusiness, prompt, refresh]);

  const generateProspects = useCallback(async () => {
    setWorking(true);
    const response = await fetch("/api/sales/prospect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: salesRequest, target_count: 50, industries: ["eCommerce"] }),
    });
    const result = await response.json();
    setNotice(`Sales Executive generated ${result.generated_count} ${result.industry} prospects.`);
    await refresh();
    setActiveTab("Sales");
    setWorking(false);
  }, [refresh, salesRequest]);

  const viewSalesOutreach = useCallback(async (leadId) => {
    setWorking(true);
    const response = await fetch(`/api/sales/leads/${leadId}/outreach`);
    const result = await response.json();
    if (!response.ok) {
      setNotice(result.detail || "Unable to load outreach package.");
    } else {
      const firstLine = (result.cold_email || "").split("\n")[0];
      setNotice(`${result.company} outreach ready: ${firstLine}`);
    }
    setWorking(false);
  }, []);

  const scheduleSalesDemo = useCallback(async (leadId) => {
    setWorking(true);
    const response = await fetch(`/api/sales/leads/${leadId}/schedule-demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ owner: "Founder", meeting_url: "https://meet.pardha.local/dp360-demo" }),
    });
    const result = await response.json();
    setNotice(response.ok ? `${result.company} demo scheduled. Calendar invite generated.` : result.detail || "Unable to schedule demo.");
    await refresh();
    setWorking(false);
  }, [refresh]);

  const moveSalesStage = useCallback(async (leadId, status) => {
    setWorking(true);
    const response = await fetch(`/api/sales/leads/${leadId}/stage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    const result = await response.json();
    setNotice(response.ok ? `${result.company} moved to ${label(result.status)}.` : result.detail || "Unable to update sales stage.");
    await refresh();
    setWorking(false);
  }, [refresh]);

  const launchMarketingCampaign = useCallback(async () => {
    setWorking(true);
    const response = await fetch("/api/marketing/campaign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: marketingRequest,
        industry: "Cloud Kitchens",
        duration_days: 30,
        budget: 25000,
        channels: ["LinkedIn", "Google Ads", "Meta Ads", "Email Campaigns", "Website Content", "SEO", "Webinars"],
      }),
    });
    const result = await response.json();
    setNotice(response.ok ? `Marketing Executive launched ${result.campaign.name} with ${result.content_calendar.length} planned calendar items.` : result.detail || "Unable to launch marketing campaign.");
    await refresh();
    setActiveTab("Marketing");
    setWorking(false);
  }, [marketingRequest, refresh]);

  const onboardCustomer = useCallback(async () => {
    setWorking(true);
    const name = businessName.trim() || "Pilot Customer";
    const response = await fetch("/api/copilot/onboarding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_name: name, business_type: "customer", description: `${name} customer pilot workspace.`, revenue_goal: 500000 }),
    });
    const result = await response.json();
    if (response.ok) {
      setActiveBusinessId(result.business_id);
      setNotice(`${result.company_name} onboarded in ${result.estimated_minutes} minutes. Dashboard ready: ${result.dashboard_ready ? "yes" : "no"}.`);
      setActiveTab("Customer Success");
    } else {
      setNotice(result.detail || "Unable to onboard customer.");
    }
    await refresh();
    setWorking(false);
  }, [businessName, refresh]);

  const loadDemoWorkspace = useCallback(async (template) => {
    setWorking(true);
    const response = await fetch("/api/copilot/demo-library/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template }),
    });
    const result = await response.json();
    if (response.ok) {
      setActiveBusinessId(result.business_id);
      setNotice(`${result.business_name} demo workspace loaded with ${result.counts.objectives} objectives and ${result.counts.tasks} tasks.`);
      setActiveTab("Presentation");
    } else {
      setNotice(result.detail || "Unable to load demo workspace.");
    }
    await refresh();
    setWorking(false);
  }, [refresh]);

  const testConnector = useCallback(async (provider) => {
    setWorking(true);
    const response = await fetch(`/api/commercial/connectors/${provider}/test`, { method: "POST" });
    const result = await response.json();
    setNotice(`${label(provider)} test: ${result.status}. ${result.message}`);
    await refresh();
    setWorking(false);
  }, [refresh]);

  const speakResponse = useCallback((text) => {
    if (!text || !("speechSynthesis" in window)) {
      setVoiceState("completed");
      return;
    }
    window.speechSynthesis.cancel();
    setVoiceState("speaking");
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    utterance.pitch = 0.92;
    utterance.onend = () => {
      setVoiceState("completed");
      if (continuousVoiceRef.current) setTimeout(() => startVoiceRef.current?.(), 600);
    };
    utterance.onerror = () => {
      setVoiceState("error");
      setVoiceError("Speech output failed. You can continue by text or restart voice.");
      if (continuousVoiceRef.current) setTimeout(() => startVoiceRef.current?.(), 1200);
    };
    window.speechSynthesis.speak(utterance);
  }, []);

  const applyConversationResult = useCallback((result, shouldSpeak = false) => {
    setConversationId(result.conversation?.conversation_id || "");
    setChatMessages((current) => [...current, result.user_message, result.assistant_message]);
    setConversationTimeline(result.timeline || []);
    setChatInput("");
    setNotice(`Conversation handled by ${result.assistant_message.capability_ids?.join(", ") || "context resolver"}`);
    if (shouldSpeak) speakResponse(result.assistant_message.content);
    else setVoiceState("completed");
  }, [speakResponse]);

  const sendConversationMessage = useCallback(async (event, overrideMessage, options = {}) => {
    event?.preventDefault?.();
    const message = (overrideMessage || chatInput).trim();
    if (!message || !activeBusiness) return;
    setWorking(true);
    setStreamingEvents([]);
    setVoiceState("thinking");
    const path = conversationId ? `/api/conversations/${conversationId}/stream` : "/api/conversations/stream";
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ business_id: activeBusiness.business_id, message, module_context: activeTab }),
    });
    if (response.ok) {
      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalResult = null;
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (!line.trim()) continue;
            const eventChunk = JSON.parse(line);
            setStreamingEvents((current) => [...current, eventChunk]);
            if (eventChunk.phase) setVoiceState(eventChunk.phase === "completed" ? "completed" : eventChunk.phase);
            if (eventChunk.result) finalResult = eventChunk.result;
          }
        }
        if (buffer.trim()) {
          const eventChunk = JSON.parse(buffer);
          setStreamingEvents((current) => [...current, eventChunk]);
          if (eventChunk.result) finalResult = eventChunk.result;
        }
        if (finalResult) applyConversationResult(finalResult, options.speak);
      }
    } else {
      const result = await response.json();
      setNotice(result.detail || "Pardha could not process the request.");
      setVoiceState("idle");
    }
    await refresh();
    setWorking(false);
  }, [activeBusiness, activeTab, applyConversationResult, chatInput, conversationId, refresh]);

  const openConversation = useCallback(async (nextConversationId) => {
    if (!nextConversationId) return;
    setWorking(true);
    const response = await fetch(`/api/conversations/${nextConversationId}`);
    const result = await response.json();
    if (response.ok) {
      setConversationId(result.conversation.conversation_id);
      setChatMessages(result.messages || []);
      setConversationTimeline(result.timeline || []);
      if (result.conversation.business_id) setActiveBusinessId(result.conversation.business_id);
      setNotice(`Conversation restored: ${result.conversation.title}`);
    } else {
      setNotice(result.detail || "Unable to restore conversation.");
    }
    setWorking(false);
  }, []);

  const patchConversation = useCallback(async (nextConversationId, patch) => {
    if (!nextConversationId) return;
    setWorking(true);
    const response = await fetch(`/api/conversations/${nextConversationId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    const result = await response.json();
    setNotice(response.ok ? `Conversation updated: ${result.title}` : result.detail || "Unable to update conversation.");
    await refresh();
    setWorking(false);
  }, [refresh]);

  const deleteConversationAction = useCallback(async (nextConversationId) => {
    if (!nextConversationId) return;
    setWorking(true);
    const response = await fetch(`/api/conversations/${nextConversationId}`, { method: "DELETE" });
    const result = await response.json();
    if (response.ok) {
      if (conversationId === nextConversationId) {
        setConversationId("");
        setChatMessages([]);
        setConversationTimeline([]);
      }
      setNotice("Conversation deleted.");
    } else {
      setNotice(result.detail || "Unable to delete conversation.");
    }
    await refresh();
    setWorking(false);
  }, [conversationId, refresh]);

  const exportConversationAction = useCallback(async (nextConversationId) => {
    if (!nextConversationId) return;
    const response = await fetch(`/api/conversations/${nextConversationId}/export`);
    const result = await response.json();
    setNotice(response.ok ? `Export ready: ${result.messages.length} messages and ${result.timeline.length} timeline events.` : result.detail || "Unable to export conversation.");
  }, []);

  const submitVoiceTranscript = useCallback((source = "voice") => {
    const transcript = voiceTranscriptRef.current.trim();
    if (!transcript) {
      setNotice(source === "stop" ? "No voice transcript was captured." : "I did not hear anything clearly.");
      setVoiceState("idle");
      return;
    }
    if (voiceSubmittedRef.current) return;
    voiceSubmittedRef.current = true;
    setInterimTranscript(transcript);
    sendConversationMessage(null, transcript, { speak: true });
  }, [sendConversationMessage]);

  const startVoice = useCallback(async () => {
    setVoiceError("");
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setVoiceError("Speech recognition is not available in this browser.");
      setVoiceState("error");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setVoiceError("Microphone access is not available in this browser.");
      setVoiceState("error");
      return;
    }
    if (!activeBusiness) {
      setVoiceError("Select a business before using voice.");
      setVoiceState("error");
      return;
    }
    window.speechSynthesis?.cancel?.();
    recognitionRef.current?.abort?.();
    voiceTranscriptRef.current = "";
    voiceSubmittedRef.current = false;
    setVoiceState("wake");
    setInterimTranscript(`Wake / ${activeTab}`);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
    } catch (error) {
      const message = error?.name === "NotAllowedError" ? "Microphone permission was denied. Allow microphone access for this site and try again." : `Microphone access failed: ${error?.message || error?.name || "unknown error"}`;
      setVoiceError(message);
      setInterimTranscript("");
      setVoiceState("error");
      return;
    }
    const recognition = new Recognition();
    recognition.continuous = continuousVoiceRef.current;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onstart = () => {
      setVoiceState("listening");
      setInterimTranscript("Listening...");
    };
    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let index = 0; index < event.results.length; index += 1) {
        const text = event.results[index][0].transcript;
        if (event.results[index].isFinal) finalText += text;
        else interimText += text;
      }
      const transcript = `${finalText} ${interimText}`.trim();
      voiceTranscriptRef.current = transcript;
      setVoiceState(finalText.trim() ? "transcribing" : "listening");
      setInterimTranscript(transcript || "Listening...");
      if (finalText.trim()) {
        recognition.stop();
        submitVoiceTranscript("final");
      }
    };
    recognition.onerror = (event) => {
      setVoiceError(`Voice input failed: ${event.error}`);
      setInterimTranscript("");
      setVoiceState("error");
      if (continuousVoiceRef.current && event.error !== "not-allowed") setTimeout(() => startVoiceRef.current?.(), 1200);
    };
    recognition.onend = () => {
      if (!voiceSubmittedRef.current && voiceTranscriptRef.current.trim()) {
        submitVoiceTranscript("end");
        return;
      }
      setVoiceState((current) => current === "listening" ? "idle" : current);
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (error) {
      setVoiceError(`Voice input failed to start: ${error?.message || "unknown error"}`);
      setInterimTranscript("");
      setVoiceState("error");
    }
  }, [activeBusiness, activeTab, submitVoiceTranscript]);

  useEffect(() => {
    startVoiceRef.current = startVoice;
  }, [startVoice]);

  const stopVoice = useCallback(() => {
    recognitionRef.current?.abort?.();
    window.speechSynthesis?.cancel?.();
    voiceSubmittedRef.current = false;
    voiceTranscriptRef.current = "";
    setInterimTranscript("");
    setVoiceState("idle");
    setVoiceError("");
  }, [submitVoiceTranscript]);

  const createFounderGoal = useCallback(async (event) => {
    event.preventDefault();
    if (!activeBusiness || !goalTitle.trim()) return;
    setWorking(true);
    const response = await fetch("/api/chief/goals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        business_id: activeBusiness.business_id,
        title: goalTitle.trim(),
        priority: "high",
        owner: "Founder",
        success_metrics: ["Owner assigned", "Tasks generated", "Daily follow-up reviewed"],
      }),
    });
    const result = await response.json();
    setNotice(response.ok ? `Goal created: ${result.title}` : result.detail || "Unable to create goal.");
    await refresh();
    setWorking(false);
  }, [activeBusiness, goalTitle, refresh]);

  const approvePlan = useCallback(async (planId) => {
    setWorking(true);
    const response = await fetch(`/api/planning/plans/${planId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decided_by: user?.full_name || "Founder", comment: "Approved from dashboard." }),
    });
    setNotice(response.ok ? "Plan approved." : "Unable to approve plan.");
    await refresh();
    setWorking(false);
  }, [refresh, user]);

  const rejectPlan = useCallback(async (planId) => {
    setWorking(true);
    const response = await fetch(`/api/planning/plans/${planId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decided_by: user?.full_name || "Founder", comment: "Rejected from Approval Center." }),
    });
    setNotice(response.ok ? "Plan rejected." : "Unable to reject plan.");
    await refresh();
    setWorking(false);
  }, [refresh, user]);

  const executePlan = useCallback(async (planId) => {
    setWorking(true);
    const response = await fetch(`/api/planning/plans/${planId}/execute`, { method: "POST" });
    const result = await response.json();
    setNotice(response.ok ? `Plan execution ${label(result.status)} at ${result.progress}%` : result.detail || "Unable to execute plan.");
    await refresh();
    setWorking(false);
  }, [refresh]);

  const startRuntimeExecution = useCallback(async (planId) => {
    if (!activeBusiness) return;
    setWorking(true);
    const response = await fetch("/api/runtime/executions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ business_id: activeBusiness.business_id, plan_id: planId, priority: 80 }),
    });
    const result = await response.json();
    setNotice(response.ok ? `Runtime execution queued: ${short(result.execution_id, 12)}` : result.detail || "Unable to queue runtime execution.");
    await refresh();
    setWorking(false);
  }, [activeBusiness, refresh]);

  const processRuntimeQueue = useCallback(async () => {
    if (!activeBusiness) return;
    setWorking(true);
    const response = await fetch(`/api/runtime/queue/process?business_id=${activeBusiness.business_id}`, { method: "POST" });
    const result = await response.json();
    setNotice(response.ok ? `Processed ${result.length} runtime item${result.length === 1 ? "" : "s"}.` : result.detail || "Unable to process queue.");
    await refresh();
    setWorking(false);
  }, [activeBusiness, refresh]);

  const rollbackRuntimeExecution = useCallback(async (executionId) => {
    setWorking(true);
    const response = await fetch(`/api/runtime/executions/${executionId}/rollback`, { method: "POST" });
    setNotice(response.ok ? "Runtime execution rolled back." : "Unable to rollback execution.");
    await refresh();
    setWorking(false);
  }, [refresh]);

  const createFactoryDelivery = useCallback(async (event) => {
    event.preventDefault();
    if (!activeBusiness || !factoryRequirement.trim()) return;
    setWorking(true);
    const response = await fetch("/api/software-factory/requirements", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        business_id: activeBusiness.business_id,
        requirement: factoryRequirement.trim(),
        requester: user?.full_name || "Founder",
        methodology: "scrum",
      }),
    });
    const result = await response.json();
    setNotice(response.ok ? `Software Factory generated ${result.artifacts.length} artifacts and ${result.approvals.length} approval gates.` : result.detail || "Unable to create software factory package.");
    await refresh();
    setActiveTab("Product Factory");
    setWorking(false);
  }, [activeBusiness, factoryRequirement, refresh, user]);

  const decideFactoryApproval = useCallback(async (approvalId, decision) => {
    setWorking(true);
    const response = await fetch(`/api/software-factory/approvals/${approvalId}/${decision}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decided_by: user?.full_name || "Founder", comment: `${label(decision)} from Product Factory.` }),
    });
    const result = await response.json();
    setNotice(response.ok ? `Factory approval ${decision}.` : result.detail || "Unable to update approval.");
    await refresh();
    setWorking(false);
  }, [refresh, user]);

  const controlModel = useCallback(async (action, model) => {
    setWorking(true);
    const response = await fetch(modelManagerEndpoints[action], {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    const result = await response.json();
    setNotice(response.ok ? `${label(result.model)} ${result.status}: ${result.message}` : result.detail || "Unable to update model runtime.");
    await refresh();
    setWorking(false);
  }, [refresh]);

  const failures = Object.entries(apiStates).filter(([, state]) => state.state === "error");
  const counts = data.founder?.counts || data.currentContext?.counts || {};
  const openTasks = data.tasks.filter((task) => task.status !== "completed");
  const recentFlow = useMemo(() => data.collaborations.slice(0, 12).sort((a, b) => new Date(b.created_at || b.timestamp) - new Date(a.created_at || a.timestamp)), [data.collaborations]);
  const connectorFailures = data.connectors.filter((item) => !item.connected);

  const openAsk = (promptText = "") => {
    setActiveTab("Ask Pardha");
    if (promptText) setChatInput(promptText);
  };

  const pages = {
    "Executive Dashboard": <ExecutiveDashboardPage user={user} data={data} activeBusiness={activeBusiness} onAsk={openAsk} onVoice={startVoice} onApprove={approvePlan} onReject={rejectPlan} working={working} voiceState={voiceState} />,
    "Ask Pardha": <AskPardhaTab data={data} activeBusiness={activeBusiness} activeConversationId={conversationId} messages={chatMessages} conversations={data.conversations} timeline={conversationTimeline} input={chatInput} setInput={setChatInput} onSend={sendConversationMessage} working={working} voiceState={voiceState} interimTranscript={interimTranscript} streamingEvents={streamingEvents} onVoiceStart={startVoice} onVoiceStop={stopVoice} onOpenConversation={openConversation} onPatchConversation={patchConversation} onDeleteConversation={deleteConversationAction} onExportConversation={exportConversationAction} />,
    Businesses: <BusinessesPage data={data} activeBusiness={activeBusiness} businessName={businessName} setBusinessName={setBusinessName} createBusiness={createBusiness} switchBusiness={switchBusiness} working={working} />,
    Agents: <AgentsPage data={data} />,
    Knowledge: <KnowledgeTab knowledge={data.knowledge} imports={data.knowledgeImports} onSubmit={addKnowledge} title={knowledgeTitle} setTitle={setKnowledgeTitle} content={knowledgeContent} setContent={setKnowledgeContent} files={knowledgeFiles} setFiles={setKnowledgeFiles} onUpload={uploadKnowledgeFiles} onDelete={deleteKnowledgeItem} search={knowledgeSearch} setSearch={setKnowledgeSearch} selected={selectedKnowledge} setSelected={setSelectedKnowledge} working={working} />,
    Marketing: <MarketingVoicePage dashboard={data.marketingDashboard} campaigns={data.marketingCampaigns} analytics={data.marketingAnalytics} content={data.marketingContent} summary={data.marketingSummary} request={marketingRequest} setRequest={setMarketingRequest} onLaunch={launchMarketingCampaign} working={working} activeBusiness={activeBusiness} voiceState={voiceState} onVoiceStart={startVoice} onVoiceStop={stopVoice} interimTranscript={interimTranscript} voiceError={voiceError} messages={chatMessages} streamingEvents={streamingEvents} approvals={data.planApprovals} ollama={data.ollama} validation={data.voiceValidation} />,
    Sales: <SalesTab dashboard={data.salesDashboard} leads={data.salesLeads} pipeline={data.salesPipeline} demos={data.salesDemos} summary={data.salesSummary} request={salesRequest} setRequest={setSalesRequest} onGenerate={generateProspects} onViewOutreach={viewSalesOutreach} onScheduleDemo={scheduleSalesDemo} onMoveStage={moveSalesStage} working={working} />,
    "Product Factory": <SoftwareFactoryTab deliveries={data.softwareFactoryDeliveries} dashboard={data.softwareFactoryDashboard} validation={data.softwareFactoryValidation} requirement={factoryRequirement} setRequirement={setFactoryRequirement} onCreate={createFactoryDelivery} onDecide={decideFactoryApproval} working={working} />,
    Operations: <RuntimeTab dashboard={data.runtimeDashboard} plans={data.executionPlans} executions={data.runtimeExecutions} queue={data.runtimeQueue} notifications={data.runtimeNotifications} departments={data.runtimeDepartments} onStart={startRuntimeExecution} onProcess={processRuntimeQueue} onRollback={rollbackRuntimeExecution} working={working} />,
    Integrations: <IntegrationsPage connectors={data.connectors} enterpriseIntegrations={data.enterpriseIntegrations} jiraStatus={data.jiraStatus} onTest={testConnector} />,
    Analytics: <AnalyticsPage data={data} />,
    Founder: <FounderPage data={data} onAsk={openAsk} />,
    Settings: <SettingsPage data={data} diagnostics={data.diagnostics} failures={failures} />,
  };

  if (!authChecked) {
    return <div className="grid min-h-screen place-items-center bg-canvas text-sm font-semibold text-ink/55">Loading secure session...</div>;
  }

  if (!authToken || !user) {
    return <LoginPage onLogin={loginUser} error={authError} />;
  }

  return (
    <WorkspaceShell
      user={user}
      activePage={activeTab}
      setActivePage={setActiveTab}
      activeBusinessId={activeBusinessId}
      businesses={data.businesses}
      onSwitchBusiness={switchBusiness}
      onRefresh={refresh}
      onLogout={logoutUser}
      onLoadDemo={loadDP360Demo}
      working={working}
      notice={notice}
      failures={failures}
      lastUpdated={lastUpdated}
      voiceState={voiceState}
      onVoiceStart={startVoice}
      onVoiceStop={stopVoice}
      continuousVoice={continuousVoice}
      onToggleContinuousVoice={() => setContinuousVoice((current) => !current)}
      voiceError={voiceError}
      interimTranscript={interimTranscript}
      ollama={data.ollama}
      voiceValidation={data.voiceValidation}
      onModelStart={(model) => controlModel("start", model)}
      onModelStop={(model) => controlModel("stop", model)}
      onModelSwitch={(model) => controlModel("switch", model)}
      pageOwnsVoice={activeTab === "Marketing"}
    >
      {pages[activeTab] || pages["Executive Dashboard"]}
    </WorkspaceShell>
  );
}

function FounderTab({ data, conversations, onPrompt }) {
  const founder = data.founder;
  const health = data.businessHealth;
  return (
    <section className="grid gap-5 xl:grid-cols-3">
      <Panel title="Quick actions" subtitle="Operate from the Founder workspace.">
        <div className="grid gap-2">
          {["What should I do next?", "Generate today's CEO report.", "What integrations are missing?", "Summarize engineering progress."].map((item) => <ShellButton key={item} onClick={() => onPrompt(item)}>{item}</ShellButton>)}
        </div>
      </Panel>
      <Panel title="Today's priorities" subtitle="Highest-value operating focus.">
        <List items={founder?.todays_priorities} empty="No priorities available." render={(item, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm">{item}</p>} />
      </Panel>
      <Panel title="Approvals waiting" subtitle="Founder decisions required.">
        <List items={data.planApprovals?.slice(0, 5)} empty="No approvals waiting." render={(item) => <p key={item.approval_id} className="rounded-xl bg-coral/10 px-4 py-3 text-sm text-coral"><strong>{item.title}</strong><span className="block text-xs">{label(item.risk_level)} / {label(item.status)}</span></p>} />
      </Panel>
      <Panel title="Notifications" subtitle="Unread operational signals.">
        <List items={data.runtimeNotifications?.filter((item) => item.status === "unread").slice(0, 5)} empty="No unread notifications." render={(item) => <p key={item.notification_id} className="rounded-xl bg-acid/40 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{label(item.category)} / {relativeTime(item.created_at)}</span></p>} />
      </Panel>
      <Panel title="Business health" subtitle="Operating health across functions.">
        <div className="grid gap-3">
          <StateCard title="Customer Health" ok={(health?.customer_health?.score || 0) >= 70} value={health?.customer_health?.score || 0} />
          <StateCard title="Risk Score" ok={(health?.risk_score || 0) < 35} value={health?.risk_score ?? 0} />
          <StateCard title="Operational Health" ok={health?.operational_health?.status === "operational"} value={label(health?.operational_health?.status || "unknown")} />
        </div>
      </Panel>
      <Panel title="Recent conversations" subtitle="Latest Chief of Staff interactions.">
        <List items={conversations?.slice(0, 5)} empty="No conversations yet. Ask Pardha a question." render={(item) => <p key={item.conversation_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{short(item.last_message || "", 90)}</span></p>} />
      </Panel>
      <Panel title="Engineering status" subtitle={founder?.engineering_status || "No engineering signal yet."}>
        <List items={founder?.recent_executions} empty="No recent executions." render={(item, index) => <p key={index} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.agent_name}</strong><span className="block text-xs text-ink/45">{label(item.status)} / {item.duration_ms || 0}ms</span></p>} />
      </Panel>
      <Panel title="Open risks" subtitle="Risks and connector gaps.">
        <List items={founder?.open_risks} empty="No open risks." render={(item, index) => <p key={index} className="rounded-xl bg-coral/10 px-4 py-3 text-sm text-coral">{item}</p>} />
      </Panel>
      <Panel title="Sales pipeline" subtitle="Communication-derived sales signals.">
        <List items={founder?.sales_pipeline} empty="No sales signals connected." render={(item, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm">{item}</p>} />
      </Panel>
      <Panel title="Marketing summary" subtitle={founder?.marketing_summary || "Marketing signals unavailable."}>
        <List items={founder?.active_objectives} empty="No active objectives." render={(item) => <p key={item.objective_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{label(item.priority)} / {label(item.status)}</span></p>} />
      </Panel>
      <Panel title="Department runtime" subtitle="Current department health and load.">
        <List items={data.runtimeDepartments?.slice(0, 9)} empty="No department runtime yet." render={(dept) => <p key={dept.department_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{dept.name}</strong><span className="block text-xs text-ink/45">{label(dept.health)} / load {dept.current_load}</span></p>} />
      </Panel>
      <Panel title="Recent agent activity" subtitle="Latest business-scoped events.">
        <List items={founder?.recent_agent_activity} empty="No recent activity." render={(item, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{label(item.event_type)}</strong><span className="block text-xs text-ink/45">{item.source_agent} to {item.target_agent}</span></p>} />
      </Panel>
      <Panel title="Current sprint" subtitle="Execution plans and runtime progress.">
        <List items={data.executionPlans?.slice(0, 4)} empty="No active sprint plan." render={(plan) => <p key={plan.plan_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{plan.title}</strong><span className="block text-xs text-ink/45">{label(plan.status)} / {plan.progress}% / {plan.nodes?.length || 0} nodes</span></p>} />
      </Panel>
    </section>
  );
}

function IntelligenceOrb({ state }) {
  return (
    <div className={`orb orb-${state}`}>
      <div className="orb-core" />
      <span className="orb-label">{label(state)}</span>
    </div>
  );
}

function AskPardhaTab({ data, activeBusiness, activeConversationId, messages, conversations, timeline, input, setInput, onSend, working, voiceState, interimTranscript, streamingEvents, onVoiceStart, onVoiceStop, onOpenConversation, onPatchConversation, onDeleteConversation, onExportConversation }) {
  const suggestions = ["We need five eCommerce pilot customers.", "Review DP360.", "Create a marketing strategy.", "Generate today's CEO report.", "Build Jira sprint.", "Create PRD for EatOnTime.", "Summarize engineering progress.", "Review customer risks."];
  const lastResponse = [...messages].reverse().find((message) => message.role === "assistant")?.response_payload;
  const [historySearch, setHistorySearch] = useState("");
  const filteredConversations = (conversations || []).filter((item) => `${item.title} ${item.summary}`.toLowerCase().includes(historySearch.toLowerCase()));
  const connected = (data.connectors || []).filter((item) => item.connected);
  const currentGoal = data.planningGoals?.[0] || data.founderGoals?.[0];
  const currentPlan = data.executionPlans?.[0];
  const openTasks = (data.tasks || []).filter((task) => task.status !== "completed").slice(0, 5);
  const recentActivity = [...(data.runtimeNotifications || []), ...(data.events || [])].slice(0, 6);
  return (
    <section className="grid gap-5 xl:grid-cols-[0.72fr_1.42fr_0.86fr]">
      <div className="grid content-start gap-5">
        <Panel title="Conversation History" subtitle={`${filteredConversations.length} saved conversation${filteredConversations.length === 1 ? "" : "s"}.`}>
          <input value={historySearch} onChange={(event) => setHistorySearch(event.target.value)} className="mb-3 min-h-10 w-full rounded-xl border border-ink/10 px-3 text-sm outline-none" placeholder="Search history" />
          <List items={filteredConversations.slice(0, 14)} empty="No saved conversations for this business yet." render={(item) => (
            <article key={item.conversation_id} className={`rounded-xl border px-3 py-3 text-sm ${item.conversation_id === activeConversationId ? "border-ink bg-ink text-white" : "border-ink/10 bg-white"}`}>
              <button onClick={() => onOpenConversation(item.conversation_id)} className="w-full text-left">
                <strong className="block">{item.title}</strong>
                <span className={`mt-1 block text-xs ${item.conversation_id === activeConversationId ? "text-white/55" : "text-ink/45"}`}>{label(item.conversation_type)} / {relativeTime(item.updated_at)}</span>
              </button>
              <div className="mt-3 flex flex-wrap gap-2">
                <button onClick={() => onPatchConversation(item.conversation_id, { pinned: !item.pinned })} className={`rounded-full px-2.5 py-1 text-[0.65rem] font-bold ${item.pinned ? "bg-acid text-ink" : "bg-ink/[0.06] text-ink/55"}`}>{item.pinned ? "Pinned" : "Pin"}</button>
                <button onClick={() => onExportConversation(item.conversation_id)} className="rounded-full bg-ink/[0.06] px-2.5 py-1 text-[0.65rem] font-bold text-ink/55">Export</button>
                <button onClick={() => onDeleteConversation(item.conversation_id)} className="rounded-full bg-coral/10 px-2.5 py-1 text-[0.65rem] font-bold text-coral">Delete</button>
              </div>
            </article>
          )} />
        </Panel>
        <Panel title="Pinned" subtitle="High-value operating threads.">
          <List items={(conversations || []).filter((item) => item.pinned).slice(0, 5)} empty="Pin executive conversations for quick restore." render={(item) => <button key={item.conversation_id} onClick={() => onOpenConversation(item.conversation_id)} className="w-full rounded-xl bg-acid/40 px-3 py-3 text-left text-sm font-semibold">{item.title}</button>} />
        </Panel>
      </div>

      <Panel title="Executive Conversation" subtitle="Conversation Engine with streaming timeline, business memory, registry routing, and verification.">
        <div className="mb-4 grid gap-4 md:grid-cols-[auto_1fr]">
          <IntelligenceOrb state={voiceState} />
          <div className="rounded-2xl bg-ink p-4 text-white">
            <p className="text-xs font-bold uppercase tracking-wider text-white/45">Voice Intelligence</p>
            <p className="mt-2 text-sm text-white/70">{interimTranscript || streamingEvents.at(-1)?.message || "Push to talk. Pardha will transcribe, stream phases, respond, and speak the result when browser voice APIs are available."}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <ShellButton disabled={working || voiceState === "listening"} onClick={onVoiceStart}>Push To Talk</ShellButton>
              <ShellButton disabled={voiceState === "idle"} onClick={onVoiceStop}>Interrupt</ShellButton>
            </div>
          </div>
        </div>
        <div className="mb-4 min-h-[24rem] space-y-3 rounded-2xl bg-ink/[0.025] p-4">
          {messages.length === 0 ? <EmptyState>Ask Pardha to create plans, summarize briefs, review risks, or operate sales and marketing.</EmptyState> : messages.map((message) => (
            <article key={message.message_id} className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === "user" ? "ml-auto bg-ink text-white" : "bg-white"}`}>
              <p className="text-[0.65rem] font-bold uppercase tracking-wider opacity-50">{message.role} / {label(message.intent)}</p>
              <p className="mt-1">{message.content}</p>
            </article>
          ))}
        </div>
        <form onSubmit={onSend} className="flex flex-col gap-2 md:flex-row">
          <input value={input} onChange={(event) => setInput(event.target.value)} className="min-h-11 flex-1 rounded-xl border border-ink/10 px-4 text-sm outline-none" placeholder="Talk to Pardha..." />
          <ShellButton dark disabled={working}>Send</ShellButton>
        </form>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {suggestions.slice(0, 4).map((item) => <button key={item} disabled={working} onClick={() => setInput(item)} className="rounded-xl border border-ink/10 bg-white px-3 py-2 text-left text-xs font-semibold text-ink/70">{item}</button>)}
        </div>
      </Panel>

      <div className="grid gap-5">
        <Panel title="Operating Context" subtitle={activeBusiness?.business_name || "No active business selected."}>
          <div className="grid gap-3">
            <StateCard title="Conversation Engine" ok={Boolean(data.conversationStatus?.ready)} value={data.conversationStatus?.ready ? "ready" : "checking"} detail={`${data.conversationStatus?.conversations?.messages || messages.length} persisted messages`} />
            <StateCard title="Database" ok={Boolean(data.diagnostics?.connected)} value={data.diagnostics?.database_name || "unknown"} detail={data.diagnostics?.scheduler_status || "scheduler unknown"} />
            <StateCard title="Ollama" ok={Boolean(data.ollama?.connected)} value={data.ollama?.connected ? data.ollama.model || "connected" : "on demand"} detail={data.ollama?.message || "Reasoning runs only when requested."} />
          </div>
        </Panel>
        <Panel title="Connected Services" subtitle={`${connected.length}/${data.connectors?.length || 0} live-authenticated.`}>
          <List items={(data.connectors || []).slice(0, 8)} empty="Connector status endpoint has not returned yet." render={(item) => <p key={item.provider} className={`rounded-xl px-4 py-3 text-sm ${item.connected ? "bg-green-50 text-green-700" : "bg-coral/10 text-coral"}`}><strong>{item.name}</strong><span className="block text-xs">{label(item.health)} / {label(item.authentication_status)}{item.missing_environment?.length ? ` / missing ${item.missing_environment.length}` : ""}</span></p>} />
        </Panel>
        <Panel title="Current Goal & Sprint" subtitle="Planner context visible during conversation.">
          <List items={[currentGoal, currentPlan].filter(Boolean)} empty="No active goal or sprint plan yet." render={(item, index) => <p key={item.goal_id || item.plan_id || index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{label(item.status || item.current_status)}{item.progress !== undefined ? ` / ${item.progress}%` : ""}</span></p>} />
        </Panel>
        <Panel title="Open Tasks" subtitle={`${openTasks.length} visible work items.`}>
          <List items={openTasks} empty="No open tasks for this business." render={(item) => <p key={item.task_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{label(item.status)} / {item.owner || item.agent_name || "unassigned"}</span></p>} />
        </Panel>
        <Panel title="Capability timeline" subtitle="Question to intent to execution to verification.">
          <List items={(timeline || []).slice(-8)} empty="No timeline yet." render={(item) => <p key={item.timeline_event_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{label(item.event_type)}</strong><span className="block text-xs text-ink/45">{short(item.detail, 110)}</span></p>} />
        </Panel>
        <Panel title="Execution Transparency" subtitle="Evidence and internals stay here unless you ask for details.">
          {lastResponse?.transparency ? (
            <div className="grid gap-2 text-sm">
              <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Intent</strong><span className="block text-xs text-ink/45">{label(lastResponse.transparency.intent || "unknown")}</span></p>
              <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Confidence</strong><span className="block text-xs text-ink/45">{lastResponse.transparency.confidence || lastResponse.confidence}% / {lastResponse.reasoning_provider || "deterministic"}</span></p>
              <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Capabilities</strong><span className="block text-xs text-ink/45">{(lastResponse.transparency.capabilities_used || []).map((item) => item.name || item.capability_id).slice(0, 3).join(", ") || "No capability executed"}</span></p>
              <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Verification</strong><span className="block text-xs text-ink/45">{short(lastResponse.transparency.verification?.summary || "Verified", 120)}</span></p>
            </div>
          ) : <EmptyState>No transparency package yet.</EmptyState>}
        </Panel>
        <Panel title="Streaming state" subtitle="Live response phases.">
          <List items={(streamingEvents || []).slice(-6)} empty="No active stream." render={(item, index) => <p key={`${item.phase}-${index}`} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{label(item.phase)}</strong><span className="block text-xs text-ink/45">{item.message}</span></p>} />
        </Panel>
        <Panel title="Suggested actions" subtitle="Executable next steps generated from the response.">
          <List items={lastResponse?.next_recommended_actions} empty="No suggestions yet." render={(item, index) => <button key={`${item.intent}-${index}`} onClick={() => setInput(item.label)} className="w-full rounded-xl bg-acid/50 px-4 py-3 text-left text-sm font-semibold">{item.label}<span className="block text-xs font-normal text-ink/45">{label(item.intent)}</span></button>} />
        </Panel>
        <Panel title="Recent Activity" subtitle="Runtime, events, and notifications.">
          <List items={recentActivity} empty="No recent activity." render={(item, index) => <p key={item.notification_id || item.event_id || index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{item.title || label(item.event_type || item.category || "activity")}</strong><span className="block text-xs text-ink/45">{relativeTime(item.created_at || item.timestamp)}</span></p>} />
        </Panel>
      </div>
    </section>
  );
}

function GoalsTab({ goals, title, setTitle, onCreate, working }) {
  return (
    <section className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
      <Panel title="Create goal" subtitle="Pardha converts goals into objectives, plans, tasks, timeline, and daily follow-ups.">
        <form onSubmit={onCreate} className="space-y-3">
          <input value={title} onChange={(event) => setTitle(event.target.value)} className="min-h-11 w-full rounded-xl border border-ink/10 px-4 text-sm outline-none" />
          <ShellButton dark disabled={working}>Create goal</ShellButton>
        </form>
      </Panel>
      <Panel title="Goal workspace" subtitle={`${goals?.length || 0} active founder goals.`}>
        <List items={goals} empty="No goals created yet." render={(goal) => <article key={goal.goal_id} className="rounded-xl border border-ink/10 p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{goal.title}</p><p className="mt-1 text-xs text-ink/45">{label(goal.priority)} / {goal.owner} / {label(goal.status)}</p></div><span className="rounded-full bg-acid px-2.5 py-1 text-[0.65rem] font-bold uppercase">{goal.daily_followups?.length || 0} follow-ups</span></div><div className="mt-3 grid gap-2 md:grid-cols-3">{(goal.success_metrics || []).slice(0, 3).map((metric, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-3 py-2 text-xs">{metric}</p>)}</div></article>} />
      </Panel>
    </section>
  );
}

function PlanningTab({ goals, plans, approvals, onApprove, onReject, onExecute, working }) {
  const latestPlan = plans?.[0];
  return (
    <section className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="Goals" value={goals?.length || 0} detail="first-class planning goals" />
        <Metric title="Plans" value={plans?.length || 0} detail="execution plans" />
        <Metric title="Approvals" value={approvals?.length || 0} detail="pending founder decisions" />
        <Metric title="Graph Nodes" value={latestPlan?.nodes?.length || 0} detail="latest plan" />
        <Metric title="Progress" value={`${latestPlan?.progress || 0}%`} detail={latestPlan?.status || "no active plan"} />
      </div>
      <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Approval Center" subtitle="Human-in-the-loop decisions for medium and high risk work.">
          <List items={approvals} empty="No pending approvals." render={(approval) => (
            <article key={approval.approval_id} className="rounded-xl border border-ink/10 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{approval.title}</p>
                  <p className="mt-1 text-xs text-ink/45">{label(approval.risk_level)} / {label(approval.approval_type)}</p>
                </div>
              </div>
              <p className="mt-3 text-sm text-ink/55">{approval.detail}</p>
              <div className="mt-3 grid gap-2 md:grid-cols-3">
                <p className="rounded-xl bg-ink/[0.035] px-3 py-2 text-xs"><strong>Preview</strong><br />{short(approval.title, 80)}</p>
                <p className="rounded-xl bg-ink/[0.035] px-3 py-2 text-xs"><strong>Expected Result</strong><br />Plan can enter runtime queue.</p>
                <p className="rounded-xl bg-ink/[0.035] px-3 py-2 text-xs"><strong>Rollback</strong><br />Cancel execution or mark nodes for retry.</p>
              </div>
              <textarea className="mt-3 min-h-20 w-full rounded-xl border border-ink/10 p-3 text-xs outline-none" placeholder="Modify or comment before decision" />
              <div className="mt-3 flex flex-wrap gap-2">
                <ShellButton dark disabled={working} onClick={() => onApprove(approval.plan_id)}>Approve</ShellButton>
                <ShellButton disabled={working} onClick={() => onReject(approval.plan_id)}>Reject</ShellButton>
                <ShellButton disabled={working}>Modify</ShellButton>
                <ShellButton disabled={working}>Comment</ShellButton>
              </div>
            </article>
          )} />
        </Panel>
        <Panel title="Execution Plans" subtitle="Goal to objectives to milestones to capabilities to verification.">
          <List items={plans?.slice(0, 6)} empty="No execution plans yet. Ask Pardha for an outcome." render={(plan) => (
            <article key={plan.plan_id} className="rounded-xl border border-ink/10 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="font-semibold">{plan.title}</p>
                  <p className="mt-1 text-xs text-ink/45">{label(plan.plan_type)} / {label(plan.status)} / {plan.nodes?.length || 0} nodes</p>
                  <p className="mt-2 text-sm text-ink/55">{plan.summary}</p>
                </div>
                <ShellButton disabled={working || plan.approval_required} onClick={() => onExecute(plan.plan_id)}>Execute</ShellButton>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-3">
                {(plan.capability_ids || []).slice(0, 6).map((capability) => <p key={capability} className="rounded-xl bg-ink/[0.035] px-3 py-2 text-xs">{capability}</p>)}
              </div>
            </article>
          )} />
        </Panel>
      </section>
      <section className="grid gap-5 xl:grid-cols-2">
        <Panel title="Planning Goals" subtitle="Business objectives with risk, progress and success metrics.">
          <List items={goals?.slice(0, 8)} empty="No planning goals yet." render={(goal) => <p key={goal.goal_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{goal.title}</strong><span className="block text-xs text-ink/45">{label(goal.department)} / {label(goal.risk_level)} / {goal.progress}%</span></p>} />
        </Panel>
        <Panel title="Latest Execution Graph" subtitle={latestPlan ? latestPlan.title : "No graph generated yet."}>
          <List items={(latestPlan?.graph?.edges || []).slice(0, 10)} empty="No graph edges yet." render={(edge, index) => <p key={`${edge.source}-${edge.target}-${index}`} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{short(edge.source, 24)}</strong><span className="block text-xs text-ink/45">depends on {short(edge.target, 34)}</span></p>} />
        </Panel>
      </section>
    </section>
  );
}

function RuntimeTab({ dashboard, plans, executions, queue, notifications, departments, onStart, onProcess, onRollback, working }) {
  const latestPlan = plans?.[0];
  const observable = dashboard?.observability || {};
  return (
    <section className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <Metric title="Executions" value={executions?.length || 0} detail={`${observable.success_rate ?? 0}% success`} />
        <Metric title="Queue" value={queue?.filter((item) => item.status === "queued").length || 0} detail="waiting" />
        <Metric title="Departments" value={departments?.length || 0} detail="runtime teams" />
        <Metric title="Notifications" value={notifications?.filter((item) => item.status === "unread").length || 0} detail="unread" />
        <Metric title="Failures" value={observable.failures || 0} detail="runtime failures" />
        <Metric title="Timeline" value={dashboard?.business_timeline?.length || 0} detail="business events" />
      </div>
      <section className="grid gap-5 xl:grid-cols-[0.75fr_1.25fr]">
        <Panel title="Runtime controls" subtitle="Queue and process plan execution through the universal runtime.">
          <div className="grid gap-3">
            <ShellButton dark disabled={working || !latestPlan} onClick={() => latestPlan && onStart(latestPlan.plan_id)}>Queue Latest Plan</ShellButton>
            <ShellButton disabled={working} onClick={onProcess}>Process Queue</ShellButton>
          </div>
        </Panel>
        <Panel title="Runtime executions" subtitle="Universal execution engine status.">
          <List items={executions?.slice(0, 8)} empty="No runtime executions yet." render={(execution) => (
            <article key={execution.execution_id} className="rounded-xl border border-ink/10 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{short(execution.execution_id, 18)}</p>
                  <p className="mt-1 text-xs text-ink/45">{label(execution.status)} / {execution.progress}% / {execution.current_capability || execution.current_stage}</p>
                </div>
                <ShellButton disabled={working} onClick={() => onRollback(execution.execution_id)}>Rollback</ShellButton>
              </div>
            </article>
          )} />
        </Panel>
      </section>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="Departments" subtitle="Independent department runtimes.">
          <List items={departments} empty="No departments initialized." render={(department) => <p key={department.department_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{department.name}</strong><span className="block text-xs text-ink/45">{label(department.health)} / load {department.current_load} / {department.capabilities?.length || 0} capabilities</span></p>} />
        </Panel>
        <Panel title="Queue" subtitle="Priority runtime queue.">
          <List items={queue?.slice(0, 8)} empty="Queue is empty." render={(item) => <p key={item.queue_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{label(item.status)}</strong><span className="block text-xs text-ink/45">P{item.priority} / {item.capability_id || short(item.plan_id || "", 18)}</span></p>} />
        </Panel>
        <Panel title="Notifications" subtitle="Central founder notification service.">
          <List items={notifications?.slice(0, 8)} empty="No runtime notifications." render={(item) => <p key={item.notification_id} className="rounded-xl bg-acid/40 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{label(item.priority)} / {label(item.status)}</span></p>} />
        </Panel>
      </section>
      <Panel title="Business timeline" subtitle="Replay goals, executions, approvals, knowledge, communications and releases.">
        <List items={dashboard?.business_timeline?.slice(0, 10)} empty="No runtime timeline yet." render={(item) => <p key={item.timeline_event_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{label(item.event_type)} / {relativeTime(item.created_at)}</span></p>} />
      </Panel>
    </section>
  );
}

function SoftwareFactoryTab({ deliveries, dashboard, validation, requirement, setRequirement, onCreate, onDecide, working }) {
  const latest = deliveries?.[0];
  const approvals = latest?.approvals || dashboard?.pending_approvals || [];
  const artifacts = latest?.artifacts || [];
  const artifact = (type) => artifacts.find((item) => item.artifact_type === type);
  const prd = artifact("prd");
  const architecture = artifact("architecture");
  const sprint = artifact("engineering_plan");
  const qa = artifact("qa_plan");
  const release = artifact("release_package");
  return (
    <section className="grid gap-5">
      <Panel title="Autonomous Product Engineering Factory" subtitle="Requirement to PRD, architecture, sprint, Jira blueprint, developer context, QA and release package. No production code is written here.">
        <form onSubmit={onCreate} className="grid gap-3 lg:grid-cols-[1fr_auto]">
          <input value={requirement} onChange={(event) => setRequirement(event.target.value)} className="min-h-11 rounded-xl border border-ink/10 px-4 text-sm outline-none" placeholder="We need QR tracking." />
          <ShellButton type="submit" disabled={working} dark>{working ? "Generating..." : "Create Factory Package"}</ShellButton>
        </form>
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="Requirements" value={deliveries?.length || 0} detail="factory packages" />
        <Metric title="Open Stories" value={dashboard?.open_stories || 0} detail="planned stories" />
        <Metric title="Blocked" value={dashboard?.blocked_stories || 0} detail="blocked stories" />
        <Metric title="Approvals" value={approvals.length} detail="waiting founder" />
        <Metric title="Validation" value={validation?.score ?? 0} detail={`${validation?.scenarios_run || 0} scenarios`} />
      </div>
      <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Current sprint" subtitle="Engineering planner output.">
          <List items={dashboard?.current_sprint?.user_stories?.slice(0, 6)} empty="No sprint package yet." render={(story, index) => (
            <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{story.title}</strong><span className="block text-xs text-ink/45">{story.story_points} points / {story.sprint}</span></p>
          )} />
        </Panel>
        <Panel title="Founder approvals" subtitle="PRD, architecture, sprint, Jira, merge, release and deployment gates.">
          <List items={approvals.slice(0, 7)} empty="No approvals waiting." render={(approval) => (
            <article key={approval.approval_id} className="rounded-xl border border-ink/10 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="font-semibold">{approval.title}</p>
                  <p className="mt-1 text-xs text-ink/45">{label(approval.approval_type)} / {label(approval.risk_level)} risk</p>
                </div>
                <div className="flex gap-2">
                  <ShellButton disabled={working} onClick={() => onDecide(approval.approval_id, "approve")}>Approve</ShellButton>
                  <ShellButton disabled={working} onClick={() => onDecide(approval.approval_id, "reject")}>Reject</ShellButton>
                </div>
              </div>
            </article>
          )} />
        </Panel>
      </section>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="PRD" subtitle={prd?.status || "not generated"}>
          <p className="text-sm leading-6 text-ink/65">{prd?.content?.executive_summary || "Create a requirement to generate an editable PRD."}</p>
          <List items={prd?.content?.acceptance_criteria?.slice(0, 4)} empty="No acceptance criteria." render={(item, index) => <p key={index} className="mt-2 rounded-xl bg-ink/[0.035] px-3 py-2 text-xs">{item}</p>} />
        </Panel>
        <Panel title="Architecture" subtitle={architecture?.status || "not generated"}>
          <List items={architecture?.content?.technical_risks?.slice(0, 4)} empty="No technical risks." render={(item, index) => <p key={index} className="rounded-xl bg-coral/10 px-3 py-2 text-xs text-coral">{item}</p>} />
          <p className="mt-3 text-xs text-ink/45">Stack: {(architecture?.content?.supported_stack || []).join(", ") || "none"}</p>
        </Panel>
        <Panel title="QA and Release" subtitle={qa?.content?.status || "not prepared"}>
          <p className="rounded-xl bg-ink/[0.035] px-3 py-2 text-xs">QA: {(qa?.content?.api_tests || []).length} API / {(qa?.content?.ui_tests || []).length} UI / {(qa?.content?.security_tests || []).length} security checks</p>
          <p className="mt-2 rounded-xl bg-acid/40 px-3 py-2 text-xs">Release: {release?.content?.readiness?.status || "not prepared"} / score {release?.content?.readiness?.score || 0}</p>
        </Panel>
      </section>
      <Panel title="Lifecycle artifacts" subtitle="Every artifact generated by the factory is founder-visible.">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {artifacts.map((item) => (
            <article key={item.artifact_id} className="rounded-xl border border-ink/10 p-4">
              <p className="text-xs font-bold uppercase tracking-wider text-ink/35">{label(item.artifact_type)}</p>
              <p className="mt-2 font-semibold">{item.title}</p>
              <p className="mt-2 text-xs text-ink/45">v{item.version} / {label(item.status)} / {item.editable ? "editable" : "generated context"}</p>
            </article>
          ))}
        </div>
      </Panel>
    </section>
  );
}

function EnterpriseTab({ dashboard, admin, validation, security, observability, rbac, billing, integrations, deployment, flags, audit, governance, tenants }) {
  const subscription = billing?.[0];
  return (
    <section className="grid gap-5">
      <Panel title="Enterprise Platform" subtitle="Multi-tenant SaaS foundation, governance, security, billing architecture and administration.">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <Metric title="Tenants" value={tenants?.length || dashboard?.tenant_health?.tenants || 0} detail={dashboard?.tenant_health?.status || "unknown"} />
          <Metric title="Businesses" value={dashboard?.businesses?.count || 0} detail={dashboard?.businesses?.isolated ? "isolated" : "review isolation"} />
          <Metric title="Users" value={dashboard?.users?.count || 0} detail={dashboard?.users?.rbac || "rbac"} />
          <Metric title="Audit" value={dashboard?.audit_activity?.events || audit?.length || 0} detail="events retained" />
          <Metric title="Validation" value={validation?.score ?? 0} detail={`${validation?.scenarios_run || 0} scenarios`} />
        </div>
      </Panel>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="Security" subtitle="Enterprise readiness controls.">
          <div className="grid gap-3 text-sm">
            <StateCard title="JWT" ok={security?.jwt_authentication === "hs256_ready"} value={security?.jwt_authentication || "unknown"} />
            <StateCard title="Refresh Tokens" ok={!!security?.refresh_tokens} value={security?.refresh_tokens || "unknown"} />
            <StateCard title="MFA" ok={security?.mfa_ready} value={security?.mfa_ready ? "ready" : "missing"} />
            <StateCard title="Rate Limiting" ok={!!security?.rate_limiting} value={security?.rate_limiting || "unknown"} />
          </div>
        </Panel>
        <Panel title="Billing Foundation" subtitle="Architecture only. No payment gateway.">
          <p className="font-display text-4xl font-semibold">{label(subscription?.plan || "none")}</p>
          <p className="mt-2 text-sm text-ink/45">{label(subscription?.status || "not configured")}</p>
          <div className="mt-4 grid gap-2 text-xs">
            {Object.entries(subscription?.usage || {}).slice(0, 6).map(([key, value]) => <p key={key} className="rounded-xl bg-ink/[0.035] px-3 py-2"><strong>{label(key)}</strong>: {value}</p>)}
          </div>
        </Panel>
        <Panel title="Observability" subtitle="System, execution, API and queue metrics.">
          <div className="grid gap-2 text-xs">
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">Executions: {observability?.execution_metrics?.executions || 0}</p>
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">Conversation messages: {observability?.conversation_metrics?.messages || 0}</p>
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">Audited API requests: {observability?.api_metrics?.audited_requests || 0}</p>
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">P95 API latency: {observability?.performance_metrics?.p95_api_latency_ms || 0}ms</p>
          </div>
        </Panel>
      </section>
      <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <Panel title="RBAC" subtitle="Capability-based role matrix.">
          <div className="grid gap-2 md:grid-cols-2">
            {Object.entries(rbac?.roles || {}).slice(0, 12).map(([role, permissions]) => <p key={role} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{label(role)}</strong><span className="block text-xs text-ink/45">{permissions.slice(0, 4).join(", ")}</span></p>)}
          </div>
        </Panel>
        <Panel title="Enterprise Integrations" subtitle="OAuth, rotation and secret-reference readiness.">
          <List items={integrations} empty="No enterprise integrations configured." render={(item) => <p key={item.integration_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{label(item.provider)}</strong><span className="block text-xs text-ink/45">{label(item.status)} / {item.auth_type} / scopes {item.scopes?.length || 0}</span></p>} />
        </Panel>
      </section>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="Deployment Profiles" subtitle="Development, testing, staging and production.">
          <List items={deployment} empty="No deployment profiles." render={(item) => <p key={item.profile_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{label(item.environment)}</strong><span className="block text-xs text-ink/45">Docker {item.docker_ready ? "ready" : "missing"} / Kubernetes {item.kubernetes_ready ? "ready" : "missing"}</span></p>} />
        </Panel>
        <Panel title="Feature Flags" subtitle="Tenant-specific rollout controls.">
          <List items={flags} empty="No feature flags." render={(item) => <p key={item.flag_id} className="rounded-xl bg-acid/40 px-4 py-3 text-sm"><strong>{item.name}</strong><span className="block text-xs text-ink/45">{item.enabled ? "enabled" : "disabled"} / rollout {item.rollout_percentage}% / emergency {item.emergency_disabled ? "on" : "off"}</span></p>} />
        </Panel>
        <Panel title="AI Governance" subtitle="Provider, model, prompt, evidence and approval tracking.">
          <List items={governance?.slice(0, 5)} empty="No governance records." render={(item) => <p key={item.governance_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{item.reasoning_provider}</strong><span className="block text-xs text-ink/45">{item.model_version} / {item.prompt_version} / confidence {item.confidence}</span></p>} />
        </Panel>
      </section>
      <section className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel title="Administration Console" subtitle="Tenant, user, capability and system control.">
          <div className="grid gap-2 text-xs">
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">Tenants: {admin?.tenants?.length || 0}</p>
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">Users: {admin?.users?.length || 0}</p>
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">Capabilities: {admin?.capabilities?.registered || 0}</p>
            <p className="rounded-xl bg-ink/[0.035] px-3 py-2">Database tables: {admin?.system_health?.tables || 0}</p>
          </div>
        </Panel>
        <Panel title="Recent Audit Activity" subtitle="Who, when, resource, outcome and metadata.">
          <List items={audit?.slice(0, 8)} empty="No audit events yet." render={(item) => <p key={item.audit_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.action}</strong><span className="block text-xs text-ink/45">{item.resource_type} / {item.outcome} / {relativeTime(item.created_at)}</span></p>} />
        </Panel>
      </section>
    </section>
  );
}

function ExecutiveCommandTab({ command }) {
  return (
    <section className="grid gap-5">
      <Panel title="Executive Command Center" subtitle={command?.business_name || "Department-level operating status."}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(command?.departments || []).map((dept) => <article key={dept.name} className="rounded-xl border border-ink/10 p-4"><p className="text-xs font-bold uppercase tracking-wider text-ink/40">{dept.name}</p><p className="mt-2 font-semibold">{dept.current_status}</p><p className="mt-3 text-xs text-ink/45">KPIs: {Object.entries(dept.kpis || {}).map(([key, value]) => `${label(key)} ${value}`).join(" / ") || "none"}</p><List items={dept.recommendations?.slice(0, 2)} empty="No recommendations." render={(item, index) => <p key={index} className="mt-2 rounded-xl bg-ink/[0.035] px-3 py-2 text-xs">{item}</p>} /></article>)}
        </div>
      </Panel>
      <section className="grid gap-5 xl:grid-cols-2">
        <Panel title="Notifications" subtitle="Important operating signals.">
          <List items={command?.notifications} empty="No notifications." render={(item, index) => <p key={index} className="rounded-xl bg-coral/10 px-4 py-3 text-sm text-coral">{item}</p>} />
        </Panel>
        <Panel title="Quick actions" subtitle="Commands Pardha can run.">
          <List items={command?.quick_actions} empty="No quick actions." render={(item, index) => <p key={index} className="rounded-xl bg-acid/40 px-4 py-3 text-sm">{item}</p>} />
        </Panel>
      </section>
    </section>
  );
}

function HelpTab({ help, capabilities, connectors, businesses, activeBusiness, runtime, onPrompt }) {
  const commands = [
    "What can you do?",
    "How do I upload knowledge?",
    "Which Gmail is connected?",
    "Which Jira is active?",
    "Show available capabilities.",
    "Explain this architecture.",
    "Explain this API.",
    ...(help?.commands || []),
  ].filter((item, index, all) => all.indexOf(item) === index);
  const gmail = connectors?.find((item) => item.provider === "gmail");
  const jira = connectors?.find((item) => item.provider === "jira");
  const healthyCapabilities = capabilities?.filter((item) => item.health === "healthy").length || 0;
  const openApprovals = runtime?.approvals?.pending || runtime?.approvals_waiting || 0;
  return (
    <section className="grid gap-5">
      <Panel title="Executive Help" subtitle="Live workspace answers from the current Pardha configuration.">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric title="Active Business" value={activeBusiness?.business_name || "None"} detail={`${businesses?.length || 0} businesses available`} />
          <Metric title="Capabilities" value={`${healthyCapabilities}/${capabilities?.length || 0}`} detail="healthy and registered" />
          <Metric title="Gmail" value={gmail?.connected ? "Connected" : "Disconnected"} detail={gmail?.connected_account || gmail?.authentication_status || "not configured"} />
          <Metric title="Jira" value={jira?.connected ? "Connected" : "Disconnected"} detail={jira?.connected_account || jira?.authentication_status || "not configured"} />
        </div>
        <p className="mt-4 rounded-2xl bg-ink/[0.035] p-4 text-sm leading-6">{help?.answer || "Ask Pardha for operational help. Responses use live businesses, capabilities, connectors, goals, knowledge, and runtime state."}</p>
      </Panel>
      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Available commands" subtitle="Click a command to send it to Executive Conversation.">
          <div className="grid gap-2 md:grid-cols-2">
            {commands.map((item) => <ShellButton key={item} onClick={() => onPrompt(item)}>{item}</ShellButton>)}
          </div>
        </Panel>
        <Panel title="Live operating facts" subtitle="Self-inspection, not hardcoded help text.">
          <div className="grid gap-3 text-sm">
            <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Runtime:</strong> {runtime?.status || "available"} / {openApprovals} approval{openApprovals === 1 ? "" : "s"} waiting.</p>
            <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Knowledge upload:</strong> Use the Knowledge tab drag-and-drop area. Supported formats are PDF, DOCX, PPTX, TXT, Markdown, CSV and JSON.</p>
            <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Connector health:</strong> {(connectors || []).filter((item) => item.connected).length}/{connectors?.length || 0} connected, {(connectors || []).filter((item) => !item.env_valid).length} missing required configuration.</p>
            <p className="rounded-xl bg-ink/[0.035] px-4 py-3"><strong>Architecture:</strong> Founder requests flow through Conversation, Intelligence Kernel, Capability Registry, Planning, Runtime and Approval services.</p>
          </div>
        </Panel>
      </section>
    </section>
  );
}

function CapabilitiesTab({ capabilities, health, graph, validation }) {
  const sorted = [...(capabilities || [])].sort((a, b) => (b.priority || 0) - (a.priority || 0));
  return (
    <section className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="Capabilities" value={health?.total ?? sorted.length} detail="registered" />
        <Metric title="Healthy" value={health?.healthy ?? 0} detail="available now" />
        <Metric title="Degraded" value={health?.degraded ?? 0} detail="needs credentials or setup" />
        <Metric title="Graph" value={graph?.edges?.length ?? 0} detail="dependency edges" />
        <Metric title="Validation" value={validation?.ready ? "Ready" : "Review"} detail={`${validation?.registered_existing_capabilities ?? 0} existing capabilities`} />
      </div>
      <Panel title="Capability Explorer" subtitle="Dynamic registry used by the Intelligence Kernel.">
        <div className="grid gap-3">
          {sorted.map((capability) => (
            <article key={capability.capability_id} className="rounded-2xl border border-ink/10 bg-white p-4">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm font-bold">{capability.name}</p>
                  <p className="mt-1 font-mono text-xs text-ink/45">{capability.capability_id} / v{capability.version}</p>
                  <p className="mt-3 max-w-4xl text-sm leading-6 text-ink/60">{capability.description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className={`rounded-full border px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider ${statusClass(capability.health === "healthy")}`}>{capability.health}</span>
                  <span className="rounded-full bg-ink px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider text-white">P{capability.priority}</span>
                  <span className="rounded-full bg-acid/60 px-2.5 py-1 text-[0.65rem] font-bold uppercase tracking-wider">{capability.execution_count || 0} runs</span>
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div>
                  <p className="text-[0.65rem] font-bold uppercase tracking-wider text-ink/35">Supported intents</p>
                  <p className="mt-1 text-xs leading-5 text-ink/60">{(capability.supported_intents || []).slice(0, 6).map(label).join(", ") || "none"}</p>
                </div>
                <div>
                  <p className="text-[0.65rem] font-bold uppercase tracking-wider text-ink/35">Dependencies</p>
                  <p className="mt-1 text-xs leading-5 text-ink/60">{(capability.dependencies || []).slice(0, 6).join(", ") || "none"}</p>
                </div>
                <div>
                  <p className="text-[0.65rem] font-bold uppercase tracking-wider text-ink/35">Outputs</p>
                  <p className="mt-1 text-xs leading-5 text-ink/60">{(capability.outputs || []).slice(0, 6).map(label).join(", ") || "none"}</p>
                </div>
              </div>
            </article>
          ))}
          {!sorted.length && <EmptyState>No capabilities registered.</EmptyState>}
        </div>
      </Panel>
      <section className="grid gap-5 xl:grid-cols-2">
        <Panel title="Registry Validation" subtitle={validation?.ready ? "All required registry fields are present." : "Review registry gaps before v2 adoption."}>
          <List items={validation?.missing_required_fields} empty="No missing required fields." render={(item) => <p key={item} className="rounded-xl bg-coral/10 px-4 py-3 text-sm text-coral">{item}</p>} />
        </Panel>
        <Panel title="Capability Graph" subtitle={`${graph?.nodes?.length || 0} nodes / ${graph?.edges?.length || 0} edges`}>
          <List items={(graph?.edges || []).slice(0, 10)} empty="No dependency edges available." render={(edge, index) => <p key={`${edge.source}-${edge.target}-${index}`} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{edge.source}</strong><span className="block text-xs text-ink/45">depends on {edge.target}</span></p>} />
        </Panel>
      </section>
    </section>
  );
}

function FounderCopilotTab({ copilot, bi, health, prompt, setPrompt, onRun, working }) {
  return (
    <section className="grid gap-5">
      <Panel title="Founder Copilot" subtitle="Turn founder intent into analysis, strategy, KPIs, and execution.">
        <form onSubmit={onRun} className="flex flex-col gap-3 md:flex-row">
          <input value={prompt} onChange={(event) => setPrompt(event.target.value)} className="min-h-11 flex-1 rounded-xl border border-ink/10 px-4 text-sm outline-none" />
          <ShellButton dark disabled={working}>Generate plan</ShellButton>
        </form>
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="Health" value={bi?.business_health_score || health?.customer_health?.score || 0} detail="business score" />
        <Metric title="Risk" value={health?.risk_score ?? 0} detail="lower is better" />
        <Metric title="Tasks" value={health?.engineering_velocity?.open_tasks ?? 0} detail="open engineering work" />
        <Metric title="Knowledge" value={health?.knowledge_growth?.records ?? 0} detail="records learned" />
        <Metric title="Revenue" value={`$${((health?.revenue_goals?.target || 0) / 1000).toFixed(0)}k`} detail={health?.revenue_goals?.status || "target"} />
      </div>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="Business analysis" subtitle={copilot?.business_analysis?.summary || "Run Founder Copilot to generate a plan."}>
          <List items={copilot?.recommended_strategy || bi?.executive_recommendations} empty="No strategy generated yet." render={(item, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm">{item}</p>} />
        </Panel>
        <Panel title="Opportunities" subtitle="Growth and AI opportunities.">
          <List items={copilot?.opportunities || bi?.growth_opportunities} empty="No opportunities yet." render={(item, index) => <p key={index} className="rounded-xl bg-acid/40 px-4 py-3 text-sm">{item}</p>} />
        </Panel>
        <Panel title="Execution plan" subtitle="Generated owner-level execution.">
          <List items={copilot?.execution_plan} empty="No execution plan yet." render={(item, index) => <p key={index} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{item.owner} / {item.status}</span></p>} />
        </Panel>
      </section>
    </section>
  );
}

function CustomerSuccessTab({ workspace, briefs, onOnboard, working }) {
  const profile = workspace?.company_profile || {};
  return (
    <section className="grid gap-5">
      <Panel title="Customer onboarding" subtitle="Create the customer workspace, import knowledge, generate objectives, briefs, and dashboard readiness.">
        <ShellButton dark disabled={working} onClick={onOnboard}>Run onboarding wizard</ShellButton>
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="Health" value={profile.health_score || 0} detail={profile.lifecycle_stage || "not started"} />
        <Metric title="Knowledge" value={workspace?.knowledge_base?.length || 0} detail="records" />
        <Metric title="Objectives" value={workspace?.objectives?.length || 0} detail="active" />
        <Metric title="Projects" value={workspace?.projects?.length || 0} detail="scanned" />
        <Metric title="Timeline" value={workspace?.timeline?.length || 0} detail="events" />
      </div>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="Company profile" subtitle={profile.company_name || "No customer selected."}>
          <List items={profile.success_plan?.success_metrics} empty="No success plan yet." render={(item, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm">{item}</p>} />
        </Panel>
        <Panel title="Meeting notes" subtitle="Customer success history.">
          <List items={workspace?.meeting_notes} empty="No meeting notes yet." render={(item) => <p key={item.meeting_note_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{short(item.summary, 120)}</span></p>} />
        </Panel>
        <Panel title="Executive briefs" subtitle="Daily, weekly, and monthly customer context.">
          <List items={briefs?.weekly_executive_summary?.next_actions} empty="No brief bundle yet." render={(item, index) => <p key={index} className="rounded-xl bg-acid/40 px-4 py-3 text-sm">{item}</p>} />
        </Panel>
      </section>
    </section>
  );
}

function BusinessHealthTab({ health, readiness }) {
  return (
    <section className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="Readiness" value={readiness?.overall_score || 0} detail="commercial score" />
        <Metric title="Pilot" value={readiness?.pilot_readiness_score || 0} detail="pilot readiness" />
        <Metric title="Risk" value={health?.risk_score ?? 0} detail="customer risk" />
        <Metric title="Sales" value={`$${((health?.sales_pipeline?.pipeline_value || 0) / 1000).toFixed(0)}k`} detail="pipeline" />
        <Metric title="Marketing" value={health?.marketing_performance?.leads || 0} detail="leads" />
      </div>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="AI recommendations" subtitle="Business consultant recommendations.">
          <List items={health?.ai_recommendations} empty="No recommendations yet." render={(item, index) => <p key={index} className="rounded-xl bg-acid/40 px-4 py-3 text-sm">{item}</p>} />
        </Panel>
        <Panel title="Operational health" subtitle={health?.operational_health?.status || "unknown"}>
          <List items={readiness?.checks} empty="No readiness checks yet." render={(item) => <p key={item.name} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.name}</strong><span className="block text-xs text-ink/45">{item.pass ? "pass" : "needs attention"}</span></p>} />
        </Panel>
        <Panel title="Technical debt" subtitle="Known non-blocking items.">
          <List items={readiness?.technical_debt} empty="No technical debt listed." render={(item, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm">{item}</p>} />
        </Panel>
      </section>
    </section>
  );
}

function PresentationTab({ presentation, demoLibrary, onLoadDemo, working }) {
  return (
    <section className="grid gap-5">
      <Panel title="Demo library" subtitle="One-click customer meeting workspaces.">
        <div className="flex flex-wrap gap-2">
          {(demoLibrary?.templates || []).map((item) => <ShellButton key={item.name} disabled={working} onClick={() => onLoadDemo(item.name)}>{item.name}</ShellButton>)}
        </div>
      </Panel>
      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl bg-ink p-8 text-white">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/45">Executive presentation</p>
          <h2 className="mt-8 font-display text-4xl font-semibold">{presentation?.company_overview?.company_name || "Select a company"}</h2>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-white/65">{presentation?.executive_summary?.summary || "Presentation mode will show company overview, health, recommendations, execution plan, KPIs, and roadmap."}</p>
        </div>
        <Panel title="Current challenges" subtitle="Meeting-ready talking points.">
          <List items={presentation?.current_challenges} empty="No challenges loaded." render={(item, index) => <p key={index} className="rounded-xl bg-coral/10 px-4 py-3 text-sm text-coral">{item}</p>} />
        </Panel>
      </section>
      <section className="grid gap-5 xl:grid-cols-3">
        <Panel title="AI recommendations" subtitle="Customer-facing recommendations.">
          <List items={presentation?.ai_recommendations} empty="No recommendations loaded." render={(item, index) => <p key={index} className="rounded-xl bg-acid/40 px-4 py-3 text-sm">{item}</p>} />
        </Panel>
        <Panel title="Execution plan" subtitle="Roadmap to action.">
          <List items={presentation?.execution_plan} empty="No execution plan loaded." render={(item, index) => <p key={index} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{item.title}</strong><span className="block text-xs text-ink/45">{item.owner || "team"} / {item.status}</span></p>} />
        </Panel>
        <Panel title="KPIs" subtitle="Success measurement.">
          <List items={presentation?.kpis} empty="No KPIs loaded." render={(item, index) => <p key={index} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm">{item}</p>} />
        </Panel>
      </section>
    </section>
  );
}

function SalesTab({ dashboard, leads, pipeline, demos, summary, request, setRequest, onGenerate, onViewOutreach, onScheduleDemo, onMoveStage, working }) {
  const shownLeads = dashboard?.leads || leads;
  const shownPipeline = dashboard?.pipeline || pipeline;
  const shownDemos = dashboard?.demos || demos || { upcoming_demos: [] };
  const shownSummary = dashboard?.summary || summary;
  return (
    <section className="grid gap-5">
      <Panel title="Sales Executive" subtitle="Generate qualified DP360 prospects, outreach, CRM records, demos, and follow-ups.">
        <div className="flex flex-col gap-3 md:flex-row">
          <input value={request} onChange={(event) => setRequest(event.target.value)} className="min-h-11 flex-1 rounded-xl border border-ink/10 px-4 text-sm outline-none" />
          <ShellButton dark disabled={working} onClick={onGenerate}>Generate 50 prospects</ShellButton>
        </div>
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric title="Prospects" value={shownSummary?.prospects || 0} detail="researched companies" />
        <Metric title="Warm leads" value={shownSummary?.warm_leads || 0} detail="active sales motion" />
        <Metric title="Pipeline" value={`$${((shownSummary?.pipeline_value || 0) / 1000).toFixed(0)}k`} detail={shownSummary?.pipeline_health || "not started"} />
        <Metric title="Demos" value={shownSummary?.upcoming_demos || 0} detail="requested or scheduled" />
        <Metric title="Forecast" value={`$${((shownSummary?.revenue_forecast || 0) / 1000).toFixed(0)}k`} detail="weighted forecast" />
      </div>
      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel title="Lead status" subtitle="Qualified prospects and personalized outreach.">
          <List items={shownLeads?.slice(0, 12)} empty="No sales leads yet. Generate prospects to populate CRM." render={(lead) => (
            <article key={lead.lead_id} className="rounded-xl border border-ink/10 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{lead.company}</p>
                  <p className="mt-1 text-xs text-ink/45">{lead.industry} / {lead.contact_name || "No contact"} / score {lead.ai_opportunity_score}</p>
                </div>
                <span className="rounded-full bg-acid px-2.5 py-1 text-[0.65rem] font-bold uppercase">{label(lead.sales_priority)}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-ink/60">{short(lead.outreach_email || lead.next_action, 220)}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <ShellButton disabled={working} onClick={() => onViewOutreach(lead.lead_id)}>Outreach</ShellButton>
                <ShellButton disabled={working} onClick={() => onScheduleDemo(lead.lead_id)}>Schedule demo</ShellButton>
                <ShellButton disabled={working} onClick={() => onMoveStage(lead.lead_id, "proposal_sent")}>Proposal</ShellButton>
              </div>
            </article>
          )} />
        </Panel>
        <div className="grid gap-5">
          <Panel title="Pipeline" subtitle="Deal stages and conversion funnel.">
            <List items={shownPipeline?.stages} empty="No pipeline stages yet." render={(stage) => <div key={stage.stage} className="rounded-xl bg-ink/[0.035] px-4 py-3"><div className="flex items-center justify-between"><p className="text-sm font-semibold">{label(stage.stage)}</p><span className="text-xs font-bold">{stage.count}</span></div><p className="mt-1 text-xs text-ink/45">${stage.value}</p></div>} />
          </Panel>
          <Panel title="Upcoming demos" subtitle="Requested and scheduled demo pipeline.">
            <List items={shownDemos?.upcoming_demos} empty="No demos requested yet." render={(demo) => <p key={demo.lead_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{demo.company}</strong><span className="block text-xs text-ink/45">{label(demo.status)} / {demo.scheduled_at ? relativeTime(demo.scheduled_at) : "schedule pending"}</span></p>} />
          </Panel>
          <Panel title="Daily activities" subtitle="Follow-ups and outreach preparation.">
            <List items={dashboard?.daily_activities?.slice(0, 8)} empty="No daily activities yet." render={(activity) => <p key={activity.activity_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{activity.company}</strong><span className="block text-xs text-ink/45">{label(activity.activity_type)} / {activity.due_date ? relativeTime(activity.due_date) : "no due date"}</span></p>} />
          </Panel>
        </div>
      </section>
    </section>
  );
}

function MarketingVoicePage({ dashboard, campaigns, analytics, content, summary, request, setRequest, onLaunch, working, activeBusiness, voiceState, onVoiceStart, onVoiceStop, interimTranscript, voiceError, messages, streamingEvents, approvals, ollama, validation }) {
  const shownSummary = dashboard?.summary || summary || {};
  const shownCampaigns = dashboard?.active_campaigns || campaigns || [];
  const shownPerformance = dashboard?.performance || analytics || [];
  const shownContent = dashboard?.content_pipeline || content || [];
  const recommendations = dashboard?.recommendations || shownSummary?.recommendations || [];
  const latestUser = [...(messages || [])].reverse().find((message) => message.role === "user");
  const latestAssistant = [...(messages || [])].reverse().find((message) => message.role !== "user");
  const active = !["idle", "completed"].includes(voiceState);
  const totalBudget = shownCampaigns.reduce((sum, campaign) => sum + Number(campaign.budget || 0), 0);
  const metricRows = [
    shownSummary.ctr !== undefined && { label: "CTR", value: `${shownSummary.ctr}%`, detail: shownSummary.clicks !== undefined ? `${shownSummary.clicks} clicks` : "" },
    shownSummary.leads !== undefined && { label: "Leads", value: shownSummary.leads, detail: shownSummary.cpl !== undefined ? `CPL $${shownSummary.cpl}` : "" },
    shownSummary.roas !== undefined && { label: "ROAS", value: `${shownSummary.roas}x`, detail: "pipeline return" },
    shownSummary.pipeline_contribution !== undefined && { label: "Pipeline", value: `$${((shownSummary.pipeline_contribution || 0) / 1000).toFixed(0)}k`, detail: "contribution" },
    totalBudget > 0 && { label: "Budget", value: `$${(totalBudget / 1000).toFixed(1)}k`, detail: `${shownCampaigns.length} campaign${shownCampaigns.length === 1 ? "" : "s"}` },
  ].filter(Boolean);
  const timeline = (streamingEvents || []).slice(-5).map((event, index) => ({
    id: event.id || `${event.type}-${index}`,
    title: event.message || label(event.type || "runtime event"),
    detail: label(event.status || event.type || "completed"),
    state: event.status || event.type || "completed",
  }));
  const campaignTimeline = timeline.length ? timeline : shownCampaigns.slice(0, 5).map((campaign) => ({
    id: campaign.campaign_id,
    title: campaign.name,
    detail: label(campaign.status || "active"),
    state: campaign.status || "active",
  }));
  const suggestedPrompts = [
    shownCampaigns.length ? "Analyse current campaign performance." : "",
    shownContent.length ? "Summarise content pipeline." : "",
    recommendations[0] ? String(recommendations[0]) : "",
  ].filter(Boolean).slice(0, 3);
  const statusColor = {
    idle: "text-slate-400 bg-slate-800/80",
    wake: "text-violet-200 bg-violet-400/15",
    listening: "text-cyan-200 bg-cyan-400/15",
    transcribing: "text-cyan-200 bg-cyan-400/15",
    thinking: "text-violet-200 bg-violet-400/15",
    planning: "text-violet-200 bg-violet-400/15",
    executing: "text-amber-200 bg-amber-400/15",
    speaking: "text-emerald-200 bg-emerald-400/15",
    error: "text-rose-200 bg-rose-400/15",
  };
  return (
    <section className="grid gap-6 text-slate-100">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h2 className="font-display text-4xl font-semibold text-white">Marketing Agent</h2>
          <p className="mt-2 text-base text-slate-500">Plan, create and execute campaigns through conversation.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <span className="inline-flex min-h-10 items-center rounded-full bg-emerald-400/15 px-4 text-sm font-bold uppercase text-emerald-300"><span className="mr-2 h-2.5 w-2.5 rounded-full bg-emerald-400" />Healthy</span>
          {shownCampaigns.length > 0 && <span className="inline-flex min-h-10 items-center rounded-full bg-slate-900 px-4 text-sm font-bold uppercase text-slate-200">{shownCampaigns.length} campaign{shownCampaigns.length === 1 ? "" : "s"}</span>}
          {shownSummary.leads !== undefined && <span className="inline-flex min-h-10 items-center rounded-full bg-slate-900 px-4 text-sm font-bold uppercase text-slate-200">{shownSummary.leads} lead{shownSummary.leads === 1 ? "" : "s"}</span>}
          <span className="inline-flex min-h-10 items-center rounded-full bg-violet-500/25 px-4 text-sm font-bold text-violet-100">{activeBusiness?.business_name || "No business selected"}</span>
        </div>
      </div>

      <section className="grid gap-6 2xl:grid-cols-[1fr_18rem]">
        <div className="grid gap-6">
          <DarkPanel title="Voice Command" className="min-h-[32rem]">
            <div className="flex justify-end gap-2">
              {["idle", "listening"].map((state) => (
                <span key={state} className={`rounded-full px-5 py-2 text-sm font-bold ${voiceState === state ? statusColor[state] : "bg-slate-900 text-slate-500"}`}>{label(state)}</span>
              ))}
            </div>
            <div className="grid min-h-[24rem] place-items-center">
              <div className="text-center">
                <button onClick={active ? onVoiceStop : onVoiceStart} className={`marketing-voice-orb voice-orb-${voiceState}`} aria-label="Marketing voice command">
                  <span className="marketing-voice-core" />
                </button>
                <div className="mt-6 flex h-16 items-end justify-center gap-3">
                  {[32, 54, 46, 58, 42, 68, 36, 64, 48, 58, 62, 50, 66, 38, 54].map((height, index) => (
                    <span key={index} className={`marketing-wave-bar ${active ? "is-active" : ""}`} style={{ height }} />
                  ))}
                </div>
                <p className="mt-4 text-2xl font-bold text-white">{label(voiceState || "idle")}...</p>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">{voiceError || interimTranscript || `"${request || "Ask Pardha to launch, analyse or optimise your marketing."}"`}</p>
                <div className="mt-6 flex flex-wrap justify-center gap-3">
                  <button onClick={onVoiceStart} disabled={active} className="inline-flex min-h-11 items-center gap-2 rounded-2xl bg-cyan-400 px-5 text-sm font-bold text-slate-950 disabled:opacity-40"><Icon name="mic" /> Talk</button>
                  <button onClick={onVoiceStop} className="min-h-11 rounded-2xl border border-slate-800 bg-slate-900 px-5 text-sm font-bold text-slate-200">Interrupt</button>
                  <button onClick={onLaunch} disabled={working || !request.trim()} className="min-h-11 rounded-2xl bg-violet-500 px-5 text-sm font-bold text-white disabled:opacity-40">Execute Request</button>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-5 text-xs font-bold">
              <span className="text-slate-500"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-slate-500" />Idle</span>
              <span className="text-cyan-300"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-cyan-300" />Listening</span>
              <span className="text-violet-300"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-violet-400" />Thinking</span>
              <span className="text-emerald-300"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />Speaking</span>
              <span className="ml-auto text-slate-500">Model {ollama?.current_model || ollama?.model || "qwen3:8b"} / score {validation?.score ?? "n/a"}</span>
            </div>
          </DarkPanel>

          <section className="grid gap-6 xl:grid-cols-[1fr_0.82fr]">
            <DarkPanel title="Conversation" action={<span className={`rounded-full px-4 py-2 text-xs font-bold uppercase ${statusColor[voiceState] || statusColor.idle}`}>{active ? "Streaming" : label(voiceState)}</span>}>
              <div className="space-y-4">
                <input value={request} onChange={(event) => setRequest(event.target.value)} className="min-h-12 w-full rounded-2xl border border-slate-800 bg-violet-500/20 px-4 text-sm font-semibold text-white outline-none placeholder:text-slate-600" placeholder="Ask Pardha to optimise campaign spend..." />
                {latestUser && <div className="ml-auto max-w-[78%] rounded-2xl bg-violet-500/25 px-5 py-4 text-sm font-semibold text-violet-50">{latestUser.content}</div>}
                {latestAssistant ? (
                  <div className="rounded-2xl bg-slate-900 px-5 py-4">
                    <p className="text-sm font-bold text-cyan-300">Pardha</p>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{latestAssistant.content}</p>
                  </div>
                ) : <DarkEmpty>No marketing conversation yet. Start with voice or type a request.</DarkEmpty>}
                {suggestedPrompts.length > 0 && (
                  <div>
                    <p className="mb-3 text-xs font-bold text-slate-500">Suggested prompts</p>
                    <div className="flex flex-wrap gap-2">
                      {suggestedPrompts.map((prompt) => <button key={prompt} onClick={() => setRequest(prompt)} className="rounded-full bg-slate-900 px-4 py-2 text-xs font-bold text-slate-300">{short(prompt, 48)}</button>)}
                    </div>
                  </div>
                )}
              </div>
            </DarkPanel>

            <DarkPanel title="Execution Timeline">
              <DarkList items={campaignTimeline} empty="No voice or campaign execution timeline yet." render={(item) => (
                <div key={item.id} className="grid grid-cols-[auto_1fr] gap-4">
                  <span className={`mt-1 h-3 w-3 rounded-full ${String(item.state).includes("pending") ? "bg-amber-400" : String(item.state).includes("error") ? "bg-rose-400" : "bg-emerald-400"}`} />
                  <div className="pb-4">
                    <p className="text-sm font-bold text-white">{item.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.detail}</p>
                  </div>
                </div>
              )} />
            </DarkPanel>
          </section>

          <DarkPanel title="Marketing Analytics">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <DarkList items={shownPerformance.slice(0, 6)} empty="No marketing analytics returned for this business." render={(row) => (
                <article key={`${row.campaign_id}-${row.channel}`} className="rounded-2xl border border-slate-800 bg-slate-900/55 p-4">
                  <p className="text-sm font-bold text-white">{row.channel}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-500">{row.impressions} impressions / {row.ctr}% CTR / {row.leads} leads / ROAS {row.roas}x</p>
                </article>
              )} />
            </div>
          </DarkPanel>
        </div>

        <aside className="grid content-start gap-6">
          <DarkPanel title="Live Intelligence">
            <div className="space-y-6">
              <div>
                <h3 className="mb-3 text-lg font-bold text-white">Current Campaigns</h3>
                <DarkList items={shownCampaigns.slice(0, 3)} empty="No active campaigns." render={(campaign) => (
                  <article key={campaign.campaign_id} className="rounded-2xl bg-slate-900 px-4 py-3">
                    <p className="text-sm font-bold text-white">{campaign.name}</p>
                    <p className="mt-1 text-xs text-slate-500">{campaign.channels?.join(", ") || "No channels"} / {label(campaign.status)}</p>
                  </article>
                )} />
              </div>
              <div>
                <h3 className="mb-3 text-lg font-bold text-white">Pending Approvals</h3>
                <DarkList items={(approvals || []).slice(0, 3)} empty="No approvals waiting." render={(approval) => (
                  <article key={approval.approval_id || approval.plan_id} className="rounded-2xl bg-violet-500/10 px-4 py-3">
                    <p className="text-sm font-bold text-white">{approval.title || approval.approval_type}</p>
                    <p className="mt-1 text-xs text-slate-500">{label(approval.risk_level || approval.status || "review")}</p>
                  </article>
                )} />
              </div>
              <div>
                <h3 className="mb-3 text-lg font-bold text-white">Top KPIs</h3>
                <DarkList items={metricRows.slice(0, 4)} empty="No marketing KPIs returned." render={(metric) => (
                  <article key={metric.label} className="rounded-2xl bg-slate-900 px-4 py-3">
                    <p className="text-xs font-bold uppercase text-slate-500">{metric.label}</p>
                    <p className="mt-2 text-2xl font-bold text-white">{metric.value}</p>
                    {metric.detail && <p className="mt-1 text-xs text-cyan-300">{metric.detail}</p>}
                  </article>
                )} />
              </div>
              <div>
                <h3 className="mb-3 text-lg font-bold text-white">AI Recommendations</h3>
                <DarkList items={recommendations.slice(0, 3)} empty="No recommendations yet." render={(item, index) => (
                  <article key={index} className="rounded-2xl bg-slate-900 px-4 py-3">
                    <p className="text-sm font-bold text-white">{typeof item === "string" ? item : item.title}</p>
                    {typeof item !== "string" && item.detail && <p className="mt-1 text-xs text-slate-500">{item.detail}</p>}
                  </article>
                )} />
              </div>
            </div>
          </DarkPanel>
        </aside>
      </section>
    </section>
  );
}

function OperationsTab({ data, connectorFailures }) {
  return (
    <section className="grid gap-5 xl:grid-cols-3">
      <Panel title="Operations" subtitle="Execution activity, event volume, and operating risks.">
        <div className="grid gap-3">
          <StateCard title="Open tasks" ok={data.tasks.some((task) => task.status !== "completed")} value={`${data.tasks.filter((task) => task.status !== "completed").length} open`} />
          <StateCard title="Events" ok={data.events.length > 0} value={`${data.events.length} recorded`} />
          <StateCard title="Connector gaps" ok={connectorFailures.length === 0} value={`${connectorFailures.length} action items`} />
        </div>
      </Panel>
      <Panel title="Recent events" subtitle="Latest operating stream.">
        <List items={data.events.slice(0, 8)} empty="No events recorded." render={(event) => <p key={event.event_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{label(event.event_type)}</strong><span className="block text-xs text-ink/45">{event.source_agent} to {event.target_agent} / {relativeTime(event.timestamp)}</span></p>} />
      </Panel>
      <Panel title="Unread notifications" subtitle="Current notification center.">
        <EmptyState>No unread notifications.</EmptyState>
      </Panel>
    </section>
  );
}

function ProjectsTab({ projects, jiraIssues }) {
  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <Panel title="Projects" subtitle="Scanned project inventory.">
        <List items={projects} empty="No scanned projects for this business." render={(project) => <p key={project.project_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{project.project_name}</strong><span className="block text-ink/45">{project.language} / {project.framework}</span><span className="block text-xs text-ink/35">{project.analysis?.file_count || 0} files / tests {project.analysis?.has_tests ? "detected" : "not detected"}</span></p>} />
      </Panel>
      <Panel title="Jira delivery" subtitle="Local Jira work items and readiness.">
        <List items={jiraIssues.slice(0, 10)} empty="No Jira items available." render={(issue) => <p key={issue.jira_issue_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{issue.jira_issue_key}</strong> {issue.summary}<span className="block text-xs text-ink/40">{label(issue.issue_type)} / {issue.status}</span></p>} />
      </Panel>
    </section>
  );
}

function KnowledgeTab({ knowledge, imports, onSubmit, title, setTitle, content, setContent, files, setFiles, onUpload, onDelete, search, setSearch, selected, setSelected, working }) {
  const filtered = knowledge.filter((item) => `${item.title} ${item.content} ${item.category} ${(item.tags || []).join(" ")}`.toLowerCase().includes(search.toLowerCase()));
  return (
    <section className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
      <div className="grid gap-5">
        <Panel title="Knowledge Center" subtitle="Drag and drop or browse files for the selected business.">
          <div
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              setFiles(Array.from(event.dataTransfer.files || []));
            }}
            className="rounded-2xl border border-dashed border-ink/20 bg-ink/[0.025] px-4 py-8 text-center"
          >
            <p className="text-sm font-semibold">Drop PDF, DOCX, PPTX, TXT, Markdown, CSV, or JSON files</p>
            <p className="mt-2 text-xs text-ink/45">{files.length ? `${files.length} file(s) selected` : "Duplicate files are detected before import."}</p>
            <input multiple type="file" accept=".pdf,.docx,.pptx,.txt,.md,.markdown,.csv,.json" onChange={(event) => setFiles(Array.from(event.target.files || []))} className="mt-5 w-full rounded-xl border border-ink/10 bg-white px-3 py-2 text-xs" />
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <ShellButton dark disabled={working || !files.length} onClick={() => onUpload(false)}>Import files</ShellButton>
              <ShellButton disabled={working || !files.length} onClick={() => onUpload(true)}>Re-import</ShellButton>
            </div>
          </div>
        </Panel>
        <Panel title="Manual knowledge" subtitle="Paste customer context when no file is available.">
          <form onSubmit={onSubmit} className="space-y-3">
            <input value={title} onChange={(event) => setTitle(event.target.value)} className="min-h-10 w-full rounded-xl border border-ink/10 px-3 text-sm outline-none" />
            <textarea value={content} onChange={(event) => setContent(event.target.value)} className="min-h-32 w-full rounded-xl border border-ink/10 p-3 text-sm outline-none" />
            <ShellButton dark disabled={working}><Icon name="plus" />Add knowledge</ShellButton>
          </form>
        </Panel>
        <Panel title="Import history" subtitle={`${imports.length} import records.`}>
          <List items={imports.slice(0, 8)} empty="No imports yet." render={(item) => <p key={item.import_id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{item.file_path}</strong><span className="block text-xs text-ink/45">{item.business_name} / {relativeTime(item.imported_at)}</span></p>} />
        </Panel>
      </div>
      <div className="grid gap-5">
        <Panel title="Knowledge library" subtitle={`${filtered.length}/${knowledge.length} records in current context.`}>
          <input value={search} onChange={(event) => setSearch(event.target.value)} className="mb-4 min-h-10 w-full rounded-xl border border-ink/10 px-3 text-sm outline-none" placeholder="Search knowledge" />
          <List items={filtered} empty="No knowledge available." render={(item) => <article key={item.knowledge_id} onClick={() => setSelected(item)} className="cursor-pointer rounded-xl border border-ink/10 p-4"><p className="text-xs font-bold uppercase tracking-wider text-coral">{label(item.category)}</p><p className="mt-2 font-semibold">{item.title}</p><p className="mt-1 text-sm leading-6 text-ink/55">{short(item.content, 240)}</p></article>} />
        </Panel>
        <Panel title="File preview" subtitle={selected?.title || "Select a knowledge record."}>
          {selected ? (
            <article>
              <p className="text-xs font-bold uppercase tracking-wider text-ink/40">{label(selected.category)} / {selected.source}</p>
              <p className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-ink/[0.035] p-4 text-sm leading-6 text-ink/65">{selected.content}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <ShellButton disabled={working} onClick={() => onDelete(selected.knowledge_id)}>Delete Knowledge</ShellButton>
              </div>
            </article>
          ) : <EmptyState>Select a record to preview content, metadata, and delete options.</EmptyState>}
        </Panel>
      </div>
    </section>
  );
}

function ObjectivesTab({ objectives, flow }) {
  return (
    <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
      <Panel title="Objectives" subtitle="Business goals currently driving execution.">
        <List items={objectives} empty="No objectives available." render={(objective) => <article key={objective.objective_id} className="rounded-xl border border-ink/10 p-4"><div className="mb-2 flex items-center justify-between gap-3"><p className="font-semibold">{objective.title}</p><span className="text-xs font-bold uppercase text-green-700">{label(objective.status)}</span></div><p className="text-sm leading-6 text-ink/55">{short(objective.description)}</p></article>} />
      </Panel>
      <Panel title="CEO to PM to CTO flow" subtitle="Agent collaboration trail.">
        <List items={flow} empty="Create an objective to see collaboration flow." render={(item) => <div key={item.collaboration_id} className="grid grid-cols-[auto_1fr] gap-3 rounded-xl bg-ink/[0.035] px-4 py-3"><span className="grid h-7 w-7 place-items-center rounded-full bg-acid text-xs font-bold">{item.step_order}</span><div><p className="text-sm font-semibold">{item.source_agent}{" -> "}{item.target_agent}</p><p className="text-xs uppercase tracking-wider text-ink/40">{label(item.event_type)}</p></div></div>} />
      </Panel>
    </section>
  );
}

function TasksTab({ tasks }) {
  const productTasks = tasks.filter((task) => task.payload?.work_type === "product");
  const engineeringTasks = tasks.filter((task) => task.payload?.work_type === "engineering");
  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <TaskColumn title="PM roadmap" tasks={productTasks} />
      <TaskColumn title="CTO engineering plan" tasks={engineeringTasks} />
    </section>
  );
}

function TaskColumn({ title, tasks }) {
  return (
    <Panel title={title} subtitle={`${tasks.length} generated tasks`}>
      <List items={tasks} empty="No tasks generated yet." render={(task) => <article key={task.task_id} className="rounded-xl border border-ink/10 p-4"><div className="mb-2 flex items-center justify-between gap-3"><p className="font-semibold">{task.title}</p><span className="text-xs font-bold uppercase text-ink/40">{label(task.status)}</span></div><p className="text-sm leading-6 text-ink/55">{short(task.description)}</p></article>} />
    </Panel>
  );
}

function ExecutionsTab({ executions, agents }) {
  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <Panel title="Agent executions" subtitle="Recent deterministic agent cycles.">
        <List items={executions.slice(0, 12)} empty="No agent executions recorded." render={(execution) => <p key={execution.execution_id} className="rounded-xl border border-ink/10 px-4 py-3 text-sm"><strong>{execution.agent_name}</strong><span className="block text-xs text-ink/45">{label(execution.status)} / {execution.duration_ms || 0}ms / {relativeTime(execution.completed_at || execution.started_at)}</span></p>} />
      </Panel>
      <Panel title="Active agents" subtitle="Registered execution roles.">
        <List items={agents} empty="No agents registered." render={(agent) => <p key={agent.id} className="rounded-xl bg-ink/[0.035] px-4 py-3 text-sm"><strong>{agent.name}</strong><span className="block text-xs text-ink/45">{agent.role} / {agent.status}</span></p>} />
      </Panel>
    </section>
  );
}

function SystemHealthTab({ health, diagnostics, ollama }) {
  const resources = health?.resources || {};
  return (
    <section className="grid gap-5 xl:grid-cols-3">
      <Panel title="Runtime" subtitle="Environment and process diagnostics.">
        <div className="grid gap-3">
          <StateCard title="Backend" ok={health?.backend?.status === "healthy"} value={health?.backend?.status || "unknown"} detail={`PID ${health?.backend?.pid || "n/a"}`} />
          <StateCard title="Environment" ok value={health?.runtime?.environment || "unknown"} />
          <StateCard title="Database type" ok={diagnostics?.connected} value={health?.database?.database_type || "unknown"} detail={diagnostics?.database_name} />
          <StateCard title="Memory" ok value={`${resources.memory_mb || 0} MB`} />
        </div>
      </Panel>
      <Panel title="Engines" subtitle="Scheduler, knowledge, agents, Ollama.">
        <div className="grid gap-3">
          <StateCard title="Scheduler" ok={diagnostics?.scheduler_status === "running"} value={diagnostics?.scheduler_status || "unknown"} />
          <StateCard title="Knowledge Engine" ok={diagnostics?.knowledge_import_status === "running"} value={diagnostics?.knowledge_import_status || "unknown"} />
          <StateCard title="Agent Engine" ok={(diagnostics?.agent_status?.active || 0) > 0} value={`${diagnostics?.agent_status?.active || 0} active`} />
          <StateCard title="Ollama" ok={ollama?.state === "Disabled" || ollama?.state === "Idle" || ollama?.state === "Running"} value={ollama?.state || "unknown"} detail={`Model ${ollama?.current_model || "llama3.2:3b"}`} />
        </div>
      </Panel>
      <Panel title="API diagnostics" subtitle="Dashboard request state.">
        <div className="grid gap-3">
          <StateCard title="Database tables" ok={(diagnostics?.tables_found || []).length > 0} value={`${(diagnostics?.tables_found || []).length} tables`} />
          <StateCard title="Last import" ok={Boolean(diagnostics?.last_import_time)} value={diagnostics?.last_import_time ? relativeTime(diagnostics.last_import_time) : "none"} />
          <StateCard title="Last execution" ok={Boolean(diagnostics?.last_agent_execution)} value={diagnostics?.last_agent_execution ? relativeTime(diagnostics.last_agent_execution) : "none"} />
          <StateCard title="VS Code" ok={Boolean(health?.vscode?.detected)} value={health?.vscode?.detected ? "detected" : "not detected"} />
        </div>
      </Panel>
    </section>
  );
}

function ConnectorsTab({ connectors, onTest }) {
  return (
    <section className="grid gap-5 xl:grid-cols-2">
      {connectors.map((connector) => (
        <Panel key={connector.provider} title={connector.name} subtitle={connector.message} action={<ShellButton onClick={() => onTest(connector.provider)}>Test Connection</ShellButton>}>
          <div className="grid gap-3 md:grid-cols-2">
            <StateCard title="Connection" ok={connector.connected} value={connector.connected ? "connected" : "disconnected"} />
            <StateCard title="Authentication" ok={connector.environment_valid} value={label(connector.authentication_status)} />
            <StateCard title="Connected Account" ok={connector.account_count > 0} value={`${connector.account_count}`} detail={connector.account_count ? "Account present" : "No account connected"} />
            <StateCard title="Last sync" ok={Boolean(connector.last_sync)} value={connector.last_sync ? relativeTime(connector.last_sync) : "never"} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <ShellButton onClick={() => onTest(connector.provider)}>Reconnect</ShellButton>
            <ShellButton onClick={() => onTest(connector.provider)}>Disconnect</ShellButton>
          </div>
          <div className="mt-4 rounded-xl bg-ink/[0.035] px-4 py-3 text-xs leading-5 text-ink/55">
            <strong>Required configuration:</strong> {connector.required_environment?.length ? connector.required_environment.join(", ") : "Local runtime detection"}
          </div>
          {connector.missing_environment?.length > 0 && <p className="mt-3 rounded-xl bg-coral/10 px-4 py-3 text-xs leading-5 text-coral">Missing env: {connector.missing_environment.join(", ")}</p>}
        </Panel>
      ))}
    </section>
  );
}

export default App;
