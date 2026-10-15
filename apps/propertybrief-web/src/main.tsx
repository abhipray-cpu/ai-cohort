import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowRight,
  Building2,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Layers3,
  LoaderCircle,
  MapPin,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Square,
  X,
} from "lucide-react";
import {
  coverageLabel,
  date,
  human,
  progress,
  recordLabel,
} from "./presentation";
import "./styles.css";

type Identity = {
  id: string;
  building_id: string;
  bin: string | null;
  bbl: string;
  address: string;
  borough: string;
};
type Case = {
  id: string;
  input: { address: string; borough: string; question: string };
  identity: Identity | null;
  revision: number;
  candidates: Identity[];
  messages?: { id: string; content: string; created_at: string }[];
  runs?: { id: string; status: string; question: string }[];
};
type RecordRow = {
  id: string;
  source: string;
  status: string;
  scope: string;
  description: string;
  flags: string[];
  fields: Record<string, string>;
};
type Source = {
  key: string;
  title: string;
  catalog: string;
  required: boolean;
};
type Evidence = {
  source: string;
  record_id: string;
  field: string;
  value: string;
};
type Draft = {
  summary: string;
  findings: { id: string; text: string; kind: string; evidence: Evidence[] }[];
  tasks: {
    title: string;
    recipient: string;
    priority: string;
    reason: string;
    verification: string;
  }[];
  limitations: string[];
};
type Report = {
  id: string;
  revision: number;
  reviewed_at: string | null;
  notes: string;
  payload: {
    draft: Draft;
    coverage: Record<string, string>;
    gaps: string[];
    critique: { outcome: string; issues: string[] };
    status: string;
    stop_reason: string;
    source_manifest: {
      source: string;
      snapshot_id: string;
      retrieved_at: string;
      catalog: string;
    }[];
  };
};
type Run = {
  id: string;
  status: string;
  question: string;
  actions: number;
  model_calls: number;
  grant: number;
  stop_reason: string | null;
  events: {
    id: number;
    stage: string;
    outcome: string;
    detail: string;
    created_at: string;
  }[];
  report: Report | null;
  preview: {
    coverage: Record<string, string>;
    sources: {
      source: string;
      count: number;
      outcome: string;
      completeness: string;
      flags: string[];
      retrieved_at: string;
      snapshot_id: string;
      records: RecordRow[];
    }[];
  };
};
type Snapshot = {
  payload: {
    source: string;
    catalog: string;
    retrieved_at: string;
    records: RecordRow[];
    completeness: string;
    sha256: string;
  };
};

async function api<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : `Request failed (${response.status})`,
    );
  }
  return response.json();
}
function App() {
  const [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState<Case | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [tab, setTab] = useState("conversation");
  const [search, setSearch] = useState("");
  const [address, setAddress] = useState("");
  const [borough, setBorough] = useState("Brooklyn");
  const [bin, setBin] = useState("");
  const [question, setQuestion] = useState(
    "Investigate recorded issues and prepare a diligence plan.",
  );
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [recordId, setRecordId] = useState("");
  const [notes, setNotes] = useState("");
  const [ack, setAck] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [editedDraft, setEditedDraft] = useState<Draft | null>(null);
  const active = run && ["queued", "running"].includes(run.status);
  const report = run?.report;
  const required = sources.filter((source) => source.required);
  const coverage = run?.preview.coverage || {};
  const checked = Object.values(coverage).filter(
    (value) => value === "complete_for_query",
  ).length;
  const title = (key: string) =>
    sources.find((source) => source.key === key)?.title || human(key);
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }
  async function list() {
    setCases(await api<Case[]>("/v1/cases"));
  }
  async function load(cid: string) {
    const item = await api<Case>(`/v1/cases/${cid}`);
    setSelected(item);
    setRun(
      item.runs?.length ? await api<Run>(`/v1/runs/${item.runs[0].id}`) : null,
    );
  }
  useEffect(() => {
    void perform(async () => {
      await list();
      const settings = await api<{ sources: Source[] }>("/v1/settings");
      setSources(settings.sources);
    });
  }, []);
  useEffect(() => {
    if (!active || !run) return;
    const timer = setInterval(() => {
      void api<Run>(`/v1/runs/${run.id}`)
        .then(setRun)
        .catch((e) => setError(String(e)));
    }, 2000);
    return () => clearInterval(timer);
  }, [run?.id, active]);
  useEffect(() => {
    if (!snapshot && !showReview) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const focusable = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          "button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)",
        ) || [],
      );
    focusable()[0]?.focus();
    function keydown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSnapshot(null);
        setShowReview(false);
      }
      if (event.key === "Tab") {
        const items = focusable();
        if (event.shiftKey && document.activeElement === items[0]) {
          event.preventDefault();
          items.at(-1)?.focus();
        } else if (!event.shiftKey && document.activeElement === items.at(-1)) {
          event.preventDefault();
          items[0]?.focus();
        }
      }
    }
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      previous?.focus();
    };
  }, [!!snapshot, showReview]);
  async function create(event: React.FormEvent) {
    event.preventDefault();
    await perform(async () => {
      const item = await api<Case>("/v1/cases", "POST", {
        address,
        borough,
        question,
        bin: bin || null,
      });
      setSelected(item);
      setRun(null);
      await list();
    });
  }
  async function resolve() {
    if (!selected) return;
    await perform(async () =>
      setSelected(await api<Case>(`/v1/cases/${selected.id}/resolve`, "POST")),
    );
  }
  async function confirm(id: string) {
    if (!selected) return;
    await perform(async () => {
      setSelected(
        await api<Case>(`/v1/cases/${selected.id}/identity`, "POST", {
          candidate_id: id,
          expected_revision: selected.revision,
        }),
      );
      await list();
    });
  }
  async function start(path = "runs", content?: string) {
    if (!selected) return;
    await perform(async () => {
      const next = await api<Run>(
        `/v1/cases/${selected.id}/${path}`,
        "POST",
        content ? { content } : undefined,
      );
      setRun(next);
      setSelected(await api<Case>(`/v1/cases/${selected.id}`));
      setMessage("");
      setTab("conversation");
    });
  }
  async function evidence(source: string, rowId = "") {
    const found = run?.preview.sources.find((value) => value.source === source);
    if (!found?.snapshot_id) return;
    await perform(async () => {
      const result = await api<Snapshot>(`/v1/snapshots/${found.snapshot_id}`);
      setSnapshot(result);
      setRecordId(rowId || result.payload.records[0]?.id || "");
    });
  }
  async function review() {
    if (!report || !run) return;
    await perform(async () => {
      await api(`/v1/reports/${report.id}/review`, "PATCH", {
        expected_revision: report.revision,
        notes,
        acknowledge_limits: ack,
        draft: editedDraft,
      });
      setRun(await api<Run>(`/v1/runs/${run.id}`));
      setShowReview(false);
    });
  }
  async function download(format = "markdown") {
    if (!report) return;
    await perform(async () => {
      const response = await fetch(`/v1/reports/${report.id}/exports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format }),
      });
      if (!response.ok)
        throw new Error(
          "Review this report and acknowledge its limitations before export.",
        );
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `propertybrief-${report.id}.${format === "markdown" ? "md" : "json"}`;
      link.click();
      URL.revokeObjectURL(url);
    });
  }
  const selectedRecord = snapshot?.payload.records.find(
    (row) => row.id === recordId,
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/">
          <span className="brand-mark">
            <Building2 size={22} />
          </span>
          <span>
            PropertyBrief<small>ACQUISITION WORKSPACE</small>
          </span>
        </a>
        <button
          className="new-case"
          onClick={() => {
            setSelected(null);
            setRun(null);
            setError("");
            setTab("conversation");
          }}
        >
          <Plus size={17} /> New investigation
        </button>
        <div className="sidebar-label">
          YOUR WORKSPACE <span>{cases.length}</span>
        </div>
        <label className="search-box">
          <Search size={15} />
          <input
            aria-label="Search properties"
            placeholder="Find a property…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <nav aria-label="Property investigations">
          {cases
            .filter((item) =>
              item.input.address.toLowerCase().includes(search.toLowerCase()),
            )
            .map((item) => (
              <button
                key={item.id}
                className={`case-link ${selected?.id === item.id ? "selected" : ""}`}
                onClick={() => void perform(() => load(item.id))}
              >
                <Building2 size={17} />
                <span>
                  {item.input.address}
                  <small>
                    {item.input.borough} ·{" "}
                    {item.identity
                      ? "Identity confirmed"
                      : "Needs confirmation"}
                  </small>
                </span>
                <ChevronRight size={14} />
              </button>
            ))}
          {!cases.length && (
            <p className="sidebar-empty">
              Your property investigations will appear here.
            </p>
          )}
        </nav>
        <div className="sidebar-footer">
          <ShieldCheck size={17} />
          <div>
            Evidence comes first<small>Official NYC public records</small>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>
              {selected ? "Property investigation" : "New investigation"}
            </span>
          </div>
          <span className="jurisdiction">
            <span /> NYC residential
          </span>
          <select className="mobile-cases" aria-label="Choose property investigation" value={selected?.id || ''} onChange={event => {if(event.target.value) void perform(() => load(event.target.value)); else {setSelected(null);setRun(null);}}}>
            <option value="">New investigation</option>
            {cases.map(item => <option key={item.id} value={item.id}>{item.input.address}</option>)}
          </select>
        </header>
        {error && (
          <div className="error" role="alert">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}
        {!selected ? (
          <div className="welcome">
            <div className="eyebrow">
              <span /> PROPERTY DUE DILIGENCE
            </div>
            <h1>
              Every property has a story.
              <br />
              <em>Start with the evidence.</em>
            </h1>
            <p className="lead">
              Investigate recorded issues, understand what needs clarification,
              and prepare your next move.
            </p>
            <form className="start-card" onSubmit={create}>
              <div className="card-heading">
                <span className="soft-icon">
                  <MapPin size={21} />
                </span>
                <div>
                  <h2>Which property are you investigating?</h2>
                  <p>
                    Start with the full official street address or a known
                    building identifier.
                  </p>
                </div>
              </div>
              <label>
                Property address
                <input
                  required
                  minLength={3}
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="e.g. 22 FRONT STAGG STREET"
                />
              </label>
              <div className="form-grid">
                <label>
                  Borough
                  <select
                    value={borough}
                    onChange={(e) => setBorough(e.target.value)}
                  >
                    {[
                      "Manhattan",
                      "Bronx",
                      "Brooklyn",
                      "Queens",
                      "Staten Island",
                    ].map((b) => (
                      <option key={b}>{b}</option>
                    ))}
                  </select>
                </label>
                <label>
                  BIN <span className="muted">optional</span>
                  <input
                    value={bin}
                    pattern="[1-5][0-9]{6}"
                    onChange={(e) => setBin(e.target.value)}
                    placeholder="7-digit building identifier"
                  />
                </label>
              </div>
              <label>
                What would you like to investigate?
                <textarea
                  value={question}
                  required
                  onChange={(e) => setQuestion(e.target.value)}
                  rows={2}
                />
              </label>
              <div className="form-footer">
                <span>
                  <Layers3 size={15} /> Eight official record checks
                </span>
                <button className="primary" disabled={busy}>
                  Create investigation <ArrowRight size={16} />
                </button>
              </div>
            </form>
            <div className="value-grid">
              <div>
                <Search size={20} />
                <h3>Follow the evidence</h3>
                <p>Each finding guides the next useful check.</p>
              </div>
              <div>
                <FileText size={20} />
                <h3>Know what is recorded</h3>
                <p>Inspect original fields, statuses and dates.</p>
              </div>
              <div>
                <ClipboardCheck size={20} />
                <h3>Leave with a plan</h3>
                <p>Clear questions for your seller and advisors.</p>
              </div>
            </div>
            <p className="scope-note">
              Initial coverage: NYC housing and building records. Physical
              condition, title, valuation and repair estimates require separate
              diligence.
            </p>
          </div>
        ) : (
          <div className="case-workspace">
            <section className="property-heading">
              <div>
                <div className="eyebrow">PROPERTY INVESTIGATION</div>
                <h1>{selected.identity?.address || selected.input.address}</h1>
                <p>
                  <MapPin size={14} />
                  {selected.input.borough}
                  {selected.identity && (
                    <>
                      {" "}
                      <span>·</span> BIN{" "}
                      {selected.identity.bin || "unavailable"} <span>·</span>{" "}
                      BBL {selected.identity.bbl}
                    </>
                  )}
                </p>
              </div>
              <div className="heading-actions">
                <span className={`status ${run?.status || "pending"}`}>
                  {run
                    ? human(run.status)
                    : selected.identity
                      ? "Ready to investigate"
                      : "Confirm property"}
                </span>
                {report && (
                  <button
                    className="secondary"
                    onClick={() => void download()}
                    disabled={busy || !report.reviewed_at}
                  >
                    <ArrowDownToLine size={15} /> Export
                  </button>
                )}
              </div>
            </section>
            {!selected.identity ? (
              <section className="identity-card">
                <h2>Confirm the building before investigating</h2>
                <p>
                  Official identifiers keep records attached to the intended
                  building. A parcel can contain multiple buildings.
                </p>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => void resolve()}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={16} />
                  ) : (
                    <Search size={16} />
                  )}{" "}
                  Find official matches
                </button>
                <div className="candidate-list">
                  {selected.candidates.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => void confirm(item.id)}
                      disabled={busy}
                    >
                      <Building2 size={20} />
                      <span>
                        <strong>{item.address}</strong>
                        <small>
                          BIN {item.bin || "unavailable"} · BBL {item.bbl}
                        </small>
                      </span>
                      <span>
                        Select <ArrowRight size={15} />
                      </span>
                    </button>
                  ))}
                </div>
                {selected.candidates.length === 0 && (
                  <p className="muted">
                    If no match is returned, create a case with a known BIN or
                    the exact official address spelling.
                  </p>
                )}
              </section>
            ) : (
              <>
                <div
                  className="tabs"
                  role="tablist"
                  aria-label="Investigation views"
                >
                  {[
                    ["conversation", "Conversation", MessageSquare],
                    ["report", "Investigation pack", FileText],
                    ["checks", "Source checks", Layers3],
                    ["history", "Activity", ClipboardCheck],
                  ].map(([key, label, Icon]) => {
                    const Component = Icon as typeof MessageSquare;
                    return (
                      <button
                        role="tab"
                        aria-selected={tab === key}
                        key={key as string}
                        className={tab === key ? "active" : ""}
                        onClick={() => setTab(key as string)}
                      >
                        <Component size={16} />
                        {label as string}
                        {key === "checks" && <span>{checked}/8</span>}
                      </button>
                    );
                  })}
                </div>
                <div className="workspace-grid">
                  <section className="workspace-content">
                    {tab === "conversation" && (
                      <div className="conversation">
                        <div className="conversation-intro">
                          <span className="soft-icon">
                            <Building2 size={20} />
                          </span>
                          <div>
                            <h2>Your property research partner</h2>
                            <p>
                              I’ll check official records, follow relevant
                              findings, and make any missing evidence explicit.
                            </p>
                          </div>
                        </div>
                        {selected.messages?.map((item) => (
                          <div className="user-message" key={item.id}>
                            <span>YOU</span>
                            <p>{item.content}</p>
                            <small>{date(item.created_at)}</small>
                          </div>
                        ))}
                        {run && (
                          <div className="agent-message">
                            <div className="agent-label">
                              <span className="brand-mark small">
                                <Building2 size={14} />
                              </span>{" "}
                              PropertyBrief{" "}
                              <small>
                                {active
                                  ? "Investigating"
                                  : "Investigation update"}
                              </small>
                            </div>
                            {active ? (
                              <>
                                <p>
                                  Following the records for this property.
                                  Completed observations are saved as the
                                  investigation proceeds.
                                </p>
                                <div className="live-check">
                                  <LoaderCircle size={16} className="spin" />
                                  {run.events.at(-1)?.stage
                                    ? human(run.events.at(-1)!.stage)
                                    : "Waiting for the worker"}
                                  <span>{checked}/8 checks complete</span>
                                </div>
                                <button
                                  className="text-button"
                                  onClick={() =>
                                    void perform(async () => {
                                      await api(
                                        `/v1/runs/${run.id}/cancel`,
                                        "POST",
                                      );
                                      setRun(
                                        await api<Run>(`/v1/runs/${run.id}`),
                                      );
                                    })
                                  }
                                >
                                  <Square size={12} /> Cancel investigation
                                </button>
                              </>
                            ) : (
                              <>
                                <p>
                                  {report?.payload.draft.summary ||
                                    run.stop_reason}
                                </p>
                                <div className="result-card">
                                  <FileText size={22} />
                                  <div>
                                    <strong>
                                      {run.status === "completed"
                                        ? "Investigation pack ready"
                                        : "Partial observations saved"}
                                    </strong>
                                    <small>
                                      {report?.payload.draft.findings.length ||
                                        0}{" "}
                                      findings · {checked}/8 sources checked
                                    </small>
                                  </div>
                                  <button
                                    className="text-button"
                                    onClick={() => setTab("report")}
                                  >
                                    Review pack <ArrowRight size={15} />
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        )}
                        {!run && (
                          <div className="begin-card">
                            <h3>Identity confirmed. Ready when you are.</h3>
                            <p>{selected.input.question}</p>
                            <button
                              className="primary"
                              onClick={() => void start()}
                              disabled={busy}
                            >
                              Start investigation <ArrowRight size={16} />
                            </button>
                          </div>
                        )}
                        <form
                          className="composer"
                          onSubmit={(e) => {
                            e.preventDefault();
                            void start("messages", message);
                          }}
                        >
                          <textarea
                            aria-label="Ask a follow-up"
                            placeholder="Ask a follow-up about this property…"
                            rows={2}
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            disabled={!!active}
                          />
                          <button
                            className="primary icon-button"
                            aria-label="Send follow-up"
                            disabled={
                              busy || !!active || message.trim().length < 3
                            }
                          >
                            <Send size={17} />
                          </button>
                          <small>
                            Follow-ups use captured evidence. Refresh checks to
                            acquire current records.
                          </small>
                        </form>
                      </div>
                    )}
                    {tab === "checks" && (
                      <div className="checks-view">
                        <h2>What has been checked</h2>
                        <p className="muted">
                          A completed check describes the queried dataset and
                          scope. Missing sources remain visible.
                        </p>
                        {required.map((source) => {
                          const value = run?.preview.sources.find(
                            (item) => item.source === source.key,
                          );
                          return (
                            <button
                              className="source-row"
                              key={source.key}
                              disabled={!value?.snapshot_id}
                              onClick={() => void evidence(source.key)}
                            >
                              <span
                                className={`check-icon ${coverage[source.key] === "complete_for_query" ? "done" : ""}`}
                              >
                                {coverage[source.key] ===
                                "complete_for_query" ? (
                                  <Check size={15} />
                                ) : (
                                  <CircleHelp size={15} />
                                )}
                              </span>
                              <span>
                                <strong>{source.title}</strong>
                                <small>
                                  {value
                                    ? `${value.count} records · ${date(value.retrieved_at)}`
                                    : "Awaiting check"}
                                </small>
                              </span>
                              <span className="source-state">
                                {coverageLabel(
                                  coverage[source.key] || "not_checked",
                                )}
                              </span>
                              <ChevronRight size={15} />
                            </button>
                          );
                        })}
                      </div>
                    )}
                    {tab === "report" && (
                      <div className="report-view">
                        <div className="section-heading">
                          <div>
                            <div className="eyebrow">DILIGENCE PACK</div>
                            <h2>Findings & next steps</h2>
                          </div>
                          {report && (
                            <button
                              className="secondary"
                              onClick={() => {
                                setShowReview(true);
                                setNotes(report.notes);
                                setAck(false);
                                setEditedDraft(null);
                              }}
                            >
                              <ClipboardCheck size={15} />
                              {report.reviewed_at
                                ? "Review notes"
                                : "Review pack"}
                            </button>
                          )}
                        </div>
                        {!report ? (
                          <p className="empty-state">
                            Your report will appear here. Source observations
                            are available as soon as each check finishes.
                          </p>
                        ) : (
                          <>
                            <p className="report-summary">
                              {report.payload.draft.summary}
                            </p>
                            {(report.payload.gaps.length > 0 ||
                              report.payload.critique.outcome !== "pass") && (
                              <div className="limitation-banner">
                                <CircleHelp size={19} />
                                <div>
                                  <strong>Additional review is needed</strong>
                                  <p>
                                    {report.payload.gaps.length} source gaps ·
                                    critique{" "}
                                    {human(report.payload.critique.outcome)}.
                                    These limitations stay attached to exports.
                                  </p>
                                </div>
                              </div>
                            )}
                            <h3>
                              Recorded findings{" "}
                              <span>
                                {report.payload.draft.findings.length}
                              </span>
                            </h3>
                            {report.payload.draft.findings.map(
                              (finding, index) => (
                                <article className="finding" key={finding.id}>
                                  <div className="finding-number">
                                    {String(index + 1).padStart(2, "0")}
                                  </div>
                                  <div>
                                    <span className="finding-kind">
                                      {human(finding.kind)}
                                    </span>
                                    <p>{finding.text}</p>
                                    <div className="citations">
                                      {finding.evidence.map((ref, i) => (
                                        <button
                                          key={i}
                                          onClick={() =>
                                            void evidence(
                                              ref.source,
                                              ref.record_id,
                                            )
                                          }
                                        >
                                          <FileText size={12} />
                                          {title(ref.source)} · {ref.record_id}
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                </article>
                              ),
                            )}
                            <h3>Follow-up plan</h3>
                            {report.payload.draft.tasks.map((task, index) => (
                              <article className="task" key={index}>
                                <span className={`priority ${task.priority}`}>
                                  {task.priority}
                                </span>
                                <div>
                                  <h4>{task.title}</h4>
                                  <span className="task-recipient">
                                    For your {task.recipient}
                                  </span>
                                  <p>{task.reason}</p>
                                  <small>
                                    Verification: {task.verification}
                                  </small>
                                </div>
                              </article>
                            ))}
                            <h3>Limitations & review</h3>
                            <ul className="limitations">
                              {[
                                ...report.payload.draft.limitations,
                                ...report.payload.critique.issues,
                              ].map((value, index) => (
                                <li key={index}>{value}</li>
                              ))}
                            </ul>
                            <p className="muted">
                              {report.reviewed_at
                                ? `Reviewed ${date(report.reviewed_at)}. ${report.notes}`
                                : "Awaiting reviewer acceptance."}
                            </p>
                            <p className="muted">
                              Stop reason: {report.payload.stop_reason}
                            </p>
                          </>
                        )}
                      </div>
                    )}
                    {tab === "history" && (
                      <div className="history-view">
                        <h2>Investigation activity</h2>
                        <p className="muted">
                          Actions, reflections, validations and failures are
                          retained with the case.
                        </p>
                        {selected.runs && selected.runs.length > 1 && (
                          <label>
                            Investigation revision
                            <select
                              value={run?.id || ""}
                              onChange={(e) =>
                                void perform(async () =>
                                  setRun(
                                    await api<Run>(
                                      `/v1/runs/${e.target.value}`,
                                    ),
                                  ),
                                )
                              }
                            >
                              {selected.runs.map((value) => (
                                <option value={value.id} key={value.id}>
                                  {value.question.slice(0, 60)} · {value.status}
                                </option>
                              ))}
                            </select>
                          </label>
                        )}
                        {run?.events.map((event) => (
                          <details className="event" key={event.id}>
                            <summary>
                              <span className={`event-dot ${event.outcome}`} />
                              <strong>{human(event.stage)}</strong>
                              <span>{human(event.outcome)}</span>
                              <small>{date(event.created_at)}</small>
                            </summary>
                            <pre>{event.detail}</pre>
                          </details>
                        ))}
                        {!run?.events.length && (
                          <p className="empty-state">
                            Activity appears when an investigation starts.
                          </p>
                        )}
                      </div>
                    )}
                  </section>
                  <aside className="case-summary">
                    <div className="summary-title">
                      <ShieldCheck size={18} />
                      <h3>Investigation coverage</h3>
                    </div>
                    <div className="coverage-number">
                      {checked}
                      <span>/ 8</span>
                    </div>
                    <p>official source checks complete</p>
                    <div className="meter">
                      <div style={{ width: `${progress(checked, 8)}%` }} />
                    </div>
                    <div className="mini-checks">
                      {required.map((source) => (
                        <div key={source.key}>
                          <span
                            className={
                              coverage[source.key] === "complete_for_query"
                                ? "done"
                                : ""
                            }
                          >
                            {coverage[source.key] === "complete_for_query" ? (
                              <Check size={13} />
                            ) : (
                              <span className="tiny-circle" />
                            )}
                          </span>
                          <span>{source.title}</span>
                        </div>
                      ))}
                    </div>
                    <div className="summary-divider" />
                    <div className="budget">
                      <span>Diagnostic actions</span>
                      <strong>
                        {run?.actions || 0} / {run?.grant === 2 ? 32 : 16}
                      </strong>
                    </div>
                    <p className="summary-footnote">
                      Every investigation has a fixed action and time allowance.
                      Completed observations survive interruptions.
                    </p>
                    {selected.identity && !active && (
                      <button
                        className="secondary full"
                        disabled={busy}
                        onClick={() => void start("refresh")}
                      >
                        <RefreshCw size={14} /> Refresh source checks
                      </button>
                    )}
                    {run &&
                      ["partial", "cancelled"].includes(run.status) &&
                      run.grant < 2 && (
                        <button
                          className="text-button full"
                          disabled={busy}
                          onClick={() =>
                            void perform(async () => {
                              setRun(
                                await api<Run>(
                                  `/v1/runs/${run.id}/resume`,
                                  "POST",
                                ),
                              );
                              setTab("conversation");
                            })
                          }
                        >
                          Resume investigation <ArrowRight size={14} />
                        </button>
                      )}
                    <div className="scope-box">
                      <CircleHelp size={16} />
                      <p>
                        Public records support your research. Physical
                        inspection, title and financial diligence remain
                        separate checks.
                      </p>
                    </div>
                  </aside>
                </div>
              </>
            )}
          </div>
        )}
      </main>
      {snapshot && (
        <div className="drawer-backdrop" onClick={() => setSnapshot(null)}>
          <aside
            className="evidence-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Source evidence"
            onClick={(e) => e.stopPropagation()}
          >
            <header>
              <div>
                <div className="eyebrow">OFFICIAL SOURCE EVIDENCE</div>
                <h2>{title(snapshot.payload.source)}</h2>
              </div>
              <button
                aria-label="Close evidence"
                onClick={() => setSnapshot(null)}
              >
                <X size={20} />
              </button>
            </header>
            <p className="muted">
              Acquired {date(snapshot.payload.retrieved_at)} ·{" "}
              {coverageLabel(snapshot.payload.completeness)}
            </p>
            <a
              className="source-link"
              href={snapshot.payload.catalog}
              target="_blank"
              rel="noreferrer"
            >
              Open official dataset <ExternalLink size={13} />
            </a>
            <label>
              Captured record
              <select
                value={recordId}
                onChange={(e) => setRecordId(e.target.value)}
              >
                {snapshot.payload.records.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id} · {recordLabel(row.status)}
                  </option>
                ))}
              </select>
            </label>
            {selectedRecord ? (
              <>
                <div className="record-status">
                  <span className={`status ${selectedRecord.status}`}>
                    {recordLabel(selectedRecord.status)}
                  </span>
                  <span>{selectedRecord.scope} scope</span>
                </div>
                <p>{selectedRecord.description}</p>
                {selectedRecord.flags.length > 0 && (
                  <div className="limitation-banner">
                    {selectedRecord.flags.map(human).join(" · ")}
                  </div>
                )}
                <dl className="field-table">
                  {Object.entries(selectedRecord.fields).map(([key, value]) => (
                    <div key={key}>
                      <dt>{human(key)}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              </>
            ) : (
              <p className="empty-state">
                No captured records for this scoped query.
              </p>
            )}
            <small className="hash">SHA-256 {snapshot.payload.sha256}</small>
          </aside>
        </div>
      )}
      {showReview && report && (
        <div className="modal-backdrop">
          <section
            className="review-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-title"
          >
            <button
              className="modal-close"
              aria-label="Close review"
              onClick={() => setShowReview(false)}
            >
              <X size={19} />
            </button>
            <span className="soft-icon">
              <ClipboardCheck size={23} />
            </span>
            <h2 id="review-title">Review this investigation pack</h2>
            <p>
              Acceptance applies to this report revision. Source coverage and
              unresolved issues remain attached.
            </p>
            <label>
              Reviewer notes
              <textarea
                rows={4}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Record corrections, questions or follow-up context…"
              />
            </label>
            {!editedDraft ? (
              <button
                className="text-button"
                onClick={() =>
                  setEditedDraft(structuredClone(report.payload.draft))
                }
              >
                Edit report wording <FileText size={14} />
              </button>
            ) : (
              <div className="report-editor">
                <p className="muted">
                  Edits create a new report revision. Evidence references and
                  source gaps are preserved; prior critique will be marked as no
                  longer applicable.
                </p>
                <label>
                  Summary
                  <textarea
                    rows={3}
                    value={editedDraft.summary}
                    onChange={(event) =>
                      setEditedDraft({
                        ...editedDraft,
                        summary: event.target.value,
                      })
                    }
                  />
                </label>
                {editedDraft.findings.map((finding, index) => (
                  <label key={finding.id}>
                    Finding {index + 1}
                    <textarea
                      rows={3}
                      value={finding.text}
                      onChange={(event) =>
                        setEditedDraft({
                          ...editedDraft,
                          findings: editedDraft.findings.map((item, i) =>
                            i === index
                              ? { ...item, text: event.target.value }
                              : item,
                          ),
                        })
                      }
                    />
                  </label>
                ))}
              </div>
            )}
            <label className="checkbox">
              <input
                type="checkbox"
                checked={ack}
                onChange={(e) => setAck(e.target.checked)}
              />
              I have reviewed the evidence and acknowledge the listed
              limitations.
            </label>
            <button
              className="primary full"
              disabled={busy || !ack}
              onClick={() => void review()}
            >
              Accept reviewed pack <Check size={16} />
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
