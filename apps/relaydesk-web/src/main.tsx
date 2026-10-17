import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  Download,
  Fingerprint,
  History,
  Layers3,
  LoaderCircle,
  LogOut,
  MessageSquare,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { canExport, terminal } from "./state";
import "./style.css";

type Account = { id: string; name: string };
type Case = {
  id: string;
  name: string;
  account_id: string;
  revision: number;
  owner: string;
  roles: string[];
  policy: { model_egress?: boolean; github_repositories?: string[] };
  conversations: { id: string }[];
  jobs: Job[];
  members: { username: string; roles: string[] }[];
};
type Evidence = {
  source_id: string;
  quote: string;
  start: number;
  end: number;
  sha256: string;
};
type Hit = {
  id: string;
  body: string;
  kind: string;
  state: string;
  author: string;
  scores: { semantic: number; lexical: number; rank: number };
  evidence: Evidence;
};
type Output = {
  id: string;
  state: string;
  reviewer: string | null;
  case_revision: number;
  payload: {
    summary: string;
    status: string;
    ai_succeeded?: boolean;
    claims?: { text: string; memory_ids: string[]; attribution?:{author:string,state:string,source_type:string}; citations?:Evidence[] }[];
    answer_state?:string;
    questions?: string[];
    limitations?: string[];
    coverage_gaps?: string[];
    recall?: {
      hits: Hit[];
      mode: string;
      coverage: { eligible: number; indexed: number; selected: number };
    };
    compression?: {
      coverage: { total: number; selected: number; omitted: number };
    };
    context_manifest?: {
      as_of?: string;
      model?: string;
      case_revision?: number;
    };
  };
};
type Job = {
  id: string;
  status: string;
  reason?: string;
  output_id?: string;
  output?: Output;
};
type Turn = { id: string; role: string; body: string; output?: Output };
type Memory = {
  id: string;
  body: string;
  kind: string;
  state: string;
  revision: number;
  source_id: string;
  source_hash: string;
  author: string;
  available_at: string;
  promoted: number;
};
type Source = {
  id: string;
  body: string;
  author: string;
  created_at: string;
  updated_at: string;
  sha256: string;
  source_key: string;
  erased: number;
};
type Ready = {
  eligible: number;
  indexed: number;
  pending: number;
  semantic_ready: boolean;
  model?: string;
};
type Event = {
  seq: number;
  kind: string;
  at: string;
  detail: Record<string, unknown>;
};
const newKey = () => crypto.randomUUID();
const date = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
const label = (value: string) => value.replaceAll("_", " ");

function App() {
  const [identity, setIdentity] = useState<{
    username: string;
    csrf: string;
    admin?: number;
  } | null>(null);
  const csrf = useRef("");
  const [boot, setBoot] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [accounts, setAccounts] = useState<Account[]>([]),
    [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState(""),
    [scope, setScope] = useState<Case | null>(null);
  const [tab, setTab] = useState<"chat" | "memory" | "activity">("chat");
  const [memories, setMemories] = useState<Memory[]>([]),
    [memoryTotal, setMemoryTotal] = useState(0),
    [offset, setOffset] = useState(0);
  const [ready, setReady] = useState<Ready | null>(null),
    [events, setEvents] = useState<Event[]>([]);
  const [conv, setConv] = useState(""),
    [session, setSession] = useState(""),
    [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState(""),
    [job, setJob] = useState<Job | null>(null),
    [output, setOutput] = useState<Output | null>(null);
  const [query, setQuery] = useState(""),
    [kind, setKind] = useState("all");
  const [modal, setModal] = useState<
    "account" | "case" | "import" | "policy" | "edit" | "source" | "user" | null
  >(null);
  const [source, setSource] = useState<Source | null>(null),
    [editing, setEditing] = useState<Memory | null>(null);
  const [history, setHistory] = useState(false),
    [asOf, setAsOf] = useState("");
  const [jsonImport, setJsonImport] = useState(""),
    [importMode, setImportMode] = useState<"github" | "json">("github");
  const active = useRef("");
  const serial = useRef(0);
  const epoch = useRef("");

  async function api<T>(
    path: string,
    method = "GET",
    body?: unknown,
    key?: string,
  ): Promise<T> {
    const response = await fetch("/v1" + path, {
      method,
      credentials: "same-origin",
      headers: {
        ...(method !== "GET"
          ? { "Content-Type": "application/json", "X-CSRF-Token": csrf.current }
          : {}),
        ...(key ? { "Idempotency-Key": key } : {}),
      },
      body:
        body === undefined
          ? method === "POST"
            ? "{}"
            : undefined
          : JSON.stringify(body),
    });
    if (!response.ok) {
      const value = await response
        .json()
        .catch(() => ({ detail: "Request unavailable" }));
      if (response.status === 401) {
        setIdentity(null);
        csrf.current = "";
        setTurns([]);
        setMemories([]);
        setOutput(null);
        setScope(null);
        setCases([]);
        setAccounts([]);
        setSelected("");
        active.current = "";
      }
      throw new Error(
        typeof value.detail === "string"
          ? value.detail
          : JSON.stringify(value.detail),
      );
    }
    return response.json();
  }
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }
  async function list() {
    const [a, c] = await Promise.all([
      api<Account[]>("/accounts"),
      api<Case[]>("/cases"),
    ]);
    setAccounts(a);
    setCases(c);
  }
  async function refresh(cid: string, page = offset) {
    const ticket = ++serial.current;
    const [c, m, r, a] = await Promise.all([
      api<Case>("/cases/" + cid),
      api<{ items: Memory[]; total: number }>(
        `/cases/${cid}/memories?offset=${page}&limit=100&history=${history}`,
      ),
      api<Ready>(`/cases/${cid}/readiness`),
      api<{ events: Event[]; epoch: string }>(`/cases/${cid}/changes`),
    ]);
    if (active.current !== cid || ticket !== serial.current) return;
    setScope(c);
    setMemories(m.items);
    setMemoryTotal(m.total);
    setReady(r);
    setEvents(a.events);
    if (epoch.current && epoch.current !== a.epoch) {
      setOutput(null);
      setTurns([]);
      setSource(null);
      setEditing(null);
      setModal(null);
      setConv("");
      setSession("");
      setJob(null);
      setNotice("Restore epoch changed. Cached context has been discarded.");
    }
    epoch.current = a.epoch;
    // An output remains visible as a stale draft, but cannot be exported after revision changes.
    if (output && output.case_revision !== c.revision)
      setOutput({ ...output, state: "stale" });
  }
  useEffect(() => {
    api<{ username: string; csrf: string; admin?: number }>("/me")
      .then((value) => {
        csrf.current = value.csrf;
        setIdentity(value);
        return list();
      })
      .catch(() => {})
      .finally(() => setBoot(false));
  }, []);
  useEffect(() => {
    active.current = selected;
    setScope(null);
    setTurns([]);
    setConv("");
    setSession("");
    setJob(null);
    setOutput(null);
    setOffset(0);
    setMemories([]);
    setReady(null);
    setEvents([]);
    setSource(null);
    setEditing(null);
    setModal(null);
    epoch.current = "";
    if (selected) void action(() => refresh(selected, 0));
  }, [selected]);
  useEffect(() => {
    if (selected) void action(() => refresh(selected, offset));
  }, [offset, history]);
  useEffect(() => {
    if (!selected || !identity) return;
    const cid = selected;
    const timer = setInterval(async () => {
      try {
        await refresh(cid);
        if (job && !terminal(job.status)) {
          const value = await api<Job>("/jobs/" + job.id);
          if (active.current !== cid) return;
          setJob(value);
          if (value.output) setOutput(value.output);
        }
        if (conv) {
          const values = await api<Turn[]>(
            "/conversations/" + conv + "/messages",
          );
          if (active.current === cid) setTurns(values);
        }
        if (output) {
          const value = await api<Output>("/handovers/" + output.id);
          if (active.current === cid) setOutput(value);
        }
      } catch (e) {
        if (active.current === cid) {
          setError(e instanceof Error ? e.message : "Sync failed");
          setMemories([]);
          setTurns([]);
          setOutput(null);
          setScope(null);
          setJob(null);
          setSource(null);
          setEditing(null);
          setModal(null);
        }
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [
    selected,
    identity,
    conv,
    job?.id,
    job?.status,
    offset,
    history,
    output?.id,
    output?.state,
  ]);

  async function login(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    await action(async () => {
      const value = await api<{
        username: string;
        csrf: string;
        admin: number;
      }>("/auth/session", "POST", Object.fromEntries(values));
      csrf.current = value.csrf;
      setIdentity(value);
      await list();
    });
  }
  async function startSession() {
    let conversation = conv;
    if (!conversation) {
      const value = await api<{ id: string; session: { id: string } }>(
        `/cases/${selected}/conversations`,
        "POST",
      );
      setConv(value.id);
      setSession(value.session.id);
      return { conversation: value.id, sessionId: value.session.id };
    }
    const value = await api<{ id: string }>(
      `/conversations/${conversation}/sessions`,
      "POST",
    );
    setSession(value.id);
    setNotice(
      "Fresh short-term buffer. Durable case memories remain available.",
    );
    return { conversation, sessionId: value.id };
  }
  async function send(event?: React.FormEvent) {
    event?.preventDefault();
    if (!question.trim() || !scope) return;
    const text = question.trim();
    const cid = selected;
    await action(async () => {
      let value: Job;
      if (asOf) {
        value = await api<Job>(
          `/cases/${cid}/recall`,
          "POST",
          {
            question: text,
            as_of: new Date(asOf).toISOString(),
            history,
            minimum_revision: scope.revision,
            limit: 12,
          },
          newKey(),
        );
      } else {
        const ids =
          session && conv
            ? { conversation: conv, sessionId: session }
            : await startSession();
        value = await api<Job>(
          `/conversations/${ids.conversation}/messages`,
          "POST",
          { content: text, session_id: ids.sessionId },
          newKey(),
        );
      }
      if (active.current !== cid) return;
      setJob(value);
      setQuestion("");
      setOutput(null);
      setNotice(
        "Question durably queued. You can leave and resume this investigation.",
      );
      await refresh(cid);
    });
  }
  async function takeover() {
    if (!scope) return;
    await action(async () => {
      const value = await api<Job>(
        `/cases/${selected}/takeover`,
        "POST",
        {
          question:
            "Prepare an incoming engineer handover: environment, reported failures, attempted actions, reported outcomes, commitments and unresolved questions. Clearly separate proposals from performed actions.",
          minimum_revision: scope.revision,
          limit: 12,
        },
        newKey(),
      );
      setJob(value);
      setOutput(null);
      setNotice(
        "Takeover draft queued. It will retain missing evidence and uncertainty.",
      );
    });
  }
  async function evidence(sid: string) {
    await action(async () => {
      setSource(await api<Source>("/sources/" + sid));
      setModal("source");
    });
  }
  async function exportOutput(format: string) {
    if (!output) return;
    await action(async () => {
      const response = await fetch(
        `/v1/handovers/${output.id}/exports?format=${format}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf.current,
          },
          body: "{}",
        },
      );
      if (!response.ok) throw new Error((await response.json()).detail);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `relaydesk-${output.id}.${format === "json" ? "json" : "md"}`;
      link.click();
      URL.revokeObjectURL(url);
    });
  }

  if (boot)
    return (
      <div className="loading">
        <LoaderCircle className="spin" /> Opening RelayDesk…
      </div>
    );
  if (!identity)
    return (
      <div className="login">
        <section>
          <div className="brand">
            <Layers3 /> RelayDesk
          </div>
          <span className="eyebrow">INVESTIGATION CONTINUITY</span>
          <h1>
            Pick up the case.
            <br />
            Not the pieces.
          </h1>
          <p>
            Source-linked memory for technical support teams. Carry the
            investigation forward, without turning assumptions into facts.
          </p>
          <div className="login-proof">
            <Fingerprint /> Durable memory. Explicit permissions. Human review.
          </div>
        </section>
        <form onSubmit={login}>
          <span className="eyebrow">YOUR WORKSPACE</span>
          <h2>Welcome back</h2>
          <p>Sign in with your individual service account.</p>
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
            Open workspace <ArrowUpRight size={16} />
          </button>
          <small>
            The administrator provisions accounts. No external model API key is
            required by this app.
          </small>
        </form>
      </div>
    );

  const visible = memories.filter(
    (m) =>
      (kind === "all" || m.kind === kind) &&
      `${m.body} ${m.author}`.toLowerCase().includes(query.toLowerCase()),
  );
  const running = job && !terminal(job.status);
  const isReviewer = scope?.roles?.includes("reviewer");
  const owner = scope?.owner === identity.username;
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="RelayDesk home">
          <Layers3 /> RelayDesk<span>05</span>
        </a>
        <div className="workspace-name">
          <div className="avatar">R</div>
          <div>
            Investigation workspace<small>Internal · read-only upstream</small>
          </div>
        </div>
        <div className="nav-label">
          YOUR CASES{" "}
          <button
            className="icon"
            aria-label="Create case"
            onClick={() => setModal("case")}
          >
            <Plus size={16} />
          </button>
        </div>
        <nav>
          {cases.map((c) => (
            <button
              key={c.id}
              className={selected === c.id ? "selected" : ""}
              onClick={() => {
                setSelected(c.id);
                setTab("chat");
              }}
            >
              <MessageSquare size={16} />
              <span>{c.name}</span>
              <ChevronRight size={14} />
            </button>
          ))}
          {!cases.length && (
            <p className="empty-note">
              No cases yet. Create an account, then an investigation.
            </p>
          )}
        </nav>
        <button
          className="quiet sidebar-action"
          onClick={() => setModal("account")}
        >
          <Plus size={15} /> New customer account
        </button>
        <div className="sidebar-bottom">
          <div className="boundary">
            <ShieldCheck size={17} />
            <span>
              Bounded by design<small>Suggestions are not executed.</small>
            </span>
          </div>
          <div className="signed">
            <div className="avatar">{identity.username[0].toUpperCase()}</div>
            <span>
              {identity.username}
              <small>{identity.admin ? "Administrator" : "Team member"}</small>
            </span>
            <button
              className="icon"
              title="Sign out"
              onClick={() =>
                void action(async () => {
                  await api("/auth/session", "DELETE");
                  setIdentity(null);
                  csrf.current = "";
                  setSelected("");
                })
              }
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <span className="eyebrow">
              CUSTOMER OPERATIONS / INVESTIGATIONS
            </span>
            <span className="top-status">
              <span className="dot" />{" "}
              {ready?.semantic_ready
                ? "Semantic memory ready"
                : selected
                  ? "Memory indexing / degraded"
                  : "Workspace ready"}
            </span>
          </div>
          {identity.admin && (
            <button className="quiet" onClick={() => setModal("user")}>
              Provision user
            </button>
          )}
        </header>
        <div className="content">
          {error && (
            <div className="error" role="alert">
              {error}
              <button
                className="icon"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
              <button
                className="icon"
                onClick={() => setNotice("")}
                aria-label="Dismiss notice"
              >
                <X size={16} />
              </button>
            </div>
          )}
          {!selected ? (
            <section className="welcome">
              <span className="eyebrow">EVERY HANDOVER, WITH CONTEXT</span>
              <h1>
                The next engineer
                <br />
                starts ahead.
              </h1>
              <p>
                Bring in a real issue thread. Preserve its investigation
                history. Ask what matters, even in a new session.
              </p>
              <button
                className="primary"
                onClick={() => setModal(accounts.length ? "case" : "account")}
              >
                <Plus size={17} /> Start an investigation
              </button>
              <div className="feature-grid">
                {[
                  [
                    BookOpen,
                    "Remember the evidence",
                    "Source-backed episodes and reviewed corrections.",
                  ],
                  [
                    History,
                    "Continue across sessions",
                    "Fresh conversation buffers, durable case memory.",
                  ],
                  [
                    ShieldCheck,
                    "Keep uncertainty visible",
                    "No automated fixes. Review before exporting.",
                  ],
                ].map(([Icon, title, description]) => {
                  const I = Icon as typeof BookOpen;
                  return (
                    <article key={String(title)}>
                      <I />
                      <h3>{String(title)}</h3>
                      <p>{String(description)}</p>
                    </article>
                  );
                })}
              </div>
            </section>
          ) : (
            <>
              <section className="case-heading">
                <div>
                  <div className="breadcrumbs">
                    {accounts.find((a) => a.id === scope?.account_id)?.name ||
                      "Customer account"}{" "}
                    <ChevronRight size={13} /> Investigation
                  </div>
                  <h1>{scope?.name || "Loading case…"}</h1>
                  <p>
                    Keep what was tried, what was reported, and what remains
                    unresolved.
                  </p>
                </div>
                <div className="heading-actions">
                  <button
                    className="secondary"
                    onClick={() => setModal("import")}
                    disabled={!scope?.roles?.includes("investigator")}
                  >
                    <Plus size={16} /> Add evidence
                  </button>
                  <button
                    className="primary"
                    onClick={() => void takeover()}
                    disabled={
                      busy ||
                      !!running ||
                      !scope?.roles?.includes("investigator")
                    }
                  >
                    <Sparkles size={16} /> Prepare handover
                  </button>
                  {owner && (
                    <button
                      className="icon bordered"
                      aria-label="Case permissions"
                      onClick={() => setModal("policy")}
                    >
                      <Settings2 size={18} />
                    </button>
                  )}
                </div>
              </section>
              {scope?.conversations?.length ? (
                <label>
                  Resume a saved conversation
                  <select
                    value={conv}
                    disabled={!!running}
                    onChange={(e) => {
                      const id = e.target.value;
                      if (!id) {
                        setConv("");
                        setSession("");
                        setTurns([]);
                        return;
                      }
                      void action(async () => {
                        const s = await api<{ id: string }>(
                          `/conversations/${id}/sessions`,
                          "POST",
                        );
                        const messages = await api<Turn[]>(
                          `/conversations/${id}/messages`,
                        );
                        setConv(id);
                        setSession(s.id);
                        setTurns(messages);
                        setNotice(
                          "Conversation resumed with a fresh interactive buffer and durable memory.",
                        );
                      });
                    }}
                  >
                    <option value="">New conversation</option>
                    {scope.conversations.map((c, i) => (
                      <option key={c.id} value={c.id}>
                        Saved conversation {scope.conversations.length - i} ·{" "}
                        {c.id.slice(0, 8)}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <div className="stats">
                <div>
                  <span>CASE MEMORIES</span>
                  <strong>{memoryTotal}</strong>
                  <small>Reported & proposed</small>
                </div>
                <div>
                  <span>VECTOR COVERAGE</span>
                  <strong>
                    {ready?.indexed ?? "—"}
                    <em> / {ready?.eligible ?? "—"}</em>
                  </strong>
                  <small>
                    {ready?.model
                      ? "CPU semantic encoder"
                      : "Encoder unavailable — lexical fallback"}
                  </small>
                </div>
                <div>
                  <span>CASE REVISION</span>
                  <strong>r{scope?.revision ?? "—"}</strong>
                  <small>Changes sync every 2 seconds</small>
                </div>
                <div>
                  <span>MODEL EGRESS</span>
                  <strong className="text-stat">
                    {scope?.policy.model_egress
                      ? "Explicitly allowed"
                      : "Denied by default"}
                  </strong>
                  <small>Installed Codex · no native tools</small>
                </div>
              </div>
              <div
                className="tabs"
                role="tablist"
                aria-label="Investigation views"
              >
                {(
                  [
                    ["chat", "Conversation", MessageSquare],
                    ["memory", "Memory ledger", BookOpen],
                    ["activity", "Activity", History],
                  ] as const
                ).map(([id, title, Icon]) => (
                  <button
                    role="tab"
                    aria-selected={tab === id}
                    key={id}
                    className={tab === id ? "active" : ""}
                    onClick={() => setTab(id)}
                  >
                    <Icon size={16} />
                    {title}
                  </button>
                ))}
                <span>Participant reports ≠ verified resolution</span>
              </div>
              {tab === "chat" && (
                <div className="investigation-grid">
                  <section className="chat-panel panel">
                    <div className="panel-title">
                      <div>
                        <span className="eyebrow">CASE CONVERSATION</span>
                        <h2>Carry the context forward</h2>
                      </div>
                      <button
                        className="quiet"
                        disabled={busy || !!running}
                        onClick={() =>
                          void action(async () => {
                            await startSession();
                          })
                        }
                      >
                        <Plus size={15} /> New session
                      </button>
                    </div>
                    <div className="chat-scroll">
                      {!turns.length && (
                        <div className="chat-empty">
                          <div className="spark">
                            <Sparkles />
                          </div>
                          <h3>What should the next engineer know?</h3>
                          <p>
                            Ask about reported outcomes, prior attempts, or the
                            next unresolved question. Evidence is retrieved from
                            this case’s durable memory.
                          </p>
                          <div className="suggestions">
                            {[
                              "What has already been tried, and what was the reported outcome?",
                              "What environment details and open questions should I confirm?",
                            ].map((q) => (
                              <button key={q} onClick={() => setQuestion(q)}>
                                {q}
                                <ArrowUpRight size={15} />
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      {turns.map((t) => (
                        <article key={t.id} className={"turn " + t.role}>
                          <div className="turn-label">
                            {t.role === "user" ? "Investigator" : "RelayDesk"}{" "}
                            {t.output && (
                              <span className="badge">
                                {label(t.output.state)}
                              </span>
                            )}
                          </div>
                          <p>{t.body}</p>
                          {t.output && (
                            <button
                              className="quiet"
                              onClick={() => setOutput(t.output!)}
                            >
                              Inspect evidence & draft{" "}
                              <ArrowUpRight size={14} />
                            </button>
                          )}
                        </article>
                      ))}
                      {running && (
                        <div className="processing" role="status">
                          <LoaderCircle size={17} className="spin" />{" "}
                          {label(job.status)} · retrieving case memory and
                          validating structured output{" "}
                          <button
                            className="quiet"
                            onClick={() =>
                              void action(async () => {
                                await api(`/jobs/${job.id}/cancel`, "POST");
                              })
                            }
                          >
                            Cancel
                          </button>
                        </div>
                      )}
                      {job && terminal(job.status) && !job.output && (
                        <div className="error">
                          Run {job.status}: {job.reason}. Original evidence is
                          retained.
                        </div>
                      )}
                    </div>
                    <form className="composer" onSubmit={send}>
                      <label className="sr-only" htmlFor="question">
                        Ask about this investigation
                      </label>
                      <textarea
                        id="question"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        maxLength={6000}
                        placeholder="Ask about this investigation…"
                        rows={3}
                        required
                      />
                      <div>
                        <span>Internal guidance · not a customer reply</span>
                        <button
                          className="primary"
                          disabled={busy || !!running || !question.trim()}
                          type="submit"
                        >
                          Ask RelayDesk <ArrowUpRight size={16} />
                        </button>
                      </div>
                      <details className="historical">
                        <summary>Historical recall options</summary>
                        <label>
                          Evidence available before
                          <input
                            type="datetime-local"
                            value={asOf}
                            onChange={(e) => setAsOf(e.target.value)}
                          />
                        </label>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={history}
                            onChange={(e) => setHistory(e.target.checked)}
                          />{" "}
                          Include superseded source history (never erased
                          content)
                        </label>
                        <small>
                          Historical mode excludes current-session turns and
                          future edits from model context.
                        </small>
                      </details>
                    </form>
                  </section>
                  <aside className="evidence-panel panel">
                    <div className="panel-title">
                      <div>
                        <span className="eyebrow">REVIEW BEFORE RELAY</span>
                        <h2>Handover & grounding</h2>
                      </div>
                      <Fingerprint size={21} />
                    </div>
                    {!output ? (
                      <div className="draft-empty">
                        <BookOpen size={29} />
                        <h3>A draft with receipts.</h3>
                        <p>
                          Ask a question or prepare a handover. The draft will
                          show recalled evidence, ranking signals, and coverage
                          gaps.
                        </p>
                        {scope?.jobs
                          ?.filter((j) => j.output_id)
                          .map((j) => (
                            <button
                              className="quiet saved-draft"
                              key={j.id}
                              onClick={() =>
                                void action(async () =>
                                  setOutput(
                                    await api<Output>(
                                      "/handovers/" + j.output_id,
                                    ),
                                  ),
                                )
                              }
                            >
                              Open saved {label(j.status)} draft{" "}
                              <ChevronRight size={14} />
                            </button>
                          ))}
                      </div>
                    ) : (
                      <div className="draft">
                        <div className="draft-status">
                          <span
                            className={
                              "badge " +
                              (output.state === "stale" ? "danger" : "")
                            }
                          >
                            {label(output.state)}
                          </span>
                          <small>
                            r{output.case_revision} ·{" "}
                            {output.payload.ai_succeeded
                              ? "AI-assisted"
                              : "Evidence fallback"}
                          </small>
                        </div>
                        <h3>{output.payload.summary}</h3>
                        {output.payload.claims?.map((c, i) => (
                          <div className="claim" key={i}>
                            <p>{c.text}</p>
                            <small>
                              {c.attribution ? `${c.attribution.author} · ${label(c.attribution.state)} · exact source quote` : `${c.memory_ids.length} memory references (legacy draft)`}
                            </small>
                            {c.citations?.map(citation=><button className="quiet" key={`${citation.source_id}:${citation.start}`} onClick={()=>void evidence(citation.source_id)}>Inspect supporting source · {citation.start}:{citation.end} <ArrowUpRight size={14}/></button>)}
                          </div>
                        ))}
                        {output.payload.questions?.length ? (
                          <>
                            <h4>Confirm next</h4>
                            <ul>
                              {output.payload.questions.map((q) => (
                                <li key={q}>{q}</li>
                              ))}
                            </ul>
                          </>
                        ) : null}
                        <h4>
                          Retrieved evidence{" "}
                          <span>
                            {output.payload.recall?.mode || "not available"}
                          </span>
                        </h4>
                        {output.payload.recall?.hits.map((h, i) => (
                          <details className="hit" key={h.id}>
                            <summary>
                              <span className="number">{i + 1}</span>
                              <div>
                                <span className="badge">
                                  {h.kind} · {h.state}
                                </span>
                                <p>
                                  {h.body.slice(0, 170)}
                                  {h.body.length > 170 ? "…" : ""}
                                </p>
                              </div>
                            </summary>
                            <p className="quote">{h.evidence.quote}</p>
                            <div className="scores">
                              Cosine {h.scores.semantic.toFixed(3)} · lexical{" "}
                              {h.scores.lexical.toFixed(3)} · rank{" "}
                              {h.scores.rank.toFixed(3)}
                            </div>
                            <small>
                              Ranking signals, not truth probabilities.{" "}
                              {h.author}
                            </small>
                            <button
                              className="quiet"
                              onClick={() =>
                                void evidence(h.evidence.source_id)
                              }
                            >
                              Inspect original source <ArrowUpRight size={14} />
                            </button>
                          </details>
                        ))}
                        <div className="limits">
                          <CircleHelp size={17} />
                          <div>
                            <strong>Limits stay attached</strong>
                            <ul>
                              {[
                                ...new Set([
                                  ...(output.payload.limitations || []),
                                  ...(output.payload.coverage_gaps || []),
                                ]),
                              ].map((g) => (
                                <li key={g}>{g}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                        {output.payload.compression && (
                          <small>
                            Compressed context:{" "}
                            {output.payload.compression.coverage.selected}/
                            {output.payload.compression.coverage.total} memories
                            retained;{" "}
                            {output.payload.compression.coverage.omitted}{" "}
                            omitted.
                          </small>
                        )}
                        <div className="review-actions">
                          {isReviewer && (
                            <button
                              className="secondary"
                              disabled={
                                busy ||
                                output.state === "stale" ||
                                output.state === "erased"
                              }
                              onClick={() =>
                                void action(async () =>
                                  setOutput(
                                    await api<Output>(
                                      `/handovers/${output.id}/reviews`,
                                      "POST",
                                      { acknowledge_limits: true },
                                    ),
                                  ),
                                )
                              }
                            >
                              <Check size={16} />
                              {output.reviewer
                                ? "Reviewed by " + output.reviewer
                                : "Review with stated limitations"}
                            </button>
                          )}
                          <button
                            className="quiet"
                            disabled={
                              !scope || !canExport(output, scope.revision)
                            }
                            onClick={() => void exportOutput("markdown")}
                          >
                            <Download size={15} /> Markdown
                          </button>
                          <button
                            className="quiet"
                            disabled={
                              !scope || !canExport(output, scope.revision)
                            }
                            onClick={() => void exportOutput("json")}
                          >
                            JSON
                          </button>
                        </div>
                      </div>
                    )}
                  </aside>
                </div>
              )}
              {tab === "memory" && (
                <section className="panel memory-panel">
                  <div className="panel-title">
                    <div>
                      <span className="eyebrow">DURABLE & SOURCE-LINKED</span>
                      <h2>
                        Memory ledger <small>{memoryTotal} total</small>
                      </h2>
                    </div>
                    <label className="search">
                      <Search size={16} />
                      <input
                        aria-label="Search this page of memories"
                        placeholder="Search this page…"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </label>
                  </div>
                  <div className="memory-controls">
                    <select
                      aria-label="Memory category"
                      value={kind}
                      onChange={(e) => setKind(e.target.value)}
                    >
                      {[
                        "all",
                        "episode",
                        "environment",
                        "attempt",
                        "outcome",
                        "workaround",
                        "hypothesis",
                        "decision",
                        "commitment",
                        "open_question",
                      ].map((k) => (
                        <option key={k}>{k}</option>
                      ))}
                    </select>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={history}
                        onChange={(e) => setHistory(e.target.checked)}
                      />{" "}
                      Show source history
                    </label>
                    <span>
                      Imported episodes are reported; model-extracted memories
                      remain proposals.
                    </span>
                  </div>
                  {visible.map((m) => (
                    <article className="memory-row" key={m.id}>
                      <div className="memory-kind">
                        <span className="badge">{label(m.kind)}</span>
                        <small>
                          {label(m.state)} · r{m.revision}
                        </small>
                      </div>
                      <div className="memory-body">
                        <p>{m.body}</p>
                        <small>
                          {m.author} · available {date(m.available_at)}{" "}
                          {m.promoted ? "· account-promoted" : ""}
                        </small>
                      </div>
                      <div className="memory-actions">
                        <button
                          className="quiet"
                          onClick={() => void evidence(m.source_id)}
                        >
                          Source <ArrowUpRight size={13} />
                        </button>
                        {isReviewer && (
                          <button
                            className="quiet"
                            onClick={() => {
                              setEditing(m);
                              setModal("edit");
                            }}
                          >
                            Review / correct
                          </button>
                        )}
                      </div>
                    </article>
                  ))}
                  {!visible.length && (
                    <div className="empty-note">
                      No memories in this view. Add source evidence or adjust
                      filters.
                    </div>
                  )}
                  <div className="pagination">
                    <button
                      className="secondary"
                      disabled={offset === 0}
                      onClick={() => setOffset(Math.max(0, offset - 100))}
                    >
                      Previous
                    </button>
                    <small>
                      {Math.min(offset + 1, memoryTotal)}–
                      {Math.min(offset + 100, memoryTotal)} of {memoryTotal}.
                      Search and category filters apply to this page.
                    </small>
                    <button
                      className="secondary"
                      disabled={offset + 100 >= memoryTotal}
                      onClick={() => setOffset(offset + 100)}
                    >
                      Next
                    </button>
                  </div>
                </section>
              )}
              {tab === "activity" && (
                <section className="panel activity">
                  <div className="panel-title">
                    <div>
                      <span className="eyebrow">AUDIT TRAIL</span>
                      <h2>Case events</h2>
                    </div>
                    <small>First 100 events · permission-scoped</small>
                  </div>
                  {events.map((e) => (
                    <article key={e.seq}>
                      <div className="event-dot" />
                      <div>
                        <strong>{label(e.kind)}</strong>
                        <small>
                          {date(e.at)} · event {e.seq}
                        </small>
                        <code>{JSON.stringify(e.detail)}</code>
                      </div>
                    </article>
                  ))}
                </section>
              )}
            </>
          )}
        </div>
        <footer>
          RelayDesk{" "}
          <span>Investigation continuity, not automated remediation.</span>
          <span>Local service · human accountability</span>
        </footer>
      </main>
      {modal && (
        <div
          className="overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setModal(null);
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <div className="modal-heading">
              <h2 id="modal-title">
                {
                  {
                    account: "New customer account",
                    case: "New investigation",
                    import: "Add real evidence",
                    policy: "Permissions & egress",
                    edit: "Review a memory",
                    source: "Original source record",
                    user: "Provision team member",
                  }[modal]
                }
              </h2>
              <button
                className="icon"
                aria-label="Close dialog"
                onClick={() => setModal(null)}
              >
                <X />
              </button>
            </div>
            <DialogFocus close={() => setModal(null)} />
            {(modal === "account" || modal === "case") && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = new FormData(e.currentTarget);
                  void action(async () => {
                    if (modal === "account")
                      await api("/accounts", "POST", { name: v.get("name") });
                    else {
                      const c = await api<Case>(
                        `/accounts/${v.get("account")}/cases`,
                        "POST",
                        { name: v.get("name") },
                      );
                      setSelected(c.id);
                    }
                    await list();
                    setModal(null);
                  });
                }}
              >
                {modal === "case" && (
                  <label>
                    Customer account
                    <select name="account" required>
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  Name
                  <input name="name" required maxLength={160} />
                </label>
                {modal === "case" && !accounts.length && (
                  <p>
                    Create an account first. Only its owner can create cases.
                  </p>
                )}
                <button
                  className="primary"
                  disabled={busy || (modal === "case" && !accounts.length)}
                >
                  Create {modal}
                </button>
              </form>
            )}
            {modal === "user" && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = new FormData(e.currentTarget);
                  void action(async () => {
                    await api("/users", "POST", {
                      username: v.get("username"),
                      password: v.get("password"),
                      admin: false,
                    });
                    setNotice(
                      "User provisioned. Grant case-specific investigator/reviewer roles separately.",
                    );
                    setModal(null);
                  });
                }}
              >
                <label>
                  Username
                  <input name="username" required maxLength={80} />
                </label>
                <label>
                  Unique password
                  <input
                    type="password"
                    name="password"
                    required
                    minLength={12}
                    autoComplete="new-password"
                  />
                </label>
                <p>
                  New users have no case access. Grant access explicitly below
                  case permissions.
                </p>
                <button className="primary" disabled={busy}>
                  Provision user
                </button>
              </form>
            )}
            {modal === "import" && (
              <>
                <div className="segmented">
                  <button
                    className={importMode === "github" ? "active" : ""}
                    onClick={() => setImportMode("github")}
                  >
                    Public GitHub issue
                  </button>
                  <button
                    className={importMode === "json" ? "active" : ""}
                    onClick={() => setImportMode("json")}
                  >
                    Captured message JSON
                  </button>
                </div>
                {importMode === "github" ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const v = new FormData(e.currentTarget);
                      void action(async () => {
                        const result = await api<{ inserted: number }>(
                          `/cases/${selected}/sources/github`,
                          "POST",
                          {
                            repository: v.get("repository"),
                            issue: Number(v.get("issue")),
                          },
                        );
                        setNotice(
                          `${result.inserted} source messages imported. Semantic indexing is asynchronous.`,
                        );
                        await refresh(selected);
                        setModal(null);
                      });
                    }}
                  >
                    <p>
                      Requires an explicit repository read grant in case
                      permissions. No upstream writes or linked-URL execution.
                    </p>
                    <label>
                      Repository
                      <input
                        name="repository"
                        placeholder="elastic/elasticsearch"
                        pattern="[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
                        required
                      />
                    </label>
                    <label>
                      Issue number
                      <input type="number" name="issue" min={1} required />
                    </label>
                    <button className="primary" disabled={busy}>
                      Fetch and import
                    </button>
                  </form>
                ) : (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void action(async () => {
                        const value = JSON.parse(jsonImport);
                        await api(`/cases/${selected}/imports`, "POST", value);
                        await refresh(selected);
                        setModal(null);
                        setNotice(
                          "Captured evidence imported. Original source keys make repeated imports idempotent.",
                        );
                      });
                    }}
                  >
                    <p>
                      JSON ImportBatch: messages with source_key, author, body,
                      created_at, updated_at; optional origin, complete and
                      gaps.
                    </p>
                    <label>
                      Choose capture
                      <input
                        type="file"
                        accept="application/json,.json"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) {
                            if (f.size > 20 * 1024 * 1024) {
                              setError("Maximum import size is 20 MiB");
                              return;
                            }
                            void f.text().then(setJsonImport);
                          }
                        }}
                      />
                    </label>
                    <label>
                      Message batch
                      <textarea
                        rows={9}
                        value={jsonImport}
                        onChange={(e) => setJsonImport(e.target.value)}
                        required
                        spellCheck={false}
                      />
                    </label>
                    <button className="primary" disabled={busy}>
                      Validate and import
                    </button>
                  </form>
                )}
              </>
            )}
            {modal === "policy" && scope && (
              <>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const v = new FormData(e.currentTarget);
                    void action(async () => {
                      await api(`/cases/${selected}/policy`, "PUT", {
                        expected_revision: scope.revision,
                        model_egress: v.get("egress") === "on",
                        github_repositories: String(v.get("repositories") || "")
                          .split(/[,\n]/)
                          .map((s) => s.trim())
                          .filter(Boolean),
                      });
                      await refresh(selected);
                      setNotice(
                        "Permission policy updated; previous drafts are stale.",
                      );
                      setModal(null);
                    });
                  }}
                >
                  <p>
                    Permission to run installed Codex is also permission for
                    selected source context to reach its configured provider. It
                    does not guarantee offline inference.
                  </p>
                  <label className="check">
                    <input
                      type="checkbox"
                      name="egress"
                      defaultChecked={scope.policy.model_egress}
                    />{" "}
                    Allow model context egress for this case
                  </label>
                  <label>
                    Allowed public repositories (one per line)
                    <textarea
                      name="repositories"
                      defaultValue={scope.policy.github_repositories?.join(
                        "\n",
                      )}
                      rows={3}
                    />
                  </label>
                  <button className="primary" disabled={busy}>
                    Save policy at r{scope.revision}
                  </button>
                </form>
                <hr />
                <h3>Case membership</h3>
                {scope.members.map((m) => (
                  <p key={m.username}>
                    {m.username}: {m.roles.join(", ") || "revoked"}
                  </p>
                ))}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const v = new FormData(e.currentTarget);
                    void action(async () => {
                      await api(`/cases/${selected}/members`, "PUT", {
                        username: v.get("username"),
                        roles: ["investigator", "reviewer"].filter(
                          (r) => v.get(r) === "on",
                        ),
                      });
                      await refresh(selected);
                    });
                  }}
                >
                  <label>
                    Existing username
                    <input name="username" required />
                  </label>
                  {["investigator", "reviewer"].map((r) => (
                    <label className="check" key={r}>
                      <input type="checkbox" name={r} />
                      {r}
                    </label>
                  ))}
                  <small>
                    Uncheck both to revoke. Owner access is retained.
                  </small>
                  <button className="secondary" disabled={busy}>
                    Update member
                  </button>
                </form>
              </>
            )}
            {modal === "edit" && editing && (
              <>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const v = new FormData(e.currentTarget);
                    void action(async () => {
                      await api(`/memories/${editing.id}/corrections`, "POST", {
                        expected_revision: editing.revision,
                        text: v.get("text"),
                        kind: v.get("kind"),
                        state: v.get("state"),
                        reason: v.get("reason"),
                      });
                      await refresh(selected);
                      setModal(null);
                    });
                  }}
                >
                  <p>
                    Creates an immutable new version. “Reported” is attribution,
                    not independent technical verification. Concurrent edits
                    require reloading.
                  </p>
                  <label>
                    Memory text
                    <textarea
                      name="text"
                      defaultValue={editing.body}
                      maxLength={4000}
                      rows={5}
                      required
                    />
                  </label>
                  <div className="form-row">
                    <label>
                      Category
                      <select name="kind" defaultValue={editing.kind}>
                        {[
                          "episode",
                          "environment",
                          "attempt",
                          "outcome",
                          "workaround",
                          "hypothesis",
                          "decision",
                          "commitment",
                          "open_question",
                        ].map((k) => (
                          <option key={k}>{k}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      State
                      <select name="state" defaultValue={editing.state}>
                        {[
                          "reported",
                          "proposed",
                          "disputed",
                          "superseded",
                          "suppressed",
                        ].map((s) => (
                          <option key={s}>{s}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <label>
                    Review rationale
                    <input name="reason" required maxLength={1000} />
                  </label>
                  <button className="primary" disabled={busy}>
                    Save correction at r{editing.revision}
                  </button>
                </form>
                {owner && (
                  <>
                    <hr />
                    <button
                      className="secondary"
                      disabled={busy || !!editing.promoted}
                      onClick={() =>
                        void action(async () => {
                          await api(
                            `/memories/${editing.id}/promotion`,
                            "POST",
                            { expected_revision: editing.revision },
                          );
                          await refresh(selected);
                          setModal(null);
                          setNotice(
                            "Promoted to account scope. Origin-case access is still required for recall.",
                          );
                        })
                      }
                    >
                      Promote to account memory
                    </button>
                    <details className="danger-zone">
                      <summary>
                        Erase this source and dependent memories
                      </summary>
                      <p>
                        Irreversibly redacts all versions of this source and
                        derived corrected memories, vectors and affected drafts.
                        Backups require the independent erasure ledger.
                      </p>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          const v = new FormData(e.currentTarget);
                          void action(async () => {
                            await api(`/cases/${selected}/erasures`, "POST", {
                              source_ids: [editing.source_id],
                              confirmation: v.get("confirmation"),
                            });
                            await refresh(selected);
                            setOutput(null);
                            setModal(null);
                            setNotice(
                              "Source and derived content redacted. Existing external exports cannot be recalled.",
                            );
                          });
                        }}
                      >
                        <label>
                          Type ERASE to confirm
                          <input name="confirmation" pattern="ERASE" required />
                        </label>
                        <button className="danger-button" disabled={busy}>
                          Erase source and derivatives
                        </button>
                      </form>
                    </details>
                  </>
                )}
              </>
            )}
            {modal === "source" && source && (
              <>
                <div className="source-meta">
                  <span className="badge">
                    {source.erased ? "erased" : "original record"}
                  </span>
                  <p>
                    {source.author} · created {date(source.created_at)}
                    <br />
                    Updated {date(source.updated_at)}
                  </p>
                  <code>{source.source_key}</code>
                </div>
                <pre className="source-body">{source.body}</pre>
                <small>SHA-256</small>
                <code className="hash">{source.sha256}</code>
                <p>
                  Source integrity does not establish that the reported
                  technical claim is true.
                </p>
              </>
            )}
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            {busy && (
              <div className="processing">
                <LoaderCircle className="spin" size={16} /> Validating request…
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function DialogFocus({ close }: { close: () => void }) {
  const marker = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = marker.current?.closest('[role="dialog"]');
    const selector =
      'button:not(:disabled), input, textarea, select, [tabindex="0"]';
    (dialog?.querySelector(selector) as HTMLElement)?.focus();
    function key(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      }
      if (e.key === "Tab") {
        const items = Array.from(
          dialog?.querySelectorAll<HTMLElement>(selector) || [],
        );
        const first = items[0],
          last = items.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, []);
  return (
    <span ref={marker} className="sr-only">
      Dialog
    </span>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
