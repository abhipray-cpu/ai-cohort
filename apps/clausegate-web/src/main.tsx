import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  Check,
  Clock3,
  Download,
  FileCheck2,
  FileText,
  History,
  Layers3,
  LogOut,
  PauseCircle,
  Plus,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Upload,
  Users,
  X,
} from "lucide-react";
import { acceptSnapshot, mayDecide, mayExport, statusText } from "./state";
import "./style.css";

type Span = { id: string; start: number; end: number; quote: string };
type Finding = {
  check_id: string;
  label: string;
  assessment: string;
  rationale: string;
  evidence_ids: string[];
  evidence: Span[];
  origin?: string;
};
type Approval = {
  id: string;
  revision: number;
  binding: string;
  kind: string;
  check_id: string;
  role: string;
  question: string;
  reason: string;
  allowed: string[];
  assignee: string | null;
  expires_at: string;
  due_at: string;
  state: string;
};
type Decision = {
  id: string;
  actor: string;
  kind: string;
  rationale: string;
  at: string;
  withdrawn: boolean;
};
type Rule = {
  id: string;
  hypothesis: string;
  action: string;
  roles?: string[];
};
type Case = {
  id: string;
  workspace_id: string;
  owner: string;
  name: string;
  revision: number;
  state: string;
  document_id: string | null;
  context: { side: string; purpose: string };
  playbook: {
    name: string;
    revision: number;
    active: boolean;
    rules: Rule[];
  } | null;
  findings: Finding[];
  requests: Approval[];
  decisions: Decision[];
  checkpoint: string | null;
  packet: { sha256: string; reviewer: string | null } | null;
  roles: string[];
  egress: boolean;
  epoch: string;
};
type Summary = Pick<
  Case,
  "id" | "name" | "workspace_id" | "state" | "revision"
>;
type Document = {
  id: string;
  name: string;
  text: string;
  text_hash: string;
  bytes_hash: string;
  complete: boolean;
  gaps: string[];
  spans: Span[];
  pages: { page: number; start: number; end: number }[];
};
type Event = {
  seq: number;
  kind: string;
  actor: string;
  at: string;
  detail: Record<string, unknown>;
};
type Audit = {
  items: Event[];
  verification: {
    valid: boolean;
    seq: number;
    assurance: string;
    anchored_seq: number;
  };
  epoch: string;
};
type Job = {
  id: string;
  kind: string;
  status: string;
  calls: number;
  cursor: number;
  reason: string;
};
type User = { username: string; csrf: string; admin: boolean };
let csrf = "";
async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRF-Token": csrf } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    let message = "Request failed";
    try {
      const v = await r.json();
      message =
        typeof v.detail === "string" ? v.detail : JSON.stringify(v.detail);
    } catch {}
    throw new Error(message);
  }
  return r.json();
}
const key = () => crypto.randomUUID();
const preset = {
  name: "EXAMPLE NDA policy · adopt only after qualified review",
  rules: [
    {
      id: "return",
      hypothesis:
        "The receiving party must return or destroy confidential information upon request.",
      action: "require_review",
      roles: ["reviewer"],
    },
    {
      id: "retention",
      hypothesis:
        "The receiving party may retain some confidential information after return or destruction.",
      action: "require_exception",
      roles: ["approver"],
    },
  ],
};
const label = (v: string) => v.replaceAll("_", " ");
const date = (v: string) => new Date(v).toLocaleString();

function App() {
  const [user, setUser] = useState<User | null>(null),
    [checking, setChecking] = useState(true),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [cases, setCases] = useState<Summary[]>([]),
    [workspaces, setWorkspaces] = useState<{ id: string; name: string }[]>([]),
    [cid, setCid] = useState(""),
    [c, setCase] = useState<Case | null>(null),
    [doc, setDoc] = useState<Document | null>(null),
    [audit, setAudit] = useState<Audit | null>(null),
    [jobs, setJobs] = useState<Job[]>([]);
  const [tab, setTab] = useState("review"),
    [opened, setOpened] = useState<Approval | null>(null),
    [choice, setChoice] = useState(""),
    [rationale, setRationale] = useState(""),
    [side, setSide] = useState("recipient"),
    [purpose, setPurpose] = useState(""),
    [answerLabel, setAnswerLabel] = useState("Entailment"),
    [evidence, setEvidence] = useState<string[]>([]),
    [focusSpan, setFocusSpan] = useState(""),
    [sourceFilter, setSourceFilter] = useState(""),
    [policy, setPolicy] = useState(JSON.stringify(preset, null, 2)),
    [text, setText] = useState(""),
    [manual, setManual] = useState(""),
    [ack, setAck] = useState(false),
    [finalReason, setFinalReason] = useState(""),
    [auditOffset, setAuditOffset] = useState(0);
  const active = useRef("");
  const latest = useRef<Case | null>(null);
  active.current = cid;
  useEffect(() => {
    api<User>("/v1/me")
      .then((v) => {
        csrf = v.csrf;
        setUser(v);
      })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);
  async function lists() {
    const [rows, ws] = await Promise.all([
      api<Summary[]>("/v1/cases"),
      api<{ id: string; name: string }[]>("/v1/workspaces"),
    ]);
    setCases(rows);
    setWorkspaces(ws);
  }
  async function refresh(id = cid, offset = auditOffset) {
    if (!id) return;
    const [next, events, task] = await Promise.all([
      api<Case>(`/v1/cases/${id}`),
      api<Audit>(`/v1/cases/${id}/audit?offset=${offset}`),
      api<Job[]>(`/v1/cases/${id}/jobs`),
    ]);
    if (active.current !== id) return;
    if (!acceptSnapshot(latest.current, next)) return;
    latest.current = next;
    setCase(next);
    setDoc((previous) => (previous?.id === next.document_id ? previous : null));
    setAudit(events);
    setJobs(task);
    if (next.document_id) {
      const source = await api<Document>(`/v1/documents/${next.document_id}`);
      if (active.current === id && latest.current?.document_id === source.id)
        setDoc(source);
    } else setDoc(null);
  }
  useEffect(() => {
    if (!user) return;
    lists().catch((e) => setError(e.message));
    const timer = setInterval(() => {
      lists().catch(() => {});
      if (active.current)
        refresh(active.current).catch((e) => setError(e.message));
    }, 2000);
    return () => clearInterval(timer);
  }, [user?.username, cid, auditOffset]);
  useEffect(() => {
    setCase(null);
    setDoc(null);
    setOpened(null);
    setAuditOffset(0);
    setRationale("");
    setNotice("");
    if (cid) refresh(cid, 0).catch((e) => setError(e.message));
  }, [cid]);
  async function act(
    task: () => Promise<unknown>,
    message = "Saved. Context and authority were checked.",
  ) {
    setBusy(true);
    setError("");
    try {
      await task();
      setNotice(message);
      await lists();
      if (active.current) await refresh(active.current);
    } catch (e) {
      setError((e as Error).message);
      if (active.current) refresh(active.current).catch(() => {});
    } finally {
      setBusy(false);
    }
  }
  function open(r: Approval) {
    setOpened(r);
    setChoice("");
    setRationale("");
    setPurpose(c?.context.purpose ?? "");
    setSide(
      c?.context.side === "unknown"
        ? "recipient"
        : (c?.context.side ?? "recipient"),
    );
    const f = c?.findings.find((f) => f.check_id === r.check_id);
    setEvidence(f?.evidence_ids ?? []);
    setAnswerLabel(f?.label ?? "Entailment");
    setFocusSpan(f?.evidence_ids[0] ?? "");
    setTab("review");
  }
  useEffect(() => {
    if (focusSpan)
      document
        .getElementById("span-" + focusSpan)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusSpan, tab]);
  async function createCase(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    await act(async () => {
      let wid = String(f.get("workspace"));
      if (!wid)
        wid = (
          await api<{ id: string }>("/v1/workspaces", "POST", {
            name: String(f.get("new_workspace") || "My review workspace"),
          })
        ).id;
      const next = await api<Case>(`/v1/workspaces/${wid}/cases`, "POST", {
        name: String(f.get("name")),
      });
      setCid(next.id);
      setTab("setup");
    }, "Case created. Add the document, context, playbook and reviewer grants.");
  }
  async function upload(file: File) {
    if (!c) return;
    if (file.size > 20 * 1024 ** 2) {
      setError("Maximum upload is 20 MiB.");
      return;
    }
    await act(async () => {
      if (file.name.toLowerCase().endsWith(".pdf")) {
        const r = await fetch(
          `/v1/cases/${c.id}/documents?expected_revision=${c.revision}&name=${encodeURIComponent(file.name)}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/pdf",
              "X-CSRF-Token": csrf,
            },
            body: file,
          },
        );
        if (!r.ok) throw new Error((await r.json()).detail);
      } else
        await api(`/v1/cases/${c.id}/imports`, "POST", {
          expected_revision: c.revision,
          name: file.name,
          text: await file.text(),
        });
    }, "Source revision imported. Prior approvals are no longer reusable.");
  }
  async function submitDecision(e: React.FormEvent) {
    e.preventDefault();
    if (!opened || !c) return;
    const body: Record<string, unknown> = {
      expected_revision: opened.revision,
      binding: opened.binding,
      kind: choice,
      rationale,
      key: key(),
    };
    if (choice === "clarify") {
      body.side = side;
      body.purpose = purpose;
    }
    if (
      choice === "correct_interpretation" ||
      choice === "confirm_interpretation"
    ) {
      body.label = answerLabel;
      body.evidence_ids = evidence;
    }
    await act(
      () => api(`/v1/approval-requests/${opened.id}/decisions`, "POST", body),
      "Human response recorded. Changed interpretations are reevaluated; exceptions are not implied.",
    );
  }
  async function download(format: string) {
    if (!c) return;
    await act(async () => {
      const r = await fetch(`/v1/cases/${c.id}/export?format=${format}`);
      if (!r.ok) throw new Error((await r.json()).detail);
      const blob = await r.blob(),
        url = URL.createObjectURL(blob),
        a = document.createElement("a");
      a.href = url;
      a.download = `clausegate-review.${format === "markdown" ? "md" : "json"}`;
      a.click();
      URL.revokeObjectURL(url);
    }, "Downloaded the current internally reviewed packet.");
  }
  const current = opened
    ? c?.requests.find((r) => r.id === opened.id)
    : undefined;
  const canSubmit =
    !!c &&
    c.state === "waiting_human" &&
    mayDecide(opened, current, c.checkpoint) &&
    !!opened &&
    c.roles.includes(opened.role) &&
    (opened.kind === "clarification" || user?.username !== c.owner) &&
    (!opened.assignee || opened.assignee === user?.username);
  const pending = c?.requests.filter((r) => r.state === "pending") ?? [];
  const selectedFinding = c?.findings.find(
    (f) => f.check_id === opened?.check_id,
  );
  const owner = !!c?.roles.includes("owner"),
    requester = !!c?.roles.includes("requester");

  if (checking)
    return <div className="boot">Connecting to your review workspace…</div>;
  if (!user)
    return (
      <div className="login-page">
        <div className="login-story">
          <div className="wordmark">
            <ShieldCheck /> ClauseGate
          </div>
          <span className="eyebrow">DECISIONS, WITH CONTEXT</span>
          <h1>
            Move the agreement.
            <br />
            Keep the judgment.
          </h1>
          <p>
            A focused workspace for the NDA exceptions that need a person—not
            another summary.
          </p>
          <div className="login-principles">
            <span>
              <FileText /> Original evidence
            </span>
            <span>
              <PauseCircle /> Deliberate checkpoints
            </span>
            <span>
              <History /> Traceable decisions
            </span>
          </div>
          <small>
            Internal review assistance. Never autonomous legal approval.
          </small>
        </div>
        <form
          className="login-card"
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            act(async () => {
              const u = await api<User>("/v1/auth/session", "POST", {
                username: f.get("username"),
                password: f.get("password"),
              });
              csrf = u.csrf;
              setUser(u);
            }, "Signed in.");
          }}
        >
          <span className="eyebrow">YOUR REVIEW DESK</span>
          <h2>Welcome back.</h2>
          <p>
            Sign in with your assigned identity. Reviewer authority is checked
            for every decision.
          </p>
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
              required
            />
          </label>
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
          <button className="primary" disabled={busy}>
            Open workspace <ArrowRight size={16} />
          </button>
          <small>
            Use your configured service credentials. No default password.
          </small>
        </form>
      </div>
    );
  return (
    <div className="app">
      <aside className="rail">
        <div className="wordmark">
          <ShieldCheck /> ClauseGate
        </div>
        <span className="rail-label">REVIEW WORKSPACE</span>
        <button
          className="rail-action"
          onClick={() => {
            setCid("");
            setTab("new");
          }}
        >
          <Plus size={16} /> New review
        </button>
        <div className="case-list">
          {cases.map((row) => (
            <button
              className={"case-link " + (cid === row.id ? "selected" : "")}
              key={row.id}
              onClick={() => setCid(row.id)}
            >
              <FileText size={16} />
              <span>
                {row.name}
                <small>{statusText(row.state)}</small>
              </span>
              {row.state === "waiting_human" && <i />}
            </button>
          ))}
        </div>
        <div className="rail-footer">
          <span>
            <span className="avatar">
              {user.username.slice(0, 2).toUpperCase()}
            </span>
            {user.username}
          </span>
          <button
            title="Sign out"
            aria-label="Sign out"
            onClick={() =>
              act(async () => {
                await api("/v1/auth/session", "DELETE");
                csrf = "";
                setUser(null);
                setCid("");
              }, "Signed out.")
            }
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <span className="eyebrow">HUMAN-IN-THE-LOOP APPROVAL</span>
            <h1>{c?.name ?? "Your decision desk"}</h1>
          </div>
          <div className="header-meta">
            <span className="connection" /> Private service workspace{" "}
            <button
              aria-label="Refresh current state"
              onClick={() => act(() => refresh())}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>
        {error && (
          <div role="alert" className="error banner">
            <strong>Action could not complete.</strong> {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}
        {notice && (
          <div role="status" className="notice banner">
            {notice}
            <button aria-label="Dismiss notice" onClick={() => setNotice("")}>
              <X size={16} />
            </button>
          </div>
        )}
        {!cid ? (
          <div className="welcome">
            <div className="welcome-copy">
              <span className="eyebrow">
                LESS BACK-AND-FORTH. CLEARER OWNERSHIP.
              </span>
              <h2>
                The right question.
                <br />
                The right person.
                <br />
                <em>The exact version.</em>
              </h2>
              <p>
                Start a review, inspect the original agreement, and resolve
                exceptions without separating an approval from its context.
              </p>
              <div className="welcome-badges">
                <span>
                  <Layers3 /> Version-bound
                </span>
                <span>
                  <Users /> Independent reviewers
                </span>
              </div>
            </div>
            <form className="card create-form" onSubmit={createCase}>
              <h3>Start an NDA review</h3>
              <label>
                Review name
                <input
                  name="name"
                  placeholder="Acme partnership · mutual NDA"
                  required
                  maxLength={160}
                />
              </label>
              <label>
                Workspace
                <select name="workspace">
                  <option value="">Create a new workspace</option>
                  {workspaces.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                New workspace name
                <input
                  name="new_workspace"
                  placeholder="Commercial operations"
                />
              </label>
              <button className="primary" disabled={busy}>
                Create review <ArrowRight size={16} />
              </button>
              <small>
                Use public or explicitly authorized contracts. No signing or
                external sending.
              </small>
            </form>
          </div>
        ) : !c ? (
          <div className="empty">Loading the current authorized revision…</div>
        ) : (
          <>
            <section className="status-bar">
              <div className={"status-icon " + c.state}>
                <PauseCircle size={22} />
              </div>
              <div>
                <strong>{statusText(c.state)}</strong>
                <small>
                  {pending.length} open request{pending.length === 1 ? "" : "s"}{" "}
                  · revision {c.revision} · {c.findings.length}/
                  {c.playbook?.rules.length ?? 0} checks assessed
                </small>
              </div>
              <div className="status-right">
                <span className="pill">
                  {c.egress ? "Model context allowed" : "Model egress denied"}
                </span>
                <span className="pill">
                  {doc?.complete
                    ? "Source text complete"
                    : doc
                      ? "Source has gaps"
                      : "No source yet"}
                </span>
              </div>
            </section>
            <nav className="tabs" aria-label="Review sections">
              {[
                ["review", "Review & decisions", FileCheck2],
                ["setup", "Intake & playbook", Settings2],
                ["audit", "Decision history", History],
                ["access", "People & controls", Users],
              ].map(([id, name, Icon]) => {
                const I = Icon as typeof FileText;
                return (
                  <button
                    key={id as string}
                    className={tab === id ? "active" : ""}
                    onClick={() => setTab(id as string)}
                  >
                    <I size={16} />
                    {name as string}
                    {id === "review" && pending.length > 0 && (
                      <b>{pending.length}</b>
                    )}
                  </button>
                );
              })}
            </nav>
            {tab === "review" && (
              <>
                <div className="review-grid">
                  <section className="document card">
                    <div className="panel-header">
                      <div>
                        <span className="eyebrow">ORIGINAL SOURCE</span>
                        <h3>{doc?.name ?? "Add an agreement to begin"}</h3>
                      </div>
                      <FileText size={19} />
                    </div>
                    {doc ? (
                      <>
                        <div className="source-meta">
                          {doc.pages.length
                            ? `${doc.pages.length} extracted pages`
                            : "Original text"}{" "}
                          · {doc.text.length.toLocaleString()} characters · SHA{" "}
                          {doc.text_hash.slice(0, 12)}
                          <a href={`/v1/documents/${doc.id}/file`}>
                            Download original
                          </a>
                        </div>
                        {doc.gaps.length > 0 && (
                          <div className="warning">{doc.gaps.join(" · ")}</div>
                        )}
                        <input
                          className="source-search"
                          aria-label="Find source text"
                          placeholder="Find a term in the source…"
                          value={sourceFilter}
                          onChange={(e) => setSourceFilter(e.target.value)}
                        />
                        <div
                          className="source-reader"
                          tabIndex={0}
                          aria-label="Original agreement text"
                        >
                          {doc.spans
                            .filter(
                              (s) =>
                                !sourceFilter ||
                                s.quote
                                  .toLowerCase()
                                  .includes(sourceFilter.toLowerCase()),
                            )
                            .map((s) => (
                              <div
                                id={"span-" + s.id}
                                key={s.id}
                                className={
                                  "source-span " +
                                  (focusSpan === s.id || evidence.includes(s.id)
                                    ? "highlighted"
                                    : "")
                                }
                              >
                                <span className="span-id">{s.id}</span>
                                <pre>{s.quote}</pre>
                                {opened?.kind === "interpretation" && (
                                  <button
                                    className="evidence-toggle"
                                    onClick={() =>
                                      setEvidence((old) =>
                                        old.includes(s.id)
                                          ? old.filter((i) => i !== s.id)
                                          : [...old, s.id],
                                      )
                                    }
                                  >
                                    {evidence.includes(s.id)
                                      ? "Remove evidence"
                                      : "+ Evidence"}
                                  </button>
                                )}
                              </div>
                            ))}
                        </div>
                      </>
                    ) : (
                      <div className="empty">
                        <Upload size={34} />
                        <p>No agreement imported.</p>
                        <button onClick={() => setTab("setup")}>
                          Open intake
                        </button>
                      </div>
                    )}
                  </section>
                  <aside className="decision-column">
                    <section className="card inbox">
                      <div className="panel-header">
                        <h3>Needs a person</h3>
                        <span className="count">{pending.length}</span>
                      </div>
                      {pending.length === 0 ? (
                        <p className="muted">
                          {c.state === "partial"
                            ? "Analysis is incomplete. Retry within allowance or record an explicit manual review."
                            : "No open decisions at this revision."}
                        </p>
                      ) : (
                        pending.map((r) => (
                          <button
                            key={r.id}
                            className={
                              "request " + (opened?.id === r.id ? "chosen" : "")
                            }
                            onClick={() => open(r)}
                          >
                            <span className={"request-type " + r.kind}>
                              {label(r.kind)}
                            </span>
                            <strong>
                              {r.check_id === "business_context"
                                ? "Business context"
                                : (c.playbook?.rules.find(
                                    (x) => x.id === r.check_id,
                                  )?.hypothesis ?? r.check_id)}
                            </strong>
                            <small>
                              <Users size={12} /> {r.assignee ?? r.role}{" "}
                              <span>
                                ·{" "}
                                {Date.parse(r.due_at) < Date.now()
                                  ? "Overdue"
                                  : "Awaiting input"}
                              </span>
                            </small>
                          </button>
                        ))
                      )}
                    </section>
                    {opened && (
                      <section className="card decision-form">
                        <span className="eyebrow">YOUR DECISION</span>
                        <h3>{opened.question}</h3>
                        <p className="reason">
                          Why paused: {label(opened.reason)}. Required
                          capability: {opened.role}.
                        </p>
                        <small>
                          Expires {date(opened.expires_at)} · request revision{" "}
                          {opened.revision}
                        </small>
                        {!canSubmit && (
                          <div role="status" className="warning">
                            This form is stale, expired, resolved or not
                            assigned to your authority. Open a current request
                            before submitting. Your unsent rationale is retained
                            here.
                          </div>
                        )}
                        {selectedFinding && (
                          <div className="finding-summary">
                            <span>
                              {selectedFinding.label} ·{" "}
                              {selectedFinding.assessment}
                            </span>
                            <p>{selectedFinding.rationale}</p>
                            <div className="chip-row">
                              {selectedFinding.evidence.map((s) => (
                                <button
                                  key={s.id}
                                  onClick={() => setFocusSpan(s.id)}
                                >
                                  {s.id} [{s.start}–{s.end}) ↗
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                        <form onSubmit={submitDecision}>
                          <label>
                            Response
                            <select
                              required
                              value={choice}
                              onChange={(e) => setChoice(e.target.value)}
                            >
                              <option value="">
                                Select an explicit response
                              </option>
                              {opened.allowed.map((k) => (
                                <option key={k} value={k}>
                                  {label(k)}
                                </option>
                              ))}
                            </select>
                          </label>
                          {choice === "clarify" && (
                            <>
                              <label>
                                Company side
                                <select
                                  value={side}
                                  onChange={(e) => setSide(e.target.value)}
                                >
                                  <option value="recipient">Recipient</option>
                                  <option value="discloser">Discloser</option>
                                  <option value="mutual">Mutual</option>
                                </select>
                              </label>
                              <label>
                                Disclosure purpose
                                <input
                                  value={purpose}
                                  onChange={(e) => setPurpose(e.target.value)}
                                  required
                                  maxLength={1500}
                                />
                              </label>
                            </>
                          )}
                          {[
                            "confirm_interpretation",
                            "correct_interpretation",
                          ].includes(choice) && (
                            <>
                              <label>
                                Reviewed interpretation
                                <select
                                  value={answerLabel}
                                  onChange={(e) =>
                                    setAnswerLabel(e.target.value)
                                  }
                                >
                                  {[
                                    "Entailment",
                                    "Contradiction",
                                    "NotMentioned",
                                  ].map((v) => (
                                    <option key={v}>{v}</option>
                                  ))}
                                </select>
                              </label>
                              <p className="muted">
                                Select original spans with “+ Evidence” in the
                                reader. Include exceptions and qualifiers.
                              </p>
                              <div className="chip-row">
                                {evidence.map((id) => (
                                  <button
                                    type="button"
                                    key={id}
                                    onClick={() => setFocusSpan(id)}
                                  >
                                    {id}
                                  </button>
                                ))}
                              </div>
                            </>
                          )}
                          {choice === "approve_exception" && (
                            <div className="warning">
                              This accepts only the stated policy deviation for
                              the bound document. It does not approve other
                              terms or sign the agreement.
                            </div>
                          )}
                          <label>
                            Rationale
                            <textarea
                              value={rationale}
                              onChange={(e) => setRationale(e.target.value)}
                              required
                              minLength={3}
                              maxLength={1800}
                              rows={4}
                              placeholder="What did you verify, decide or need changed?"
                            />
                          </label>
                          <button
                            className="primary"
                            disabled={busy || !canSubmit || !choice}
                          >
                            Record human response <Check size={16} />
                          </button>
                        </form>
                      </section>
                    )}
                    <section className="card review-packet">
                      <span className="eyebrow">INTERNAL HANDOFF</span>
                      <h3>Final review, not a signature.</h3>
                      <p className="muted">
                        All blockers must be resolved against current context
                        before an independent final reviewer can approve the
                        packet.
                      </p>
                      {c.packet && (
                        <small>
                          Packet {c.packet.sha256.slice(0, 16)} ·{" "}
                          {c.packet.reviewer
                            ? `reviewed by ${c.packet.reviewer}`
                            : "unreviewed"}
                        </small>
                      )}
                      {c.state === "review_ready" && (
                        <form
                          onSubmit={(e) => {
                            e.preventDefault();
                            act(
                              () =>
                                api(`/v1/cases/${c.id}/reviews`, "POST", {
                                  expected_revision: c.revision,
                                  packet_hash: c.packet!.sha256,
                                  rationale: finalReason,
                                  acknowledge_limits: ack,
                                }),
                              "Exact internal packet reviewed.",
                            );
                          }}
                        >
                          <label>
                            Review rationale
                            <textarea
                              required
                              minLength={3}
                              maxLength={1800}
                              value={finalReason}
                              onChange={(e) => setFinalReason(e.target.value)}
                            />
                          </label>
                          <label className="check">
                            <input
                              type="checkbox"
                              checked={ack}
                              onChange={(e) => setAck(e.target.checked)}
                              required
                            />
                            I reviewed all findings, evidence, decisions and
                            disclosed limitations.
                          </label>
                          <button
                            className="primary"
                            disabled={
                              busy ||
                              !c.roles.includes("final_reviewer") ||
                              user.username === c.owner ||
                              !ack
                            }
                          >
                            Finalize internal packet
                          </button>
                        </form>
                      )}
                      <div className="button-row">
                        <button
                          disabled={
                            !mayExport(c.state, !!c.packet?.reviewer) || busy
                          }
                          onClick={() => download("markdown")}
                        >
                          <Download size={15} /> Markdown
                        </button>
                        <button
                          disabled={
                            !mayExport(c.state, !!c.packet?.reviewer) || busy
                          }
                          onClick={() => download("json")}
                        >
                          JSON
                        </button>
                        {["waiting_human", "resume_queued"].includes(
                          c.state,
                        ) && (
                          <button
                            disabled={busy}
                            onClick={() =>
                              act(() =>
                                api(`/v1/cases/${c.id}/resume`, "POST", {}),
                              )
                            }
                          >
                            Revalidate & continue
                          </button>
                        )}
                      </div>
                    </section>
                  </aside>
                </div>
                {c.findings.length > 0 && (
                  <section className="card findings-table">
                    <div className="panel-header">
                      <h3>All assessed checks</h3>
                      <span className="muted">
                        Interpretation ≠ organizational acceptance
                      </span>
                    </div>
                    {c.findings.map((f) => (
                      <div className="finding-row" key={f.check_id}>
                        <div>
                          <strong>
                            {c.playbook?.rules.find((r) => r.id === f.check_id)
                              ?.hypothesis ?? f.check_id}
                          </strong>
                          <small>{f.rationale}</small>
                        </div>
                        <span className="pill">{f.label}</span>
                        <span className="pill">{f.assessment}</span>
                        <div className="chip-row">
                          {f.evidence.map((s) => (
                            <button
                              key={s.id}
                              onClick={() => {
                                setFocusSpan(s.id);
                                window.scrollTo({
                                  top: 180,
                                  behavior: "smooth",
                                });
                              }}
                            >
                              {s.id} ↗
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </section>
                )}
              </>
            )}
            {tab === "setup" && (
              <div className="setup-grid">
                <section className="card">
                  <span className="eyebrow">01 / SOURCE</span>
                  <h3>The actual agreement</h3>
                  <p className="muted">
                    PDF or text; 20 MiB, 150 pages, 500,000 extracted characters
                    maximum. Scans without readable text require manual
                    handling.
                  </p>
                  <label className="upload">
                    <Upload />
                    <span>Choose PDF or text file</span>
                    <input
                      type="file"
                      accept=".pdf,.txt"
                      disabled={!requester || busy}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) upload(f);
                        e.target.value = "";
                      }}
                    />
                  </label>
                  <details>
                    <summary>Import plain text</summary>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        act(() =>
                          api(`/v1/cases/${c.id}/imports`, "POST", {
                            expected_revision: c.revision,
                            name: "agreement.txt",
                            text,
                          }),
                        );
                      }}
                    >
                      <label>
                        Original agreement text
                        <textarea
                          value={text}
                          onChange={(e) => setText(e.target.value)}
                          required
                          rows={8}
                          maxLength={500000}
                        />
                      </label>
                      <button disabled={!requester || busy || !text.trim()}>
                        Import new revision
                      </button>
                    </form>
                  </details>
                  <p className="muted">
                    A new revision invalidates prior approvals even when the
                    filename is unchanged.
                  </p>
                </section>
                <section className="card">
                  <span className="eyebrow">02 / BUSINESS CONTEXT</span>
                  <h3>Facts, not assumptions</h3>
                  <p className="muted">
                    Current: {c.context.side} ·{" "}
                    {c.context.purpose || "purpose unknown"}
                  </p>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = new FormData(e.currentTarget);
                      act(() =>
                        api(`/v1/cases/${c.id}/context`, "PUT", {
                          expected_revision: c.revision,
                          side: f.get("side"),
                          purpose: f.get("purpose"),
                        }),
                      );
                    }}
                  >
                    <label>
                      Our side
                      <select name="side" defaultValue={c.context.side}>
                        <option value="unknown">
                          Unknown—ask the requester
                        </option>
                        <option value="recipient">Recipient</option>
                        <option value="discloser">Discloser</option>
                        <option value="mutual">Mutual</option>
                      </select>
                    </label>
                    <label>
                      Disclosure purpose
                      <input
                        name="purpose"
                        defaultValue={c.context.purpose}
                        maxLength={1500}
                      />
                    </label>
                    <button disabled={!requester || busy}>
                      Save revised context
                    </button>
                  </form>
                </section>
                <section className="card wide">
                  <span className="eyebrow">03 / ORGANIZATION PLAYBOOK</span>
                  <h3>Explicit positions and authority</h3>
                  <div className="warning">
                    The example is a labelled development fixture, not legal
                    best practice. A qualified policy owner must adopt real
                    positions. Every final packet still needs a person.
                  </div>
                  <p className="muted">
                    Active: {c.playbook?.name ?? "none"}{" "}
                    {c.playbook &&
                      `· revision ${c.playbook.revision} · ${c.playbook.active ? "active" : "draft"}`}
                  </p>
                  <button
                    onClick={() =>
                      c.playbook &&
                      setPolicy(
                        JSON.stringify(
                          { name: c.playbook.name, rules: c.playbook.rules },
                          null,
                          2,
                        ),
                      )
                    }
                  >
                    Load current playbook into editor
                  </button>
                  <label>
                    Strict playbook JSON
                    <textarea
                      className="code"
                      rows={13}
                      value={policy}
                      onChange={(e) => setPolicy(e.target.value)}
                      spellCheck={false}
                    />
                  </label>
                  <div className="button-row">
                    <button
                      disabled={!owner || busy}
                      onClick={() =>
                        act(() =>
                          api(`/v1/cases/${c.id}/playbook/draft`, "PUT", {
                            expected_revision: c.revision,
                            playbook: JSON.parse(policy),
                          }),
                        )
                      }
                    >
                      Save draft
                    </button>
                    <button
                      className="primary"
                      disabled={!owner || busy}
                      onClick={() =>
                        act(
                          () =>
                            api(`/v1/cases/${c.id}/playbook`, "PUT", {
                              expected_revision: c.revision,
                              playbook: JSON.parse(policy),
                            }),
                          "Playbook explicitly activated. Earlier decisions are stale.",
                        )
                      }
                    >
                      Activate revised playbook
                    </button>
                  </div>
                </section>
                <section className="card">
                  <span className="eyebrow">04 / ANALYSIS</span>
                  <h3>Propose, then validate</h3>
                  <p className="muted">
                    Installed Codex may use remote inference. Egress is denied
                    until the owner explicitly permits document context. No
                    action tools are authorized.
                  </p>
                  <button
                    disabled={!owner || busy}
                    onClick={() =>
                      act(() =>
                        api(`/v1/cases/${c.id}/egress`, "PUT", {
                          expected_revision: c.revision,
                          allowed: !c.egress,
                        }),
                      )
                    }
                  >
                    {c.egress
                      ? "Revoke model egress"
                      : "Allow model-context egress"}
                  </button>
                  <button
                    className="primary"
                    disabled={
                      !requester ||
                      busy ||
                      !c.document_id ||
                      !c.playbook?.active
                    }
                    onClick={() =>
                      act(
                        () =>
                          api(`/v1/cases/${c.id}/analyses`, "POST", {
                            expected_revision: c.revision,
                            key: key(),
                          }),
                        "Analysis queued with a bounded grant. Waiting for a person does not consume model runtime.",
                      )
                    }
                  >
                    <ArrowRight size={16} /> Start bounded analysis
                  </button>
                  <div className="job-list">
                    {jobs.map((j) => (
                      <div key={j.id}>
                        <strong>
                          {j.kind} · {j.status}
                        </strong>
                        <small>
                          {j.calls}/4 calls reserved · {j.cursor} chunks saved
                          <br />
                          {j.reason}
                        </small>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="card">
                  <span className="eyebrow">MANUAL FALLBACK</span>
                  <h3>Explicit human findings</h3>
                  <p className="muted">
                    If generation is unavailable, a reviewer may submit all
                    configured checks with original span IDs. This is attributed
                    human review, not AI success.
                  </p>
                  <button
                    onClick={() =>
                      setManual(
                        JSON.stringify(
                          (c.findings.length
                            ? c.findings
                            : (c.playbook?.rules.map((r) => ({
                                check_id: r.id,
                                label: "NotMentioned",
                                assessment: "uncertain",
                                rationale: "Human review needed",
                                evidence_ids: [],
                              })) ?? [])
                          ).map((f) => ({
                            check_id: f.check_id,
                            label: f.label,
                            assessment: f.assessment,
                            rationale: f.rationale,
                            evidence_ids: f.evidence_ids,
                          })),
                          null,
                          2,
                        ),
                      )
                    }
                  >
                    Prepare review form
                  </button>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = new FormData(e.currentTarget);
                      act(() =>
                        api(`/v1/cases/${c.id}/findings`, "POST", {
                          expected_revision: c.revision,
                          findings: JSON.parse(manual),
                          rationale: f.get("reason"),
                        }),
                      );
                    }}
                  >
                    <label>
                      Reviewed findings JSON
                      <textarea
                        className="code"
                        rows={8}
                        value={manual}
                        onChange={(e) => setManual(e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      Full review rationale
                      <input name="reason" required maxLength={1800} />
                    </label>
                    <button disabled={!c.roles.includes("reviewer") || busy}>
                      Record all supplied human findings
                    </button>
                  </form>
                </section>
              </div>
            )}
            {tab === "audit" && (
              <div className="history-grid">
                <section className="card">
                  <div className="panel-header">
                    <div>
                      <span className="eyebrow">AUDIT LINEAGE</span>
                      <h3>From source to decision</h3>
                    </div>
                    <History />
                  </div>
                  <p className="muted">
                    {audit?.verification.assurance} · head #
                    {audit?.verification.seq} · epoch{" "}
                    {audit?.epoch.slice(0, 10)}. A local hash chain alone does
                    not prevent privileged rewriting.
                  </p>
                  {owner && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        act(
                          () =>
                            api(`/v1/cases/${c.id}/audit/anchor`, "POST", {}),
                          "Audit head retained in the independent authority store.",
                        )
                      }
                    >
                      Retain external audit checkpoint
                    </button>
                  )}
                  <ol className="timeline">
                    {audit?.items.map((e) => (
                      <li key={e.seq}>
                        <span className="timeline-dot" />
                        <div>
                          <strong>{label(e.kind)}</strong>
                          <small>
                            #{e.seq} · {e.actor} · {date(e.at)}
                          </small>
                          <details>
                            <summary>Event details</summary>
                            <pre>{JSON.stringify(e.detail, null, 2)}</pre>
                          </details>
                        </div>
                      </li>
                    ))}
                  </ol>
                  <div className="button-row">
                    <button
                      disabled={auditOffset === 0}
                      onClick={() =>
                        setAuditOffset(Math.max(0, auditOffset - 100))
                      }
                    >
                      Previous
                    </button>
                    <span>
                      Events {auditOffset + 1}–
                      {auditOffset + (audit?.items.length ?? 0)}
                    </span>
                    <button
                      disabled={(audit?.items.length ?? 0) < 100}
                      onClick={() => setAuditOffset(auditOffset + 100)}
                    >
                      Next
                    </button>
                  </div>
                </section>
                <section className="card">
                  <h3>Human decisions</h3>
                  {c.decisions.length === 0 && (
                    <p className="muted">No decisions recorded.</p>
                  )}
                  {c.decisions.map((d) => (
                    <div className="decision-record" key={d.id}>
                      <span className="pill">
                        {label(d.kind)}
                        {d.withdrawn ? " · withdrawn" : ""}
                      </span>
                      <strong>{d.actor}</strong>
                      <p>{d.rationale}</p>
                      <small>{date(d.at)}</small>
                      {!d.withdrawn && (d.actor === user.username || owner) && (
                        <button
                          disabled={busy}
                          onClick={() =>
                            act(
                              () =>
                                api(
                                  `/v1/cases/${c.id}/decisions/${d.id}/withdraw`,
                                  "POST",
                                  { expected_revision: c.revision },
                                ),
                              "Decision withdrawn. Dependent readiness has been invalidated.",
                            )
                          }
                        >
                          Withdraw decision
                        </button>
                      )}
                    </div>
                  ))}
                </section>
              </div>
            )}
            {tab === "access" && (
              <div className="setup-grid">
                <section className="card">
                  <span className="eyebrow">PEOPLE & AUTHORITY</span>
                  <h3>Grant a real reviewer</h3>
                  <p className="muted">
                    A user account has no case access until granted. Updating
                    authority conservatively stales workspace case approvals.
                    Requesters cannot approve their own exceptions.
                  </p>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = new FormData(e.currentTarget);
                      act(() =>
                        api(`/v1/workspaces/${c.workspace_id}/members`, "PUT", {
                          username: f.get("username"),
                          roles: f.getAll("roles"),
                          case_ids: [c.id],
                          expires_at: f.get("expires")
                            ? new Date(String(f.get("expires"))).toISOString()
                            : null,
                        }),
                      );
                    }}
                  >
                    <label>
                      Existing username
                      <input name="username" required />
                    </label>
                    <div className="role-grid">
                      {[
                        "requester",
                        "reviewer",
                        "approver",
                        "final_reviewer",
                        "auditor",
                      ].map((role) => (
                        <label className="check" key={role}>
                          <input type="checkbox" name="roles" value={role} />
                          {label(role)}
                        </label>
                      ))}
                    </div>
                    <label>
                      Grant expiry (optional)
                      <input type="datetime-local" name="expires" />
                    </label>
                    <button disabled={!owner || busy}>
                      Apply case-scoped grant
                    </button>
                  </form>
                </section>
                <section className="card">
                  <span className="eyebrow">EXPLICIT ASSIGNMENT</span>
                  <h3>Own the next decision</h3>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = new FormData(e.currentTarget);
                      const r = pending.find((x) => x.id === f.get("request"));
                      if (!r) return;
                      act(() =>
                        api(`/v1/approval-requests/${r.id}/assignment`, "PUT", {
                          expected_revision: r.revision,
                          username: f.get("username"),
                          expires_at: f.get("expires")
                            ? new Date(String(f.get("expires"))).toISOString()
                            : null,
                        }),
                      );
                    }}
                  >
                    <label>
                      Pending request
                      <select name="request" required>
                        <option value="">Choose request</option>
                        {pending.map((r) => (
                          <option value={r.id} key={r.id}>
                            {r.check_id} · {r.role}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Authorized assignee
                      <input name="username" required />
                    </label>
                    <label>
                      Assignment expiry
                      <input type="datetime-local" name="expires" />
                    </label>
                    <button disabled={!owner || busy}>
                      Assign / delegate within existing role
                    </button>
                  </form>
                  <p className="muted">
                    Assignment never grants a new capability. The assignee must
                    already hold the required case role.
                  </p>
                </section>
                {user.admin && (
                  <section className="card">
                    <h3>Provision a separate identity</h3>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        const f = new FormData(e.currentTarget);
                        act(
                          () =>
                            api("/v1/users", "POST", {
                              username: f.get("username"),
                              password: f.get("password"),
                              admin: false,
                            }),
                          "User created without case access. Grant the case role separately.",
                        );
                      }}
                    >
                      <label>
                        Username
                        <input
                          name="username"
                          required
                          pattern="[A-Za-z0-9_.-]+"
                          maxLength={80}
                        />
                      </label>
                      <label>
                        Unique password
                        <input
                          name="password"
                          type="password"
                          required
                          minLength={12}
                          maxLength={256}
                          autoComplete="new-password"
                        />
                      </label>
                      <button disabled={busy}>Create user</button>
                    </form>
                  </section>
                )}
                <section className="card danger">
                  <h3>Stop or erase this review</h3>
                  <button
                    disabled={!requester || busy}
                    onClick={() =>
                      act(() =>
                        api(`/v1/cases/${c.id}/cancel`, "POST", {
                          expected_revision: c.revision,
                        }),
                      )
                    }
                  >
                    Cancel active workflow
                  </button>
                  <p className="muted">
                    Erasure removes case sources and derived content from the
                    live store. Downloaded packets and backup media require
                    separate disposal. Non-content receipts remain.
                  </p>
                  <button
                    disabled={!owner || busy}
                    onClick={() =>
                      act(async () => {
                        const p = await api<{
                          documents: number;
                          decisions: number;
                          revision: number;
                        }>(`/v1/cases/${c.id}/erasures/preview`);
                        if (
                          window.prompt(
                            `Erase ${p.documents} documents and ${p.decisions} decisions? Type ERASE. Downloaded copies cannot be recalled.`,
                          ) !== "ERASE"
                        )
                          return;
                        await api(`/v1/cases/${c.id}/erasures`, "POST", {
                          expected_revision: p.revision,
                          confirmation: "ERASE",
                        });
                      }, "Case content erased. Separate backup-media disposal may still be required.")
                    }
                  >
                    Preview and confirm erasure
                  </button>
                </section>
              </div>
            )}
          </>
        )}
        <footer>
          <ShieldCheck size={14} /> Human judgment stays human. Internal
          approval ≠ legal certification or signature.
          <span>ClauseGate · Day 06</span>
        </footer>
      </main>
      {busy && (
        <div className="working" role="status">
          <Clock3 size={15} /> Checking and saving…
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
