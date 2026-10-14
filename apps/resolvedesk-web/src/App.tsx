import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  Copy,
  ExternalLink,
  FileText,
  History,
  Inbox,
  Layers3,
  Loader2,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

type Source = {
  id: string;
  title: string;
  url: string;
  version: string;
  visibility: string;
  origin: string;
  created_at: string;
  indexed: number;
};
type Passage = {
  id: string;
  snapshot_id: string;
  title: string;
  url: string;
  version: string;
  visibility: string;
  origin: string;
  text: string;
  heading?: string;
  anchor?: string;
};
type Claim = {
  id: string;
  text: string;
  category: string;
  version: string;
  citations: { passage_id: string; quote: string }[];
};
type Draft = {
  claims: Claim[];
  reply_order: string[];
  questions: string[];
  limitations: string[];
  evidence_state: string;
};
type Answer = {
  id: string;
  revision: number;
  draft: Draft;
  evidence: Passage[];
  approved_at: string | null;
  approved_by: string | null;
};
type Run = {
  id: string;
  status: string;
  error: string | null;
  answer: Answer | null;
  events: {
    id: number;
    stage: string;
    outcome: string;
    detail: string;
    created_at: string;
    elapsed_ms: number;
  }[];
};
type Case = {
  id: string;
  title: string;
  question: string;
  server_version: string | null;
  client_version: string | null;
  os: string | null;
  revision: number;
  created_at: string;
  latest_run?: Run | null;
};
type Settings = { search_configured: boolean; index_revision: number };

async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  extraHeaders: Record<string, string> = {},
): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...extraHeaders },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const value = await response
      .json()
      .catch(() => ({ detail: "Request failed. Please retry." }));
    throw new Error(
      typeof value.detail === "string"
        ? value.detail
        : "Please check the form fields and try again.",
    );
  }
  return response.headers.get("content-type")?.includes("application/json")
    ? response.json()
    : (response.text() as Promise<T>);
}
const label = (value: string) => value.replaceAll("_", " ");
const time = (value: string) =>
  new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });

export default function App() {
  const [view, setView] = useState<"cases" | "knowledge">(
    window.location.hash === "#knowledge" ? "knowledge" : "cases",
  );
  const [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState<Case | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [modal, setModal] = useState<"case" | "source" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("");
  const [tab, setTab] = useState<"reply" | "history">("reply");
  const [mobilePane, setMobilePane] = useState<"ticket" | "reply" | "evidence">(
    "reply",
  );
  const [activeCitation, setActiveCitation] = useState<{
    passage: Passage;
    quote: string;
  } | null>(null);
  const [sourcePreview, setSourcePreview] = useState<{
    title: string;
    text: string;
    version: string;
  } | null>(null);
  const [editing, setEditing] = useState(false);
  const [texts, setTexts] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const [acknowledge, setAcknowledge] = useState(false);
  const [allowInternal, setAllowInternal] = useState(false);
  const [environment, setEnvironment] = useState({
    server_version: "",
    client_version: "",
    os: "",
  });

  const run = selected?.latest_run;
  const answer = run?.answer;
  const draft = answer?.draft;
  const investigating = run?.status === "queued" || run?.status === "running";
  const unresolved =
    draft?.evidence_state === "insufficient" ||
    draft?.evidence_state === "conflicting";
  const needsAck = Boolean(
    draft &&
    (draft.limitations.length ||
      draft.questions.length ||
      draft.evidence_state === "partial"),
  );
  const hasInternal = Boolean(
    answer?.evidence.some(
      (p) =>
        p.visibility === "internal" &&
        draft?.claims.some((c) =>
          c.citations.some((ref) => ref.passage_id === p.id),
        ),
    ),
  );

  async function load() {
    const [items, knowledge, configuration] = await Promise.all([
      api<Case[]>("/v1/cases"),
      api<Source[]>("/v1/sources"),
      api<Settings>("/v1/settings"),
    ]);
    setCases(items);
    setSources(knowledge);
    setSettings(configuration);
  }
  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!modal && !sourcePreview) return;
    setError("");
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const controls = () => [
      ...(dialog?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), input, textarea, select, a[href], [tabindex="0"]',
      ) || []),
    ];
    controls()[0]?.focus();
    function keyboard(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setModal(null);
        setSourcePreview(null);
      }
      if (event.key === "Tab") {
        const items = controls();
        const first = items[0],
          last = items.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    }
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("keydown", keyboard);
      previous?.focus();
    };
  }, [modal, sourcePreview]);
  useEffect(() => {
    if (!selected?.id || !investigating) return;
    const id = selected.id;
    const timer = window.setInterval(() => {
      api<Case>(`/v1/cases/${id}`)
        .then((value) =>
          setSelected((current) => (current?.id === id ? value : current)),
        )
        .catch((e) => setError(e.message));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [selected?.id, investigating]);

  async function act(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Something went wrong. Please retry.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function openCase(id: string) {
    await act(async () => {
      const item = await api<Case>(`/v1/cases/${id}`);
      setSelected(item);
      setActiveCitation(null);
      setEditing(false);
      setTab("reply");
      setReason("");
      setAcknowledge(false);
      setAllowInternal(false);
      setEnvironment({
        server_version: item.server_version || "",
        client_version: item.client_version || "",
        os: item.os || "",
      });
      setMobilePane("reply");
      setView("cases");
    });
  }
  async function investigate() {
    if (!selected) return;
    await act(async () => {
      await api(`/v1/cases/${selected.id}/runs`, "POST", undefined, {
        "Idempotency-Key": crypto.randomUUID(),
      });
      setSelected(await api<Case>(`/v1/cases/${selected.id}`));
      setActiveCitation(null);
      setEditing(false);
      setReason("");
      setAcknowledge(false);
      setAllowInternal(false);
    });
  }
  async function review(action: "approve" | "edit" | "escalate") {
    if (!answer || !selected) return;
    await act(async () => {
      await api(`/v1/answers/${answer.id}/review`, "PATCH", {
        expected_revision: answer.revision,
        action,
        reason,
        claim_texts: action === "edit" ? texts : {},
        acknowledge_limits: acknowledge,
        allow_internal: allowInternal,
      });
      setSelected(await api<Case>(`/v1/cases/${selected.id}`));
      setEditing(false);
      setNotice(
        action === "approve"
          ? "Reply approved. You can now copy or export this revision."
          : action === "edit"
            ? "New revision saved. Review the edited text against its evidence."
            : "Case marked for expert review.",
      );
    });
  }
  async function exportReply(
    format: "json" | "markdown",
    escalation = false,
    copy = false,
  ) {
    if (!answer) return;
    await act(async () => {
      const result = await api<unknown>(
        `/v1/answers/${answer.id}/exports`,
        "POST",
        { format, escalation },
      );
      const text =
        typeof result === "string" ? result : JSON.stringify(result, null, 2);
      if (copy) {
        await navigator.clipboard.writeText(text);
        setNotice("Approved reply copied.");
        return;
      }
      const href = URL.createObjectURL(
        new Blob([text], {
          type: format === "json" ? "application/json" : "text/markdown",
        }),
      );
      const link = document.createElement("a");
      link.href = href;
      link.download = `resolvedesk-${escalation ? "escalation" : "reply"}-${answer.revision}.${format === "json" ? "json" : "md"}`;
      link.click();
      URL.revokeObjectURL(href);
    });
  }
  function cite(reference: Claim["citations"][number]) {
    const passage = answer?.evidence.find((p) => p.id === reference.passage_id);
    if (passage) {
      setActiveCitation({ passage, quote: reference.quote });
      setMobilePane("evidence");
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="ResolveDesk home">
          <span className="brand-mark">
            <Layers3 size={23} />
          </span>
          <span>
            resolve<span className="brand-light">desk</span>
            <small>SUPPORT WITH SUBSTANCE</small>
          </span>
        </a>
        <div className="workspace-label">
          YOUR WORKSPACE <span>PILOT</span>
        </div>
        <nav aria-label="Primary">
          <a className="nav-item" href="#chat">
            <MessageSquare size={18} /> RAG chat
          </a>
          <button
            className={view === "cases" ? "nav-item active" : "nav-item"}
            onClick={() => setView("cases")}
          >
            <Inbox size={18} /> Support cases <span>{cases.length}</span>
          </button>
          <button
            className={view === "knowledge" ? "nav-item active" : "nav-item"}
            onClick={() => setView("knowledge")}
          >
            <BookOpen size={18} /> Knowledge library
          </button>
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={23} />
          <strong>Evidence before answers.</strong>
          <p>
            Inspect the source. Understand the limits. Send with confidence.
          </p>
        </div>
        <div className="account">
          <span className="avatar">SE</span>
          <div>
            Support engineer<small>Team workspace · PostgreSQL</small>
          </div>
          <span className="online-dot" />
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <span>
              {view === "knowledge"
                ? "Knowledge library"
                : selected
                  ? "Investigation"
                  : "Support cases"}
            </span>
          </div>
          <span className="version-chip">PostgreSQL 16 & 17</span>
          <button
            className="button primary small"
            onClick={() => setModal("case")}
          >
            <Plus size={15} /> New case
          </button>
        </header>
        {error && (
          <div className="banner error" role="alert">
            <CircleHelp size={18} />
            <span>{error}</span>
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}
        {notice && (
          <div className="banner success" role="status">
            <CheckCircle2 size={18} />
            <span>{notice}</span>
            <button
              aria-label="Dismiss notification"
              onClick={() => setNotice("")}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {view === "knowledge" ? (
          <section className="page">
            <div className="page-heading">
              <div>
                <span className="eyebrow">THE SOURCE OF YOUR ANSWERS</span>
                <h1>
                  Knowledge library<span className="heading-dot">.</span>
                </h1>
                <p>
                  Versioned documentation and approved runbooks. Every answer
                  starts here.
                </p>
              </div>
              <button
                className="button primary"
                onClick={() => setModal("source")}
              >
                <Plus size={16} /> Add knowledge
              </button>
            </div>
            <div className="knowledge-summary">
              <div>
                <BookOpen size={23} />
                <strong>{sources.filter((s) => s.indexed).length}</strong>
                <span>indexed sources</span>
              </div>
              <div>
                <History size={23} />
                <strong>{settings?.index_revision ?? 0}</strong>
                <span>index revision</span>
              </div>
              <div>
                <Search size={23} />
                <strong>
                  {settings?.search_configured ? "Enabled" : "Not configured"}
                </strong>
                <span>official-source search</span>
              </div>
            </div>
            {!settings?.search_configured && (
              <div className="callout">
                <CircleHelp size={18} />
                <div>
                  <strong>Search fallback needs a connection</strong>
                  <p>
                    Saved knowledge is available. An administrator must
                    configure the search service before ResolveDesk can search
                    official documentation for missing evidence.
                  </p>
                </div>
              </div>
            )}
            <div className="table-card">
              <div className="table-title">
                <h2>Your evidence collection</h2>
                <span>{sources.length} snapshots</span>
              </div>
              {sources.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Version</th>
                        <th>Visibility</th>
                        <th>Status</th>
                        <th>Captured</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {sources.map((s) => (
                        <tr key={s.id}>
                          <td>
                            <button
                              className="source-link"
                              onClick={() =>
                                act(async () => {
                                  setSourcePreview(
                                    await api(`/v1/sources/${s.id}`),
                                  );
                                })
                              }
                            >
                              <FileText size={17} />
                              <span>
                                {s.title}
                                <small>
                                  {s.url.startsWith("https:")
                                    ? "Official PostgreSQL documentation"
                                    : "Team runbook"}
                                </small>
                              </span>
                            </button>
                          </td>
                          <td>
                            <span className="tag">PG {s.version}</span>
                          </td>
                          <td>{label(s.visibility)}</td>
                          <td>
                            <span
                              className={`status ${s.indexed ? "supported" : "partial"}`}
                            >
                              {s.indexed ? "Indexed" : "Search evidence"}
                            </span>
                          </td>
                          <td className="muted">{time(s.created_at)}</td>
                          <td>
                            {!s.indexed && (
                              <button
                                className="button small"
                                onClick={() =>
                                  act(async () => {
                                    await api(
                                      `/v1/sources/${s.id}/promote`,
                                      "POST",
                                    );
                                    await load();
                                    setNotice(
                                      "Source promoted to the knowledge library.",
                                    );
                                  })
                                }
                              >
                                Promote
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty
                  icon={<BookOpen size={32} />}
                  title="Build your evidence collection"
                  text="Add official PostgreSQL documentation or an approved team runbook to start grounded investigations."
                  action={
                    <button
                      className="button primary"
                      onClick={() => setModal("source")}
                    >
                      Add your first source <ArrowRight size={16} />
                    </button>
                  }
                />
              )}
            </div>
          </section>
        ) : !selected ? (
          <section className="page">
            <div className="page-heading">
              <div>
                <span className="eyebrow">LESS SEARCHING. MORE RESOLVING.</span>
                <h1>
                  Support cases<span className="heading-dot">.</span>
                </h1>
                <p>
                  A clear path from customer question to a reply you can stand
                  behind.
                </p>
              </div>
              <div className="date-note">
                <Clock3 size={15} />
                {new Date().toLocaleDateString([], {
                  month: "long",
                  day: "numeric",
                })}
              </div>
            </div>
            <div className="intro-strip">
              <span className="intro-icon">
                <Sparkles size={22} />
              </span>
              <div>
                <strong>
                  Your next answer, grounded in the right version.
                </strong>
                <p>
                  Investigate PostgreSQL questions with sources, visible
                  uncertainty, and a human final check.
                </p>
              </div>
              <button className="text-button" onClick={() => setModal("case")}>
                Start an investigation <ArrowRight size={16} />
              </button>
            </div>
            <div className="table-card">
              <div className="table-title">
                <h2>
                  Case inbox <span className="count">{cases.length}</span>
                </h2>
                <label className="search-input">
                  <Search size={16} />
                  <input
                    placeholder="Find a case…"
                    aria-label="Find a case"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  />
                </label>
              </div>
              {cases.length ? (
                <div className="case-list">
                  {cases
                    .filter((c) =>
                      `${c.title} ${c.question}`
                        .toLowerCase()
                        .includes(filter.toLowerCase()),
                    )
                    .map((c, i) => (
                      <button
                        key={c.id}
                        className="case-row"
                        onClick={() => openCase(c.id)}
                      >
                        <span className="case-number">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <div>
                          <strong>{c.title}</strong>
                          <p>{c.question}</p>
                          <span>
                            PostgreSQL {c.server_version || "unknown"}{" "}
                            <span className="separator">·</span>{" "}
                            {c.os || "Environment incomplete"}
                          </span>
                        </div>
                        <span className="tag">
                          {c.client_version
                            ? `Client ${c.client_version}`
                            : "Client unknown"}
                        </span>
                        <ChevronRight size={18} />
                      </button>
                    ))}
                </div>
              ) : (
                <Empty
                  icon={<Inbox size={33} />}
                  title="Good support starts with a question"
                  text="Create a case with the customer's error and environment. ResolveDesk will find evidence, identify gaps, and prepare a reply for your review."
                  action={
                    <button
                      className="button primary"
                      onClick={() => setModal("case")}
                    >
                      <Plus size={16} /> Create a case
                    </button>
                  }
                />
              )}
            </div>
            <div className="footer-note">
              <ShieldCheck size={15} /> Every generated reply is a draft. Your
              review makes it ready.
            </div>
          </section>
        ) : (
          <section className="investigation">
            <div className="investigation-heading">
              <div>
                <button
                  className="back-link"
                  onClick={() => {
                    setSelected(null);
                    load().catch((e) => setError(e.message));
                  }}
                >
                  ← All cases
                </button>
                <h1>{selected.title}</h1>
                <div className="case-meta">
                  <span
                    className={`status ${answer?.approved_at ? "supported" : draft?.evidence_state || "neutral"}`}
                  >
                    {answer?.approved_at
                      ? "Approved reply"
                      : investigating
                        ? "Investigating"
                        : run
                          ? label(run.status)
                          : "Ready to investigate"}
                  </span>
                  <span>Created {time(selected.created_at)}</span>
                </div>
              </div>
              <button
                className="button primary"
                disabled={busy || investigating}
                onClick={investigate}
              >
                {investigating ? (
                  <Loader2 size={17} className="spin" />
                ) : (
                  <Sparkles size={17} />
                )}{" "}
                {run ? "New investigation" : "Investigate case"}
              </button>
            </div>
            <nav className="mobile-tabs" aria-label="Workbench panes">
              {(["ticket", "reply", "evidence"] as const).map((p) => (
                <button
                  key={p}
                  className={mobilePane === p ? "selected" : ""}
                  onClick={() => setMobilePane(p)}
                >
                  {label(p)}
                </button>
              ))}
            </nav>
            <div className="workbench">
              <aside
                className={`ticket-panel pane ${mobilePane === "ticket" ? "mobile-active" : ""}`}
              >
                <div className="pane-heading">
                  <Inbox size={16} />
                  <h2>The customer question</h2>
                </div>
                <p className="ticket-text">{selected.question}</p>
                <div className="section-rule" />
                <div className="mini-heading">
                  ENVIRONMENT <span>Revision {selected.revision}</span>
                </div>
                <form
                  className="environment-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    act(async () => {
                      const changed = await api<Case>(
                        `/v1/cases/${selected.id}/environment`,
                        "PATCH",
                        {
                          expected_revision: selected.revision,
                          changes: {
                            server_version: environment.server_version || null,
                            client_version: environment.client_version || null,
                            os: environment.os || null,
                          },
                        },
                      );
                      setSelected({
                        ...changed,
                        latest_run: selected.latest_run,
                      });
                      setNotice(
                        "Environment updated. Start a new investigation to use these details.",
                      );
                    });
                  }}
                >
                  <label>
                    Server version
                    <input
                      placeholder="Unknown"
                      value={environment.server_version}
                      onChange={(e) =>
                        setEnvironment({
                          ...environment,
                          server_version: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Client utility version
                    <input
                      placeholder="Unknown"
                      value={environment.client_version}
                      onChange={(e) =>
                        setEnvironment({
                          ...environment,
                          client_version: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Operating system
                    <input
                      placeholder="Unknown"
                      value={environment.os}
                      onChange={(e) =>
                        setEnvironment({ ...environment, os: e.target.value })
                      }
                    />
                  </label>
                  <button className="button small" disabled={busy}>
                    Save environment
                  </button>
                </form>
                <div className="ticket-tip">
                  <CircleHelp size={17} />
                  <p>
                    The server and backup client can have different versions.
                    Missing details stay visible.
                  </p>
                </div>
              </aside>

              <section
                className={`reply-panel pane ${mobilePane === "reply" ? "mobile-active" : ""}`}
              >
                <div className="reply-tabs">
                  <button
                    className={tab === "reply" ? "selected" : ""}
                    onClick={() => setTab("reply")}
                  >
                    <FileText size={16} /> Reply draft
                  </button>
                  <button
                    className={tab === "history" ? "selected" : ""}
                    onClick={() => setTab("history")}
                  >
                    <History size={16} /> Investigation{" "}
                    {run && <span>{run.events.length}</span>}
                  </button>
                </div>
                {tab === "history" ? (
                  <div className="timeline">
                    {run?.events.length ? (
                      run.events.map((event) => (
                        <div className="timeline-event" key={event.id}>
                          <span className={`timeline-dot ${event.outcome}`} />
                          <div>
                            <strong>
                              {label(event.stage)}{" "}
                              <span className="tag">{event.outcome}</span>
                            </strong>
                            <p>{event.detail}</p>
                            <small>
                              {time(event.created_at)}{" "}
                              {event.elapsed_ms > 0 &&
                                `· ${(event.elapsed_ms / 1000).toFixed(1)}s`}
                            </small>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="muted">
                        Start an investigation to see its evidence and history.
                      </p>
                    )}
                  </div>
                ) : (
                  <>
                    {investigating && (
                      <div className="investigating-state" role="status">
                        <Loader2 size={19} className="spin" />
                        <div>
                          <strong>Building an evidence-backed reply</strong>
                          <p>
                            {run?.events.at(-1)?.stage
                              ? label(run.events.at(-1)!.stage)
                              : "Waiting for the worker"}{" "}
                            · this may take a few minutes
                          </p>
                        </div>
                      </div>
                    )}
                    {run?.error && (
                      <div className="callout danger">
                        <CircleHelp size={18} />
                        <div>
                          <strong>Investigation paused</strong>
                          <p>{run.error}</p>
                          <button
                            className="button small"
                            disabled={busy}
                            onClick={() =>
                              act(async () => {
                                await api(`/v1/runs/${run.id}/retry`, "POST");
                                setSelected(
                                  await api(`/v1/cases/${selected.id}`),
                                );
                              })
                            }
                          >
                            <RefreshCw size={14} /> Retry from saved evidence
                          </button>
                        </div>
                      </div>
                    )}
                    {draft ? (
                      <div className="answer-content">
                        <div
                          className={`evidence-banner ${draft.evidence_state}`}
                        >
                          <ShieldCheck size={20} />
                          <div>
                            <strong>
                              {label(draft.evidence_state)} evidence
                            </strong>
                            <p>
                              {draft.evidence_state === "supported"
                                ? "Sources checked. Inspect the citations before approving."
                                : "Review the limitations below before taking the next step."}
                            </p>
                          </div>
                          <span>v{answer!.revision}</span>
                        </div>
                        {(draft.questions.length > 0 ||
                          draft.limitations.length > 0) && (
                          <div className="limitations">
                            <h3>
                              <CircleHelp size={16} /> What still needs
                              attention
                            </h3>
                            {draft.questions.map((q, i) => (
                              <p key={`q${i}`}>
                                <strong>Clarify:</strong> {q}
                              </p>
                            ))}
                            {draft.limitations.map((l, i) => (
                              <p key={`l${i}`}>{l}</p>
                            ))}
                          </div>
                        )}
                        {draft.claims.length ? (
                          <>
                            <div className="draft-overline">
                              {answer?.approved_at
                                ? "APPROVED CUSTOMER REPLY"
                                : "CUSTOMER REPLY · FOR YOUR REVIEW"}
                            </div>
                            {draft.reply_order.map((id) => {
                              const claim = draft.claims.find(
                                (c) => c.id === id,
                              )!;
                              return (
                                <div className="claim" key={id}>
                                  {editing ? (
                                    <label className="claim-editor">
                                      Edit claim {id}
                                      <textarea
                                        rows={4}
                                        value={texts[id] ?? claim.text}
                                        onChange={(e) =>
                                          setTexts({
                                            ...texts,
                                            [id]: e.target.value,
                                          })
                                        }
                                      />
                                    </label>
                                  ) : (
                                    <p>{claim.text}</p>
                                  )}
                                  <div className="claim-citations">
                                    {claim.citations.map((ref, i) => (
                                      <button
                                        key={`${ref.passage_id}-${i}`}
                                        onClick={() => cite(ref)}
                                        className={
                                          activeCitation?.passage.id ===
                                          ref.passage_id
                                            ? "citation selected"
                                            : "citation"
                                        }
                                      >
                                        <BookOpen size={12} />
                                        {answer!.evidence.find(
                                          (p) => p.id === ref.passage_id,
                                        )?.title || "Source"}{" "}
                                        <span>{i + 1}</span>
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              );
                            })}
                          </>
                        ) : (
                          <div className="no-answer">
                            <CircleHelp size={28} />
                            <h3>
                              A good next question is better than a guess.
                            </h3>
                            <p>
                              Use the clarification or escalation details above
                              to move this case forward.
                            </p>
                          </div>
                        )}
                        {answer?.approved_at && (
                          <div className="approved-note">
                            <CheckCircle2 size={17} /> Reviewed by{" "}
                            {answer.approved_by} · {time(answer.approved_at)}
                          </div>
                        )}
                        <div className="review-box">
                          <h3>Make it ready to send</h3>
                          <p>
                            Record what you checked. Approval applies to this
                            revision only.
                          </p>
                          <label>
                            Review reason
                            <input
                              placeholder="e.g. Checked client compatibility against the cited manual"
                              value={reason}
                              onChange={(e) => setReason(e.target.value)}
                            />
                          </label>
                          {needsAck && (
                            <label className="check-label">
                              <input
                                type="checkbox"
                                checked={acknowledge}
                                onChange={(e) =>
                                  setAcknowledge(e.target.checked)
                                }
                              />{" "}
                              I reviewed and acknowledge the visible
                              limitations.
                            </label>
                          )}
                          {hasInternal && (
                            <label className="check-label">
                              <input
                                type="checkbox"
                                checked={allowInternal}
                                onChange={(e) =>
                                  setAllowInternal(e.target.checked)
                                }
                              />{" "}
                              I authorize the cited internal content in this
                              export.
                            </label>
                          )}
                          <div className="review-actions">
                            {editing ? (
                              <>
                                <button
                                  className="button primary"
                                  disabled={busy || reason.length < 3}
                                  onClick={() => review("edit")}
                                >
                                  <Check size={15} /> Save new revision
                                </button>
                                <button
                                  className="button"
                                  onClick={() => setEditing(false)}
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  className="button primary"
                                  disabled={
                                    busy ||
                                    investigating ||
                                    run?.status === "failed" ||
                                    unresolved ||
                                    !draft.claims.length ||
                                    reason.length < 3 ||
                                    (needsAck && !acknowledge) ||
                                    (hasInternal && !allowInternal)
                                  }
                                  onClick={() => review("approve")}
                                >
                                  <ShieldCheck size={16} /> Approve reply
                                </button>
                                <button
                                  className="button"
                                  disabled={
                                    busy ||
                                    !draft.claims.length ||
                                    investigating
                                  }
                                  onClick={() => {
                                    setEditing(true);
                                    setTexts(
                                      Object.fromEntries(
                                        draft.claims.map((c) => [c.id, c.text]),
                                      ),
                                    );
                                  }}
                                >
                                  Edit wording
                                </button>
                                <button
                                  className="text-button"
                                  disabled={busy || reason.length < 3}
                                  onClick={() => review("escalate")}
                                >
                                  Escalate
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                        <div className="export-actions">
                          <button
                            className="button small"
                            disabled={!answer?.approved_at || busy}
                            onClick={() => exportReply("markdown", false, true)}
                          >
                            <Copy size={14} /> Copy approved reply
                          </button>
                          <button
                            className="button small"
                            disabled={!answer?.approved_at || busy}
                            onClick={() => exportReply("markdown")}
                          >
                            <ArrowDownToLine size={14} /> Markdown
                          </button>
                          <button
                            className="button small"
                            disabled={!answer?.approved_at || busy}
                            onClick={() => exportReply("json")}
                          >
                            JSON
                          </button>
                          <button
                            className="text-button"
                            disabled={busy}
                            onClick={() => exportReply("markdown", true)}
                          >
                            Export escalation
                          </button>
                        </div>
                      </div>
                    ) : (
                      !investigating && (
                        <Empty
                          icon={<Sparkles size={31} />}
                          title="Let's get to the substance"
                          text="Start an investigation to retrieve the right documentation and prepare a cited reply. Missing evidence will be flagged."
                          action={
                            <button
                              className="button primary"
                              disabled={busy}
                              onClick={investigate}
                            >
                              Investigate case <ArrowRight size={16} />
                            </button>
                          }
                        />
                      )
                    )}
                  </>
                )}
              </section>

              <aside
                className={`evidence-panel pane ${mobilePane === "evidence" ? "mobile-active" : ""}`}
              >
                <div className="pane-heading">
                  <BookOpen size={17} />
                  <h2>Evidence</h2>
                  <span>{answer?.evidence.length ?? 0}</span>
                </div>
                {activeCitation ? (
                  <div className="source-detail">
                    <span className="eyebrow">
                      {activeCitation.passage.origin === "search"
                        ? "FOUND BY OFFICIAL-SOURCE SEARCH"
                        : activeCitation.passage.visibility === "internal"
                          ? "INTERNAL TEAM KNOWLEDGE"
                          : "INDEXED DOCUMENTATION"}
                    </span>
                    <h3>{activeCitation.passage.title}</h3>
                    <span className="tag">
                      PostgreSQL {activeCitation.passage.version}
                    </span>
                    <div
                      className="source-passage"
                      tabIndex={0}
                      role="region"
                      aria-label="Source passage"
                    >
                      <Highlighted
                        text={activeCitation.passage.text}
                        quote={activeCitation.quote}
                      />
                    </div>
                    <div className="quote-exact">
                      <strong>Cited quote</strong>
                      <p>{activeCitation.quote}</p>
                    </div>
                    {activeCitation.passage.url.startsWith("https://") && (
                      <a
                        className="button small"
                        href={
                          activeCitation.passage.url +
                          (activeCitation.passage.anchor
                            ? "#" +
                              encodeURIComponent(activeCitation.passage.anchor)
                            : "")
                        }
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open official page <ExternalLink size={13} />
                      </a>
                    )}
                    <p className="source-disclaimer">
                      Showing the saved evidence used for this answer. The live
                      page may have changed.
                    </p>
                  </div>
                ) : (
                  <div className="evidence-empty">
                    <BookOpen size={30} />
                    <h3>See what supports the answer.</h3>
                    <p>
                      Select a citation in the reply to inspect its exact
                      passage, version, and origin.
                    </p>
                    {answer?.evidence.map((p) => (
                      <button
                        key={p.id}
                        className="evidence-item"
                        onClick={() => {
                          setActiveCitation({ passage: p, quote: "" });
                          setMobilePane("evidence");
                        }}
                      >
                        <FileText size={15} />
                        <span>
                          {p.title}
                          <small>
                            PostgreSQL {p.version} · {label(p.origin)}
                          </small>
                        </span>
                        <ChevronRight size={14} />
                      </button>
                    ))}
                  </div>
                )}
              </aside>
            </div>
          </section>
        )}
      </main>

      {modal && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <button
              className="modal-close"
              aria-label="Close dialog"
              onClick={() => setModal(null)}
            >
              <X size={20} />
            </button>
            <span className="eyebrow">
              {modal === "case"
                ? "START WITH THE QUESTION"
                : "BUILD YOUR EVIDENCE"}
            </span>
            <h2 id="modal-title">
              {modal === "case" ? "Create a support case" : "Add knowledge"}
            </h2>
            {error && (
              <div className="banner error" role="alert">
                {error}
              </div>
            )}
            {modal === "case" ? (
              <form
                onSubmit={(e: FormEvent<HTMLFormElement>) => {
                  e.preventDefault();
                  const values = new FormData(e.currentTarget);
                  act(async () => {
                    const item = await api<Case>("/v1/cases", "POST", {
                      title: values.get("title"),
                      question: values.get("question"),
                      server_version: values.get("server") || null,
                      client_version: values.get("client") || null,
                      os: values.get("os") || null,
                    });
                    setModal(null);
                    await load();
                    setSelected(item);
                    setEnvironment({
                      server_version: item.server_version || "",
                      client_version: item.client_version || "",
                      os: item.os || "",
                    });
                    setView("cases");
                    setActiveCitation(null);
                    setTab("reply");
                  });
                }}
              >
                <label>
                  Case title
                  <input
                    name="title"
                    required
                    minLength={2}
                    maxLength={200}
                    placeholder="e.g. Backup fails after server upgrade"
                    autoFocus
                  />
                </label>
                <label>
                  Customer question or error
                  <textarea
                    name="question"
                    rows={5}
                    required
                    minLength={5}
                    maxLength={20000}
                    placeholder="Paste the question and relevant error. Avoid credentials and connection strings."
                  />
                </label>
                <div className="form-row">
                  <label>
                    Server version
                    <input name="server" placeholder="e.g. 17" />
                  </label>
                  <label>
                    Client utility version
                    <input name="client" placeholder="e.g. 16" />
                  </label>
                </div>
                <label>
                  Operating system
                  <input name="os" placeholder="e.g. Windows Server" />
                </label>
                <p className="form-hint">
                  Unknown details can be left blank. ResolveDesk will ask when
                  they matter.
                </p>
                <button className="button primary" disabled={busy}>
                  <Plus size={16} /> Create case
                </button>
              </form>
            ) : (
              <KnowledgeForm
                busy={busy}
                submit={async (mode, values) => {
                  await act(async () => {
                    if (mode === "official") {
                      const result = await api<{
                        results: { status: string }[];
                      }>("/v1/sources/refresh", "POST", { urls: [values.url] });
                      if (result.results.some((r) => r.status !== "ready"))
                        throw new Error(
                          "Source could not be fetched. Use a PostgreSQL 16 or 17 official documentation page.",
                        );
                    } else
                      await api("/v1/sources", "POST", {
                        title: values.title,
                        text: values.text,
                        version: values.version,
                        visibility: "internal",
                      });
                    await load();
                    setModal(null);
                    setNotice(
                      "Knowledge added. Future investigations will use the new index revision.",
                    );
                  });
                }}
              />
            )}
          </section>
        </div>
      )}
      {sourcePreview && (
        <div className="modal-backdrop">
          <section
            className="modal wide"
            role="dialog"
            aria-modal="true"
            aria-label="Source snapshot"
          >
            <button
              className="modal-close"
              aria-label="Close source"
              onClick={() => setSourcePreview(null)}
            >
              <X size={20} />
            </button>
            <span className="eyebrow">
              PINNED SOURCE SNAPSHOT · PG {sourcePreview.version}
            </span>
            <h2>{sourcePreview.title}</h2>
            <pre className="source-preview" tabIndex={0}>
              {sourcePreview.text}
            </pre>
          </section>
        </div>
      )}
    </div>
  );
}

function Empty({
  icon,
  title,
  text,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">{icon}</span>
      <h2>{title}</h2>
      <p>{text}</p>
      {action}
    </div>
  );
}
function Highlighted({ text, quote }: { text: string; quote: string }) {
  const index = quote ? text.indexOf(quote) : -1;
  return (
    <>
      {index < 0 ? (
        text
      ) : (
        <>
          {text.slice(0, index)}
          <mark>{quote}</mark>
          {text.slice(index + quote.length)}
        </>
      )}
    </>
  );
}
function KnowledgeForm({
  busy,
  submit,
}: {
  busy: boolean;
  submit: (mode: string, values: Record<string, string>) => Promise<void>;
}) {
  const [mode, setMode] = useState("official");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const data = new FormData(e.currentTarget);
        submit(
          mode,
          Object.fromEntries(
            [...data].map(([key, value]) => [key, String(value)]),
          ),
        );
      }}
    >
      <div className="segmented">
        <button
          type="button"
          className={mode === "official" ? "selected" : ""}
          onClick={() => setMode("official")}
        >
          Official documentation
        </button>
        <button
          type="button"
          className={mode === "runbook" ? "selected" : ""}
          onClick={() => setMode("runbook")}
        >
          Team runbook
        </button>
      </div>
      {mode === "official" ? (
        <>
          <label>
            Official page URL
            <input
              name="url"
              type="url"
              required
              placeholder="https://www.postgresql.org/docs/17/app-pgdump.html"
            />
          </label>
          <p className="form-hint">
            ResolveDesk fetches and snapshots versioned PostgreSQL 16 or 17
            documentation. Refreshing preserves earlier evidence.
          </p>
        </>
      ) : (
        <>
          <label>
            Runbook title
            <input
              name="title"
              required
              minLength={2}
              placeholder="Approved backup troubleshooting runbook"
            />
          </label>
          <label>
            PostgreSQL version
            <select name="version">
              <option value="17">17</option>
              <option value="16">16</option>
            </select>
          </label>
          <label>
            Runbook text
            <textarea
              name="text"
              rows={8}
              required
              minLength={20}
              placeholder="Paste approved Markdown or text. Runbooks remain internal."
            />
          </label>
          <p className="form-hint">
            Internal evidence needs explicit reviewer authorization before it
            appears in a customer export.
          </p>
        </>
      )}
      <button className="button primary" disabled={busy}>
        {busy ? <Loader2 size={16} className="spin" /> : <BookOpen size={16} />}{" "}
        {busy ? "Adding evidence…" : "Add knowledge"}
      </button>
    </form>
  );
}
