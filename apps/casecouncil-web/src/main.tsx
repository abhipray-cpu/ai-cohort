import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Scale,
  FileText,
  ShieldCheck,
  Plus,
  LogOut,
  Settings,
  ArrowLeft,
  AlertTriangle,
  Download,
  Clock,
  Search,
  X,
  ChevronRight,
  CheckCircle2,
} from "lucide-react";
import {
  highlight,
  voteLabel,
  confidenceLabel,
  canReview,
  roleName,
  readable,
  pendingPacketLabel,
  reviewResponseSeed,
} from "./domain";
import "./style.css";

type Workspace = { id: string; name: string; role: string };
type Policy = {
  name: string;
  instructions: string;
  required_documents: string[];
  egress_enabled: boolean;
};
type WorkspaceDetail = Workspace & {
  policy: Policy;
  policy_revision: number;
  hold: string | null;
};
type Context = {
  title: string;
  jurisdiction?: string;
  product?: string;
  issues: { id: string; title: string }[];
  facts: string;
  draft: string;
  missing: string[];
};
type Citation = {
  source_id: string;
  start: number;
  end: number;
  quote: string;
};
type Source = {
  id: string;
  name: string;
  text?: string;
  pages: number;
  partial: boolean;
  kind?: string;
  text_hash: string;
  mapping: string;
};
type Case = {
  id: string;
  workspace: string;
  creator: string;
  revision: number;
  context: Context;
  sources: Source[];
  role: string;
};
type Candidate = {
  id: string;
  issue_id: string;
  disposition: string;
  remedy: string;
  rationale: string;
  counterargument: string;
  conditions: string[];
  citations: Citation[];
  missing: string[];
  roles?: string[];
};
type Proposal = {
  issues: Candidate[];
  new_issues: string[];
  critique_responses: { finding_id: string; action: string; reason: string }[];
};
type Finding = {
  id: string;
  issue_id: string;
  target_role: string;
  severity: string;
  assertion: string;
  reason: string;
  citations: Citation[];
};
type Choice = {
  candidate_id: string | null;
  reason: string;
  missing: string[];
};
type ConsensusIssue = {
  issue_id: string;
  status: string;
  winner: string | null;
  votes: Record<string, number>;
  denominator: number;
  ballots: Record<string, Choice>;
  blockers: string[];
  route: string;
  qualified: boolean;
};
type Packet = {
  proposals: Record<string, Proposal>;
  critique: { findings: Finding[] } | null;
  registry?: { candidates: Candidate[] };
  consensus: {
    issues: ConsensusIssue[];
    confidence_band: string;
    blockers: string[];
  } | null;
  synthesis: {
    observations: { text: string; citations: Citation[] }[];
    proposed_response: string;
    next_actions: string[];
  } | null;
  unavailable?: string[];
  review_requirements: string[];
  review_questions?: Record<string, string>;
  limitations: string[];
  approved: boolean;
};
type JobSummary = {
  id: string;
  state: string;
  calls: number;
  error: string | null;
  created: number;
};
type Job = JobSummary & {
  actor: string;
  packet: Packet | null;
  packet_hash: string | null;
  checkpoints: Record<string, unknown>;
  attempts: {
    stage: string;
    receipt: {
      status: string;
      usage: { input_tokens: number; output_tokens: number } | null;
    } | null;
  }[];
  reviews: { actor: string; body: { response: string; reason: string } }[];
  incidents?: {
    id: string;
    attempt_id: string;
    usage_remains_unknown: boolean;
    tool_safety_unverified: boolean;
  }[];
};
type Clearance = {
  id: string;
  basis: string;
  reference: string;
  expires: number;
  egress: boolean;
};
type Preview = {
  binding: string;
  context: Context;
  policy: Policy;
  blockers: string[];
  evidence: {
    spans: { source_id: string; start: number; end: number; text: string }[];
    partial: boolean;
    selected_chars: number;
    total_chars: number;
  };
};
let csrf = "";
const retryKeys = new Map<string, string>();
async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const form = body instanceof FormData;
  const signature =
    method +
    path +
    (form
      ? Array.from(body.entries())
          .map(
            ([k, v]) =>
              k +
              ":" +
              (v instanceof File ? v.name + v.size + v.lastModified : v),
          )
          .join("|")
      : JSON.stringify(body));
  const key = retryKeys.get(signature) || crypto.randomUUID();
  retryKeys.set(signature, key);
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      ...(form ? {} : { "Content-Type": "application/json" }),
      "X-CSRF-Token": csrf,
      "Idempotency-Key": key,
    },
    body:
      body === undefined
        ? undefined
        : form
          ? (body as FormData)
          : JSON.stringify(body),
  });
  if (!response.ok) {
    if (response.status === 401)
      window.dispatchEvent(new Event("casecouncil-auth-lost"));
    let detail = "Request could not be completed.";
    try {
      detail = (await response.json()).detail || detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : "Invalid request.");
  }
  retryKeys.delete(signature);
  return response.status === 204 ? (undefined as T) : response.json();
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog ref={ref} onCancel={onClose} aria-label={title}>
      <header>
        <div>
          <p className="eyebrow">CASECOUNCIL WORKSPACE</p>
          <h2>{title}</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </header>
      {children}
    </dialog>
  );
}
function App() {
  const [user, setUser] = useState<{ name: string } | null>(null),
    [boot, setBoot] = useState(true),
    [workspaces, setWorkspaces] = useState<Workspace[]>([]),
    [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null),
    [cases, setCases] = useState<Case[]>([]),
    [selected, setSelected] = useState<Case | null>(null),
    [jobs, setJobs] = useState<JobSummary[]>([]),
    [job, setJob] = useState<Job | null>(null),
    [rights, setRights] = useState<Clearance[]>([]),
    [preview, setPreview] = useState<Preview | null>(null),
    [modal, setModal] = useState<string | null>(null),
    [tab, setTab] = useState("decision"),
    [issue, setIssue] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState(""),
    [evidence, setEvidence] = useState<{
      source: Source;
      citation?: Citation;
    } | null>(null);
  const isWriter = !!workspace && ["owner", "analyst"].includes(workspace.role);
  async function task(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operation failed.");
    } finally {
      setBusy(false);
    }
  }
  async function restore() {
    const me = await api<{
      name: string;
      csrf: string;
      workspaces: Workspace[];
    }>("/api/me");
    csrf = me.csrf;
    setUser({ name: me.name });
    setWorkspaces(me.workspaces);
  }
  useEffect(() => {
    restore()
      .catch(() => {})
      .finally(() => setBoot(false));
    const lost = () => {
      setUser(null);
      setWorkspace(null);
      setSelected(null);
      setJob(null);
      setEvidence(null);
      setModal(null);
    };
    window.addEventListener("casecouncil-auth-lost", lost);
    return () => window.removeEventListener("casecouncil-auth-lost", lost);
  }, []);
  async function openWorkspace(id: string) {
    const w = await api<WorkspaceDetail>(`/api/workspaces/${id}`);
    setWorkspace(w);
    setCases(await api<Case[]>(`/api/workspaces/${id}/cases`));
    setRights(await api<Clearance[]>(`/api/workspaces/${id}/rights`));
    setSelected(null);
    setJob(null);
    setEvidence(null);
  }
  async function openCase(id: string) {
    const c = await api<Case>(`/api/cases/${id}`);
    setSelected(c);
    setIssue(c.context.issues[0]?.id || "");
    const list = await api<JobSummary[]>(`/api/cases/${id}/runs`);
    setJobs(list);
    setJob(list[0] ? await api<Job>(`/api/runs/${list[0].id}`) : null);
    setEvidence(null);
    setTab("decision");
  }
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.state)) return;
    const timer = window.setInterval(() => {
      api<Job>(`/api/runs/${job.id}`)
        .then(setJob)
        .catch((e) => setError(e.message));
    }, 2000);
    return () => clearInterval(timer);
  }, [job?.id, job?.state]);
  async function download(reviewed: boolean, format = "json") {
    if (!job) return;
    const r = await fetch(
      `/api/runs/${job.id}/export?reviewed=${reviewed}&format=${format}`,
      { credentials: "same-origin", cache: "no-store" },
    );
    if (!r.ok)
      throw new Error(
        "Export is not authorized or the packet is no longer current.",
      );
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = `casecouncil-${job.id}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }
  async function showCitation(c: Citation) {
    setEvidence({
      source: await api<Source>(`/api/sources/${c.source_id}`),
      citation: c,
    });
  }
  function citationButtons(citations: Citation[]) {
    return (
      <div className="citations">
        {citations.map((c, n) => (
          <button
            key={n}
            className="citation"
            onClick={() => task(() => showCitation(c))}
          >
            <FileText size={12} /> Source {n + 1} · {c.start}–{c.end}
          </button>
        ))}
      </div>
    );
  }
  if (boot)
    return (
      <main className="loading" aria-live="polite">
        Connecting to your review desk…
      </main>
    );
  if (!user)
    return (
      <div className="login-layout">
        <section className="login-story">
          <div className="brand">
            <Scale /> CaseCouncil
          </div>
          <p className="eyebrow">A SECOND LOOK. A STRONGER DECISION.</p>
          <h1>
            Challenge the reasoning.
            <br />
            Keep the evidence.
          </h1>
          <p>
            An adversarial review desk for motor-insurance complaints. Three
            perspectives, an independent critique, and a human in control.
          </p>
          <div className="login-principles">
            <span>
              <ShieldCheck />
              Evidence before agreement
            </span>
            <span>
              <FileText />
              Dissent stays in the record
            </span>
            <span>
              <CheckCircle2 />
              No automatic customer actions
            </span>
          </div>
          <footer>
            Advisory review · Not an insurer, legal adviser or ombudsman
          </footer>
        </section>
        <section className="login-form">
          <p className="eyebrow">YOUR REVIEW WORKSPACE</p>
          <h2>Welcome back.</h2>
          <p className="muted">Sign in with your configured service account.</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              task(async () => {
                const r = await api<{ name: string; csrf: string }>(
                  "/api/session",
                  "POST",
                  { username: f.get("username"), password: f.get("password") },
                );
                csrf = r.csrf;
                await restore();
              });
            }}
          >
            <label>
              Username
              <input name="username" autoComplete="username" required />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                minLength={12}
                required
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button disabled={busy}>
              Sign in <ChevronRight size={16} />
            </button>
          </form>
          <p className="small muted">
            Service credentials are configured on your host. There are no shared
            demo credentials.
          </p>
        </section>
      </div>
    );
  const packet = job?.packet,
    ci = packet?.consensus?.issues.find((i) => i.issue_id === issue),
    candidates = packet?.registry?.candidates || [];
  return (
    <div className="app">
      <aside className="nav">
        <a className="brand" href="/" onClick={(e) => e.preventDefault()}>
          <Scale /> CaseCouncil
        </a>
        <span className="nav-caption">DECISION REVIEW DESK</span>
        <label className="workspace-picker">
          Workspace
          <select
            value={workspace?.id || ""}
            onChange={(e) => task(() => openWorkspace(e.target.value))}
          >
            <option value="" disabled>
              Select workspace
            </option>
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        <button className="nav-action" onClick={() => setModal("workspace")}>
          <Plus size={16} /> Create workspace
        </button>
        <div className="nav-divider" />
        <button
          className="nav-link active"
          onClick={() => {
            setSelected(null);
            setJob(null);
          }}
        >
          <FileText size={17} /> Complaint reviews <span>{cases.length}</span>
        </button>
        {workspace?.role === "owner" && (
          <button className="nav-link" onClick={() => setModal("settings")}>
            <Settings size={17} /> Policy & access
          </button>
        )}
        <div className="nav-note">
          <ShieldCheck size={18} />
          <strong>Human judgement stays final.</strong>
          <p>
            Agreement is not proof. Every response remains a draft until an
            authorized reviewer checks it.
          </p>
        </div>
        <div className="account">
          <span className="avatar">{user.name[0].toUpperCase()}</span>
          <div>
            <strong>{user.name}</strong>
            <small>{workspace?.role || "Signed in"}</small>
          </div>
          <button
            className="icon-button"
            aria-label="Sign out"
            onClick={() =>
              task(async () => {
                await api("/api/session", "DELETE");
                setUser(null);
                setSelected(null);
                setJob(null);
                setWorkspace(null);
                setEvidence(null);
              })
            }
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <span>
            {workspace?.name || "Your workspaces"} <ChevronRight size={13} />{" "}
            {selected ? "Case review" : "Complaint reviews"}
          </span>
          <span className="badge">ADVISORY · HUMAN REVIEW REQUIRED</span>
        </header>
        <div className="messages" aria-live="polite">
          {error && (
            <div role="alert" className="error">
              <AlertTriangle size={17} />
              {error}
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {notice && <div className="notice">{notice}</div>}
          {workspace?.hold && (
            <div className="error">
              Runtime circuit open: {workspace.hold}. No new inference until
              usage/runtime is reconciled.
            </div>
          )}
        </div>
        {!selected ? (
          <section className="queue">
            <div className="page-heading">
              <div>
                <p className="eyebrow">
                  EVIDENCE. PERSPECTIVE. ACCOUNTABILITY.
                </p>
                <h1>
                  Make the next decision
                  <br />a better-supported one.
                </h1>
                <p className="muted">
                  A dedicated place to challenge a complaint response before it
                  leaves your team.
                </p>
              </div>
              {isWriter && (
                <button onClick={() => setModal("case")}>
                  <Plus size={16} /> New complaint review
                </button>
              )}
            </div>
            <div className="stats">
              <article>
                <span>Cases in workspace</span>
                <strong>{cases.length}</strong>
                <small>Actual case records, not demo activity</small>
              </article>
              <article>
                <span>Your access</span>
                <strong className="text-stat">
                  {workspace ? readable(workspace.role) : "Select a workspace"}
                </strong>
                <small>Checked again on every action</small>
              </article>
              <article>
                <span>Decision standard</span>
                <strong className="text-stat">Evidence first</strong>
                <small>Three roles · No forced consensus</small>
              </article>
            </div>
            {!workspace ? (
              <div className="empty">
                <Scale size={38} />
                <h2>Your review desk starts here.</h2>
                <p>
                  Create a workspace or select one you have been granted access
                  to.
                </p>
                <button onClick={() => setModal("workspace")}>
                  Create workspace
                </button>
              </div>
            ) : (
              <>
                <div className="section-heading">
                  <h2>
                    Complaint reviews{" "}
                    <span className="count">{cases.length}</span>
                  </h2>
                  <label className="search">
                    <Search size={16} />
                    <input
                      aria-label="Search complaint reviews"
                      placeholder="Search case titles…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                </div>
                {!cases.length ? (
                  <div className="empty">
                    <FileText size={32} />
                    <h3>No complaint cases yet.</h3>
                    <p>
                      Owners should approve policy, record source rights and
                      grant an independent reviewer access before running a
                      case.
                    </p>
                    {workspace.role === "owner" && (
                      <button
                        className="secondary"
                        onClick={() => setModal("settings")}
                      >
                        Configure policy & access
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="case-table">
                    <div className="table-head">
                      <span>CASE</span>
                      <span>ISSUES</span>
                      <span>REVISION</span>
                      <span>CREATED</span>
                    </div>
                    {cases
                      .filter((c) =>
                        c.context.title
                          .toLowerCase()
                          .includes(search.toLowerCase()),
                      )
                      .map((c) => (
                        <button
                          className="case-row"
                          key={c.id}
                          onClick={() => task(() => openCase(c.id))}
                        >
                          <span>
                            <FileText size={19} />
                            <strong>{c.context.title}</strong>
                          </span>
                          <span>{c.context.issues.length} declared</span>
                          <span>v{c.revision}</span>
                          <span>
                            {new Date(
                              (c as unknown as { created: number }).created *
                                1000,
                            ).toLocaleDateString()}{" "}
                            <ChevronRight size={15} />
                          </span>
                        </button>
                      ))}
                  </div>
                )}
              </>
            )}
          </section>
        ) : (
          <>
            <section className="case-heading">
              <button
                className="text-button"
                onClick={() => {
                  setSelected(null);
                  setJob(null);
                  setEvidence(null);
                }}
              >
                <ArrowLeft size={14} /> All reviews
              </button>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">MOTOR INSURANCE · UNITED KINGDOM</p>
                  <h1>{selected.context.title}</h1>
                  <p className="muted">
                    Source revision {selected.revision} ·{" "}
                    {selected.sources.length} active documents · Owner:{" "}
                    {selected.creator}
                  </p>
                </div>
                <div className="actions">
                  {isWriter && (
                    <button
                      className="secondary"
                      onClick={() => setModal("edit")}
                    >
                      Edit context
                    </button>
                  )}
                  {isWriter && (
                    <button
                      disabled={
                        busy || ["queued", "running"].includes(job?.state || "")
                      }
                      onClick={() =>
                        task(async () => {
                          setPreview(
                            await api<Preview>(
                              `/api/cases/${selected.id}/egress-preview`,
                            ),
                          );
                          setModal("egress");
                        })
                      }
                    >
                      Prepare review <ChevronRight size={16} />
                    </button>
                  )}
                </div>
              </div>
              <div
                className="case-tabs"
                role="tablist"
                aria-label="Case sections"
              >
                {[
                  ["decision", "Decision desk"],
                  ["sources", "Sources & context"],
                  ["history", "Run history"],
                ].map(([k, v]) => (
                  <button
                    key={k}
                    role="tab"
                    aria-selected={tab === k}
                    className={tab === k ? "selected" : ""}
                    onClick={() => setTab(k)}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </section>
            {tab === "sources" ? (
              <section className="content-card sources">
                <h2>Source material & declared facts</h2>
                <p className="muted">
                  Only material you are authorized to process. Rights
                  attestation is not an automatically verified licence.
                </p>
                {isWriter && (
                  <UploadSources
                    caseData={selected}
                    rights={rights}
                    busy={busy}
                    run={task}
                    onDone={async () => {
                      await openCase(selected.id);
                      setTab("sources");
                    }}
                  />
                )}
                <div className="source-list">
                  {selected.sources.map((s) => (
                    <button
                      className="source-row"
                      key={s.id}
                      onClick={() =>
                        task(async () =>
                          setEvidence({
                            source: await api<Source>(`/api/sources/${s.id}`),
                          }),
                        )
                      }
                    >
                      <FileText />
                      <div>
                        <strong>{s.name}</strong>
                        <small>
                          {s.kind} · {s.pages || "Text"}{" "}
                          {s.pages ? "pages" : ""} ·{" "}
                          {s.partial ? "PARTIAL EXTRACTION" : "Text extracted"}
                        </small>
                      </div>
                      <ChevronRight size={16} />
                    </button>
                  ))}
                </div>
                <h3>Attributed case facts</h3>
                <p className="prewrap">
                  {selected.context.facts || "No manually supplied facts."}
                </p>
                <h3>Handler’s proposed response</h3>
                <p className="prewrap">
                  {selected.context.draft ||
                    "No response supplied. Agents will independently propose alternatives."}
                </p>
                <h3>Declared missing evidence</h3>
                <ul>
                  {selected.context.missing.map((m, n) => (
                    <li key={n}>{m}</li>
                  ))}
                </ul>
                {workspace?.role === "owner" && (
                  <button
                    className="danger secondary"
                    onClick={() =>
                      task(async () => {
                        const p = await api<{
                          revision: number;
                          warning: string;
                        }>(`/api/cases/${selected.id}/erasure-preview`);
                        if (
                          !window.confirm(
                            p.warning +
                              "\nPermanently erase this case and its derived content?",
                          )
                        )
                          return;
                        const reason = window.prompt(
                          "Record your retention/erasure reason (at least 10 characters):",
                        );
                        if (!reason) return;
                        await api(`/api/cases/${selected.id}`, "DELETE", {
                          revision: p.revision,
                          reason,
                        });
                        await openWorkspace(selected.workspace);
                        setNotice(
                          "Case erased. Backups and already downloaded copies require separate retention review.",
                        );
                      })
                    }
                  >
                    Erase case content…
                  </button>
                )}
              </section>
            ) : tab === "history" ? (
              <section className="content-card">
                <h2>Run history</h2>
                <p className="muted">
                  Old packets remain historical. A changed source cannot
                  silently inherit a review.
                </p>
                {jobs.map((j) => (
                  <button
                    key={j.id}
                    className="history-row"
                    onClick={() =>
                      task(async () => {
                        setJob(await api<Job>(`/api/runs/${j.id}`));
                        setTab("decision");
                      })
                    }
                  >
                    <span>
                      <Clock size={17} />{" "}
                      {new Date(j.created * 1000).toLocaleString()}
                    </span>
                    <span>{readable(j.state)}</span>
                    <span>{j.calls} calls</span>
                  </button>
                ))}
                {job?.attempts.map((a, n) => (
                  <div className="receipt" key={n}>
                    <strong>{readable(a.stage)}</strong>
                    <span>
                      {a.receipt?.status || "Pending / usage not settled"}
                    </span>
                    <small>
                      {a.receipt?.usage
                        ? `${a.receipt.usage.input_tokens.toLocaleString()} input · ${a.receipt.usage.output_tokens.toLocaleString()} output tokens`
                        : "Usage unknown — never assumed free"}
                    </small>
                  </div>
                ))}
                {job?.incidents?.map((incident) => (
                  <div className="receipt" role="alert" key={incident.id}>
                    <strong>Owner-accepted runtime incident</strong>
                    <span>
                      Usage remains unknown. Tool safety is unverified.
                    </span>
                    <small>
                      Full reservation retained. Incident {incident.id}
                    </small>
                  </div>
                ))}
              </section>
            ) : !job ? (
              <section className="empty">
                <Scale size={38} />
                <h2>Ready for a second look?</h2>
                <p>
                  Add authorized source material, confirm the issues and inspect
                  the egress preview. No analysis runs until explicitly
                  authorized.
                </p>
              </section>
            ) : (
              <>
                <div
                  className={`run-banner ${job.state === "stale" ? "warning" : ""}`}
                >
                  <div>
                    <span className="status-dot" />
                    <strong>{readable(job.state)}</strong>
                    <span>
                      {Object.keys(job.checkpoints).length} checkpoints ·{" "}
                      {job.calls}/22 calls
                    </span>
                  </div>
                  {["queued", "running"].includes(job.state) && isWriter && (
                    <button
                      className="secondary"
                      onClick={() =>
                        task(async () => {
                          await api(`/api/runs/${job.id}/cancel`, "POST");
                          setJob(await api<Job>(`/api/runs/${job.id}`));
                        })
                      }
                    >
                      Cancel run
                    </button>
                  )}
                  {job.state === "stale" && (
                    <span>
                      Historical only · reviewed-current export blocked
                    </span>
                  )}
                </div>
                <div className="review-grid">
                  <aside className="issues-panel">
                    <p className="eyebrow">DECLARED ISSUES</p>
                    {selected.context.issues.map((i, n) => (
                      <button
                        key={i.id}
                        className={issue === i.id ? "issue selected" : "issue"}
                        onClick={() => setIssue(i.id)}
                      >
                        <span className="issue-number">
                          {String(n + 1).padStart(2, "0")}
                        </span>
                        <span>{i.title}</span>
                      </button>
                    ))}
                    <div className="coverage-note">
                      <ShieldCheck size={18} />
                      <strong>Confidence is not a vote count.</strong>
                      <p>
                        {packet?.consensus
                          ? confidenceLabel(packet.consensus.confidence_band)
                          : "Assessment incomplete"}
                      </p>
                      <small>
                        Same-model roles are correlated. Human review remains
                        required.
                      </small>
                    </div>
                  </aside>
                  <section className="decision-panel">
                    {!packet ? (
                      <div className="empty">
                        <Clock size={30} />
                        <h3>{pendingPacketLabel(job.state)}</h3>
                        <p>
                          Valid stage checkpoints are retained. A completed
                          stage is not a completed complaint decision.
                        </p>
                        <div className="stage-list">
                          {Object.keys(job.checkpoints).map((s) => (
                            <span key={s}>
                              <CheckCircle2 size={13} />
                              {readable(s)}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="section-heading">
                          <div>
                            <p className="eyebrow">
                              COMPUTED AGREEMENT · NOT A BINDING DECISION
                            </p>
                            <h2>
                              {ci
                                ? readable(ci.status)
                                : "Manual investigation required"}
                            </h2>
                          </div>
                          <span className="badge">UNAPPROVED DRAFT</span>
                        </div>
                        {ci?.winner && (
                          <div className="recommendation">
                            <span className="eyebrow">PROPOSED RESOLUTION</span>
                            <h3>
                              {readable(
                                candidates.find((c) => c.id === ci.winner)
                                  ?.disposition || "undetermined",
                              )}
                            </h3>
                            <p>
                              {
                                candidates.find((c) => c.id === ci.winner)
                                  ?.remedy
                              }
                            </p>
                            <small>{ci.route && readable(ci.route)}</small>
                          </div>
                        )}
                        {!!ci?.blockers.length && (
                          <div className="blockers">
                            <h3>
                              <AlertTriangle size={17} /> Open review questions
                            </h3>
                            <ul>
                              {ci.blockers.map((b, n) => (
                                <li key={n}>{b}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <h3 className="subheading">
                          Three perspectives. Evidence attached.
                        </h3>
                        {Object.entries(packet.proposals || {}).map(
                          ([role, p]) => {
                            const proposal = p.issues?.find(
                              (i) => i.issue_id === issue,
                            );
                            return (
                              <article className="proposal" key={role}>
                                <header>
                                  <span className={`role-marker ${role}`} />
                                  <strong>{roleName(role)}</strong>
                                  <span className="badge">
                                    {proposal
                                      ? readable(proposal.disposition)
                                      : "Unavailable"}
                                  </span>
                                </header>
                                {proposal && (
                                  <>
                                    <p>{proposal.rationale}</p>
                                    <p className="muted">
                                      <strong>
                                        Strongest counterargument:
                                      </strong>{" "}
                                      {proposal.counterargument}
                                    </p>
                                    <p className="muted">
                                      <strong>Proposal:</strong>{" "}
                                      {proposal.remedy}
                                    </p>
                                    {proposal.conditions.length > 0 && (
                                      <ul>
                                        {proposal.conditions.map((c, n) => (
                                          <li key={n}>{c}</li>
                                        ))}
                                      </ul>
                                    )}
                                    {citationButtons(proposal.citations)}
                                    {p.critique_responses.map((r) => (
                                      <p
                                        className="small muted"
                                        key={r.finding_id}
                                      >
                                        <strong>
                                          {r.finding_id} · {r.action}:
                                        </strong>{" "}
                                        {r.reason} (not human clearance)
                                      </p>
                                    ))}
                                  </>
                                )}
                              </article>
                            );
                          },
                        )}
                        <h3 className="subheading">Critic’s challenge</h3>
                        {packet.critique?.findings
                          .filter((f) => f.issue_id === issue)
                          .map((f) => (
                            <article className="critique" key={f.id}>
                              <div>
                                <span className="badge">{f.severity}</span>
                                <strong>
                                  {roleName(f.target_role)} · {f.id}
                                </strong>
                              </div>
                              <blockquote>{f.assertion}</blockquote>
                              <p>{f.reason}</p>
                              {citationButtons(f.citations)}
                              <small>
                                Proposer acceptance does not constitute human
                                resolution.
                              </small>
                            </article>
                          ))}
                        {packet.critique?.findings.length === 0 && (
                          <p className="muted">
                            No critic findings were returned. This is not proof
                            of correctness.
                          </p>
                        )}
                        <h3 className="subheading">
                          Ballots & retained dissent
                        </h3>
                        <div className="ballot-list">
                          {["customer", "insurer", "fairness"].map((role) => {
                            const b = ci?.ballots[role];
                            return (
                              <div key={role}>
                                <strong>{roleName(role)}</strong>
                                <span>
                                  {b
                                    ? b.candidate_id
                                      ? b.candidate_id === ci?.winner
                                        ? "Selected majority candidate"
                                        : "Different candidate — dissent retained"
                                      : "Explicit abstention"
                                    : "Unavailable — not an abstention"}
                                </span>
                                <small>{b?.reason}</small>
                              </div>
                            );
                          })}
                        </div>
                        {ci && (
                          <p className="small muted">
                            {voteLabel(
                              ci.winner ? ci.votes[ci.winner] || 0 : 0,
                            )}{" "}
                            support the selected candidate. The denominator
                            never shrinks.
                          </p>
                        )}
                        <h3 className="subheading">
                          AI advisory review summary · not a customer letter
                        </h3>
                        <p className="draft prewrap">
                          {packet.synthesis?.proposed_response ||
                            "Synthesis unavailable. The valid earlier proposals, evidence and disagreement are retained above."}
                        </p>
                        {packet.synthesis?.next_actions.length && (
                          <ul>
                            {packet.synthesis.next_actions.map((a, n) => (
                              <li key={n}>{a}</li>
                            ))}
                          </ul>
                        )}
                        <div className="limitations">
                          {packet.limitations?.map((l, n) => (
                            <p key={n}>{l}</p>
                          ))}
                        </div>
                        <div className="export-actions">
                          <button
                            className="secondary"
                            onClick={() => task(() => download(false))}
                          >
                            <Download size={15} /> Draft JSON
                          </button>
                          <button
                            className="secondary"
                            onClick={() => task(() => download(false, "html"))}
                          >
                            Print-friendly draft
                          </button>
                          {workspace &&
                            canReview(
                              workspace.role,
                              user.name,
                              selected.creator,
                              job.actor,
                            ) &&
                            ["draft_ready", "manual_required"].includes(
                              job.state,
                            ) && (
                              <button onClick={() => setModal("review")}>
                                Record independent review
                              </button>
                            )}
                          {job.reviews.length > 0 &&
                            ["owner", "reviewer"].includes(
                              workspace?.role || "",
                            ) &&
                            ["draft_ready", "manual_required"].includes(
                              job.state,
                            ) && (
                              <button
                                className="secondary"
                                onClick={() => task(() => download(true))}
                              >
                                Reviewed export
                              </button>
                            )}
                        </div>
                        {job.reviews.map((r, n) => (
                          <div className="human-review" key={n}>
                            <strong>Human review · {r.actor}</strong>
                            <p>{r.body.reason}</p>
                            <p className="prewrap">{r.body.response}</p>
                          </div>
                        ))}
                      </>
                    )}
                  </section>
                  <aside className="evidence-panel">
                    <div className="section-heading">
                      <h3>
                        <FileText size={17} /> Evidence
                      </h3>
                      {evidence && (
                        <button
                          className="icon-button"
                          aria-label="Clear evidence"
                          onClick={() => setEvidence(null)}
                        >
                          <X size={16} />
                        </button>
                      )}
                    </div>
                    {evidence ? (
                      <Evidence
                        source={evidence.source}
                        citation={evidence.citation}
                      />
                    ) : (
                      <div className="evidence-empty">
                        <FileText size={28} />
                        <p>
                          Select a citation to inspect the exact redacted
                          source.
                        </p>
                        <small>
                          Source references use Unicode character offsets, not
                          raw PDF coordinates.
                        </small>
                      </div>
                    )}
                  </aside>
                </div>
              </>
            )}
          </>
        )}
        <footer className="workspace-footer">
          CaseCouncil · Evidence-backed advisory review{" "}
          <span>
            No automated rejection, payout or customer-message sending.
          </span>
        </footer>
      </main>
      {modal === "workspace" && (
        <Modal title="Create workspace" onClose={() => setModal(null)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              task(async () => {
                const r = await api<{ id: string }>("/api/workspaces", "POST", {
                  name: f.get("name"),
                });
                await restore();
                await openWorkspace(r.id);
                setModal(null);
              });
            }}
          >
            <label>
              Client / workspace name
              <input name="name" required minLength={3} maxLength={150} />
            </label>
            <p className="small muted">
              Cases, permissions, policy and usage are isolated to this
              workspace.
            </p>
            <button disabled={busy}>Create workspace</button>
          </form>
        </Modal>
      )}
      {(modal === "case" || modal === "edit") && workspace && (
        <Modal
          title={
            modal === "edit" ? "Edit case context" : "New complaint review"
          }
          onClose={() => setModal(null)}
        >
          <CaseForm
            initial={modal === "edit" ? selected?.context : undefined}
            busy={busy}
            submit={(value) =>
              task(async () => {
                const r =
                  modal === "edit" && selected
                    ? await api<{ id: string }>(
                        `/api/cases/${selected.id}`,
                        "PUT",
                        { revision: selected.revision, context: value },
                      )
                    : await api<{ id: string }>("/api/cases", "POST", {
                        workspace: workspace.id,
                        context: value,
                      });
                setCases(
                  await api<Case[]>(`/api/workspaces/${workspace.id}/cases`),
                );
                await openCase(r.id);
                setModal(null);
              })
            }
          />
        </Modal>
      )}
      {modal === "settings" && workspace && (
        <Modal
          title="Policy, source rights & access"
          onClose={() => setModal(null)}
        >
          <SettingsPanel
            workspace={workspace}
            rights={rights}
            run={task}
            busy={busy}
            onRefresh={async () => {
              setWorkspace(
                await api<WorkspaceDetail>(`/api/workspaces/${workspace.id}`),
              );
              setRights(
                await api<Clearance[]>(
                  `/api/workspaces/${workspace.id}/rights`,
                ),
              );
            }}
          />
        </Modal>
      )}
      {modal === "egress" && preview && selected && (
        <Modal
          title="Authorize this exact review context"
          onClose={() => setModal(null)}
        >
          <div className="warning">
            <AlertTriangle size={18} />
            <p>
              Installed Codex may use remote inference. Authorization covers
              this frozen snapshot and derived debate outputs: up to 22 calls
              and 30 minutes, not an unlimited debate or a hard token-cost cap.
            </p>
          </div>
          <h3>Declared coverage</h3>
          <p>
            {preview.evidence.selected_chars.toLocaleString()} of{" "}
            {preview.evidence.total_chars.toLocaleString()} source characters
            selected ·{" "}
            {preview.evidence.partial ? "PARTIAL" : "Selected text fits"}
          </p>
          <ul>
            {preview.blockers.map((b, n) => (
              <li key={n}>{b}</li>
            ))}
          </ul>
          <details>
            <summary>
              Inspect redacted context and permitted source spans
            </summary>
            <pre className="egress-preview">
              {JSON.stringify(preview, null, 2)}
            </pre>
          </details>
          <p className="small muted">
            A source, permission or policy change invalidates this
            authorization. No response is sent to a customer.
          </p>
          <button
            disabled={busy}
            onClick={() =>
              task(async () => {
                const r = await api<{ id: string }>(
                  `/api/cases/${selected.id}/runs`,
                  "POST",
                  { binding: preview.binding },
                );
                setJob(await api<Job>(`/api/runs/${r.id}`));
                setJobs(
                  await api<JobSummary[]>(`/api/cases/${selected.id}/runs`),
                );
                setModal(null);
                setTab("decision");
              })
            }
          >
            Authorize bounded advisory run
          </button>
        </Modal>
      )}
      {modal === "review" && job?.packet && job.packet_hash && (
        <Modal
          title="Record independent human review"
          onClose={() => setModal(null)}
        >
          <ReviewForm
            job={job}
            handlerDraft={selected?.context.draft}
            busy={busy}
            submit={(value) =>
              task(async () => {
                await api(`/api/runs/${job.id}/reviews`, "POST", value);
                setJob(await api<Job>(`/api/runs/${job.id}`));
                setModal(null);
                setNotice(
                  "Human review recorded against the exact packet revision. Automated ballots remain unchanged.",
                );
              })
            }
          />
        </Modal>
      )}
      {evidence && tab === "sources" && (
        <Modal title={evidence.source.name} onClose={() => setEvidence(null)}>
          <Evidence source={evidence.source} />
        </Modal>
      )}
    </div>
  );
}

function Evidence({
  source,
  citation,
}: {
  source: Source;
  citation?: Citation;
}) {
  const parts = highlight(
    source.text || "",
    citation?.start || 0,
    citation?.end || 0,
  );
  const mark = useRef<HTMLElement>(null);
  useEffect(() => {
    if (citation) mark.current?.scrollIntoView({ block: "center" });
  }, [citation?.start, source.id]);
  return (
    <>
      <strong className="source-title">{source.name}</strong>
      <p className="small muted">{source.mapping}</p>
      <p className="source-text">
        {parts[0]}
        <mark ref={mark}>{parts[1]}</mark>
        {parts[2]}
      </p>
    </>
  );
}

function CaseForm({
  initial,
  busy,
  submit,
}: {
  initial?: Context;
  busy: boolean;
  submit: (value: Context) => void;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const lines = String(f.get("issues"))
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean);
        submit({
          title: String(f.get("title")),
          jurisdiction: "UK",
          product: "motor_insurance",
          facts: String(f.get("facts")),
          draft: String(f.get("draft")),
          missing: String(f.get("missing"))
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
          issues: lines.map((title, n) => ({
            id: initial?.issues[n]?.id || `issue_${n + 1}`,
            title,
          })),
        });
      }}
    >
      <label>
        Case title
        <input
          name="title"
          defaultValue={initial?.title}
          required
          minLength={3}
          maxLength={200}
        />
      </label>
      <label>
        Confirmed issues · one per line
        <textarea
          name="issues"
          defaultValue={initial?.issues.map((i) => i.title).join("\n")}
          placeholder="Outstanding premium deduction&#10;Customer communication"
          required
          maxLength={2000}
        />
      </label>
      <label>
        Attributed case facts
        <textarea
          name="facts"
          defaultValue={initial?.facts}
          maxLength={10000}
        />
      </label>
      <label>
        Handler’s proposed response · not source truth
        <textarea
          name="draft"
          defaultValue={initial?.draft}
          maxLength={10000}
        />
      </label>
      <label>
        Known missing evidence · one item per line
        <textarea
          name="missing"
          defaultValue={initial?.missing.join("\n")}
          maxLength={6000}
        />
      </label>
      <p className="small muted">
        Editing creates a new revision and invalidates earlier current-review
        eligibility. No inference starts automatically.
      </p>
      <button disabled={busy}>Save case context</button>
    </form>
  );
}

function UploadSources({
  caseData,
  rights,
  busy,
  run,
  onDone,
}: {
  caseData: Case;
  rights: Clearance[];
  busy: boolean;
  run: (fn: () => Promise<void>) => Promise<void>;
  onDone: () => Promise<void>;
}) {
  return (
    <form
      className="upload-form"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        f.set("revision", String(caseData.revision));
        if (!f.get("replaces")) f.delete("replaces");
        run(async () => {
          await api(`/api/cases/${caseData.id}/sources`, "POST", f);
          await onDone();
        });
      }}
    >
      <label>
        Document
        <input name="file" type="file" accept=".pdf,.txt" required />
      </label>
      <div className="form-row">
        <label>
          Document kind
          <select name="kind">
            <option value="complaint">Complaint</option>
            <option value="policy">Policy wording</option>
            <option value="correspondence">Correspondence</option>
            <option value="other">Other evidence</option>
          </select>
        </label>
        <label>
          Source-rights clearance
          <select name="rights_id" required>
            <option value="">Choose approved authority</option>
            {rights
              .filter((r) => r.expires > Date.now() / 1000)
              .map((r) => (
                <option value={r.id} key={r.id}>
                  {r.basis} · {r.reference}
                </option>
              ))}
          </select>
        </label>
      </div>
      <label>
        Replace an active source, if applicable
        <select name="replaces">
          <option value="">Add a new source</option>
          {caseData.sources.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <p className="small muted">
        Text PDFs and UTF-8 .txt. No OCR or multimedia analysis. Raw documents
        are retained locally; the model receives selected redacted text only
        after authorization.
      </p>
      <button className="secondary" disabled={busy || !rights.length}>
        <Plus size={15} /> Add source revision
      </button>
    </form>
  );
}

function SettingsPanel({
  workspace: w,
  rights,
  run,
  busy,
  onRefresh,
}: {
  workspace: WorkspaceDetail;
  rights: Clearance[];
  run: (fn: () => Promise<void>) => Promise<void>;
  busy: boolean;
  onRefresh: () => Promise<void>;
}) {
  const [members, setMembers] = useState<{ name: string; role: string }[]>([]),
    [audit, setAudit] = useState<
      { seq: number; actor: string; action: string; occurred: number }[]
    >([]);
  useEffect(() => {
    api<typeof members>(`/api/workspaces/${w.id}/members`)
      .then(setMembers)
      .catch(() => {});
  }, [w.id]);
  return (
    <div className="settings-sections">
      <section>
        <h3>Approved review policy · v{w.policy_revision}</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              await api(`/api/workspaces/${w.id}/policy`, "PUT", {
                revision: w.policy_revision,
                policy: {
                  name: f.get("name"),
                  instructions: f.get("instructions"),
                  required_documents: f.getAll("documents"),
                  egress_enabled: f.has("egress"),
                },
              });
              await onRefresh();
            });
          }}
        >
          <label>
            Policy name
            <input
              name="name"
              defaultValue={w.policy.name}
              required
              minLength={3}
              maxLength={150}
            />
          </label>
          <label>
            Approved instructions · no invented legal rules
            <textarea
              name="instructions"
              defaultValue={w.policy.instructions}
              maxLength={6000}
            />
          </label>
          <fieldset>
            <legend>Required document kinds</legend>
            {["complaint", "policy", "correspondence", "other"].map((k) => (
              <label className="check" key={k}>
                <input
                  type="checkbox"
                  name="documents"
                  value={k}
                  defaultChecked={w.policy.required_documents.includes(k)}
                />
                {readable(k)}
              </label>
            ))}
          </fieldset>
          <label className="check">
            <input
              name="egress"
              type="checkbox"
              defaultChecked={w.policy.egress_enabled}
            />{" "}
            Permit explicitly authorized model-context egress
          </label>
          <p className="small muted">
            Activation invalidates prior runs. No policy supplies a blanket
            legal licence or makes a response automatically acceptable.
          </p>
          <button disabled={busy}>Activate policy revision</button>
        </form>
      </section>
      <section>
        <h3>Source rights & permitted processing</h3>
        <div className="warning">
          Publicly readable Ombudsman decisions are not automatically licensed
          for a stored benchmark. Record actual permission or another reviewed
          legal basis; do not select “owned test” for third-party case material.
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              await api(`/api/workspaces/${w.id}/rights`, "POST", {
                basis: f.get("basis"),
                reference: f.get("reference"),
                expires: new Date(String(f.get("expires"))).getTime() / 1000,
                egress: f.has("egress"),
              });
              await onRefresh();
            });
          }}
        >
          <label>
            Authority basis
            <select name="basis" required>
              <option value="">Select verified basis</option>
              <option value="authorized_customer">
                Authorized customer case files
              </option>
              <option value="licensed">Explicit licence / permission</option>
              <option value="reviewed_legal_basis">
                Qualified reviewed legal basis
              </option>
              <option value="owned_test">
                Personally authored engineering fixtures only
              </option>
            </select>
          </label>
          <label>
            Permission / review evidence reference
            <input name="reference" required minLength={10} maxLength={500} />
          </label>
          <label>
            Authority expires
            <input type="datetime-local" name="expires" required />
          </label>
          <label className="check">
            <input type="checkbox" name="egress" /> This authority covers
            model-context egress
          </label>
          <button className="secondary" disabled={busy}>
            Record owner attestation
          </button>
        </form>
        {rights.map((r) => (
          <div className="clearance" key={r.id}>
            <span>
              <strong>{readable(r.basis)}</strong>
              <small>
                {r.reference} ·{" "}
                {new Date(r.expires * 1000).toLocaleDateString()}
              </small>
            </span>
            {r.expires > Date.now() / 1000 && (
              <button
                className="secondary danger"
                onClick={() =>
                  run(async () => {
                    await api(
                      `/api/workspaces/${w.id}/rights/${r.id}`,
                      "DELETE",
                    );
                    await onRefresh();
                  })
                }
              >
                Revoke
              </button>
            )}
          </div>
        ))}
      </section>
      <section>
        <h3>People & independent review</h3>
        <p className="muted small">
          Create accounts and grant access before running cases. Membership
          changes conservatively invalidate existing current packets. The case
          maker cannot grant their own packet a reviewed label.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              await api("/api/users", "POST", {
                username: f.get("username"),
                password: f.get("password"),
              });
            });
          }}
        >
          <div className="form-row">
            <label>
              New account name
              <input
                name="username"
                required
                maxLength={100}
                autoComplete="off"
              />
            </label>
            <label>
              Initial password
              <input
                name="password"
                type="password"
                required
                minLength={12}
                autoComplete="new-password"
              />
            </label>
          </div>
          <button className="secondary" disabled={busy}>
            Create account
          </button>
        </form>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              await api(`/api/workspaces/${w.id}/members`, "PUT", {
                username: f.get("username"),
                role: f.get("role") || null,
              });
              setMembers(
                await api<typeof members>(`/api/workspaces/${w.id}/members`),
              );
              await onRefresh();
            });
          }}
        >
          <div className="form-row">
            <label>
              Existing account
              <input name="username" required />
            </label>
            <label>
              Workspace role
              <select name="role">
                <option value="analyst">Analyst</option>
                <option value="reviewer">Reviewer</option>
                <option value="viewer">Viewer</option>
                <option value="owner">Owner</option>
                <option value="">Revoke workspace access</option>
              </select>
            </label>
          </div>
          <button className="secondary" disabled={busy}>
            Apply membership
          </button>
        </form>
        {members.map((m) => (
          <div className="member" key={m.name}>
            <strong>{m.name}</strong>
            <span>{m.role}</span>
          </div>
        ))}
      </section>
      <section>
        <h3>Workspace audit</h3>
        <button
          className="secondary"
          onClick={() =>
            run(async () =>
              setAudit(
                await api<typeof audit>(`/api/workspaces/${w.id}/audit`),
              ),
            )
          }
        >
          Load first 200 audit events
        </button>
        {audit.map((a) => (
          <div className="audit" key={a.seq}>
            <small>
              #{a.seq} · {new Date(a.occurred * 1000).toLocaleString()}
            </small>
            <span>{readable(a.action)}</span>
            <small>{a.actor}</small>
          </div>
        ))}
      </section>
    </div>
  );
}

function ReviewForm({
  job,
  handlerDraft,
  busy,
  submit,
}: {
  job: Job;
  handlerDraft: string | undefined;
  busy: boolean;
  submit: (value: unknown) => void;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const resolutions = Object.fromEntries(
          (job.packet?.review_requirements || []).map((k) => [k, f.get(k)]),
        );
        submit({
          packet_hash: job.packet_hash,
          reason: f.get("reason"),
          response: f.get("response"),
          resolutions,
          overrides: Object.fromEntries(
            (job.packet?.consensus?.issues || [])
              .map((i) => [
                i.issue_id,
                String(f.get("override:" + i.issue_id) || ""),
              ])
              .filter(([, value]) => value.trim()),
          ),
        });
      }}
    >
      <p className="muted">
        This records your independent assessment of the exact packet, including
        dissent. It does not alter the automated votes or certify legal
        correctness.
      </p>
      {job.packet?.review_requirements.map((k) => (
        <label key={k}>
          {job.packet?.review_questions?.[k] || k}
          <textarea
            name={k}
            required
            minLength={10}
            maxLength={2000}
            placeholder="Explain your resolution, authority and supporting evidence."
          />
        </label>
      ))}
      <label>
        Review rationale
        <textarea name="reason" required minLength={10} maxLength={2000} />
      </label>
      {job.packet?.consensus?.issues.map((i) => (
        <label key={i.issue_id}>
          Optional attributed human override · {i.issue_id}
          <textarea
            name={"override:" + i.issue_id}
            maxLength={2000}
            placeholder="If you disagree, record your alternative resolution, evidence and reason. Automated votes will stay unchanged."
          />
        </label>
      ))}
      <label>
        Human-reviewed proposed response
        <textarea
          name="response"
          defaultValue={reviewResponseSeed(handlerDraft)}
          placeholder="Compose the response after checking the evidence. The AI review brief is not customer-ready copy."
          maxLength={10000}
        />
      </label>
      <p className="muted">
        This editor starts with the handler’s draft, not the AI voting summary.
        Nothing is sent to a customer by recording a review.
      </p>
      <label className="check">
        <input type="checkbox" required /> I independently checked evidence,
        unresolved conditions and the response before recording this review.
      </label>
      <button disabled={busy}>Record exact-revision review</button>
    </form>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
