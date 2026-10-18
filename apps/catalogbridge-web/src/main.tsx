import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  Boxes,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  FileDown,
  Layers3,
  LogOut,
  Plus,
  ShieldCheck,
  Upload,
  Wallet,
} from "lucide-react";
import {
  budgetLabel,
  canContinue,
  canReview,
  formatCost,
  isReviewStale,
  prettyState,
  validateBatch,
} from "./domain";
import "./style.css";

type Row = {
  id: string;
  title: string;
  brand: string;
  description: string;
  model: string;
  gtin: string;
  price: string;
};
type Task = {
  id: string;
  state: string;
  revision: number;
  source: Row;
  review: null | { action: string; candidate_id: string; actor: string };
  result: {
    reason?: string;
    candidate_id?: string;
    candidates?: Row[];
    conflicts?: Record<string, string[]>;
    proposal?: {
      reason: string;
      evidence: { side: string; field: string; quote: string }[];
    };
    effective_model?: string;
    model_requested?: string;
    calibrated?: boolean;
    exit_stage?: string;
    cached_from?: { task_id: string; batch_id: string; created: number; expires: number };
    local_routing?: { raw_score: number; band_precision_lower_bound: number; profile_sha256: string };
  };
};
type Batch = {
  id: string;
  state: string;
  spec: {
    master_id: string;
    supplier_id: string;
    egress: boolean;
    token_budget: number;
    economy_model: string;
    strong_model: string;
  };
};
type Metrics = {
  tokens: number;
  reserved_tokens: number;
  unknown_attempts: number;
  attempts: number;
  rows: number;
  remaining_tokens: number;
  states: Record<string, number>;
  routes: Record<string, number>;
  cost_basis: string;
  estimated_microunits: number | null;
  cost_unit: string;
  cost_per_input_row_microunits: number | null;
  journal_consistent: boolean;
  runtime_circuit?: { open: boolean; unknown_attempts: number; reason: string | null };
};
type Feed = { id: string; kind: string; hash: string };
type User = { name: string; role: string; csrf: string };

function App() {
  const [user, setUser] = useState<User | null>(null),
    [csrf, setCsrf] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [batches, setBatches] = useState<Batch[]>([]),
    [feeds, setFeeds] = useState<Feed[]>([]),
    [active, setActive] = useState(""),
    [tasks, setTasks] = useState<Task[]>([]),
    [metrics, setMetrics] = useState<Metrics | null>(null),
    [offset, setOffset] = useState(0),
    [taskId, setTaskId] = useState("");
  const [view, setView] = useState("workbench"),
    [setup, setSetup] = useState(false),
    [kind, setKind] = useState("master"),
    [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState("");
  const [master, setMaster] = useState(""),
    [supplier, setSupplier] = useState(""),
    [economy, setEconomy] = useState("gpt-6-luna"),
    [strong, setStrong] = useState("gpt-6.1-sol"),
    [tokens, setTokens] = useState(100000),
    [egress, setEgress] = useState(false),
    [reuseDrafts, setReuseDrafts] = useState(false);
  const [choice, setChoice] = useState(""),
    [reason, setReason] = useState(""),
    [audit, setAudit] = useState<
      { seq: number; kind: string; created: number }[]
    >([]);
  const [reviewRevision, setReviewRevision] = useState<number | null>(null);
  const [manualId, setManualId] = useState("");
  const [topUp, setTopUp] = useState(0);
  const [localRouting, setLocalRouting] = useState(false);
  const [routingProfile, setRoutingProfile] = useState<{ available: boolean; sha256?: string } | null>(null);
  const [lastExport, setLastExport] = useState<{
    batch: string;
    manifest: unknown;
  } | null>(null);
  const batch = batches.find((b) => b.id === active),
    task = tasks.find((t) => t.id === taskId);
  async function api(
    path: string,
    body?: unknown,
    method?: string,
    raw = false,
  ) {
    const response = await fetch(path, {
      method: method || (body === undefined ? "GET" : "POST"),
      headers: {
        "X-CSRF-Token": csrf,
        ...(raw
          ? { "Content-Type": "text/plain" }
          : { "Content-Type": "application/json" }),
      },
      body:
        body === undefined
          ? undefined
          : raw
            ? (body as string)
            : JSON.stringify(body),
    });
    if (!response.ok) {
      if (response.status === 401) setUser(null);
      const payload = await response
        .json()
        .catch(() => ({ detail: "Request failed" }));
      throw Error(
        typeof payload.detail === "string"
          ? payload.detail
          : "Check the input fields.",
      );
    }
    return response.json();
  }
  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function refresh() {
    const [b, f, p] = await Promise.all([api("/api/batches"), api("/api/feeds"), api("/api/routing-profile")]);
    setBatches(b);
    setFeeds(f);
    setRoutingProfile(p);
    if (active) {
      const [t, m, a] = await Promise.all([
        api(`/api/batches/${active}/tasks?offset=${offset}`),
        api(`/api/batches/${active}/analytics`),
        api(`/api/batches/${active}/audit`),
      ]);
      setTasks(t);
      setMetrics(m);
      setAudit(a);
    }
  }
  useEffect(() => {
    fetch("/api/session")
      .then((r) => (r.ok ? r.json() : null))
      .then((u) => {
        if (u) {
          setUser(u);
          setCsrf(u.csrf);
        }
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!user) return;
    let stopped = false;
    const tick = () =>
      refresh().catch((e) => {
        if (!stopped) setError(e.message);
      });
    tick();
    const timer = setInterval(tick, 2500);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [user?.name, active, offset]);
  useEffect(() => {
    setChoice(task?.review?.candidate_id || task?.result.candidate_id || "");
    setReason("");
    setReviewRevision(task?.revision ?? null);
  }, [taskId]);
  async function download() {
    const out = await api(`/api/batches/${active}/exports`, {});
    setLastExport({ batch: active, manifest: out.manifest });
    const blob = new Blob([out.csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `catalogbridge-${active.slice(0, 8)}-reviewed.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
  if (!user)
    return (
      <main className="login">
        <div className="login-story">
          <div className="wordmark">
            <Layers3 /> CatalogBridge
          </div>
          <p className="eyebrow">THE CATALOG OPERATIONS DESK</p>
          <h1>
            Right product.
            <br />
            Clear evidence.
            <br />
            <em>Controlled effort.</em>
          </h1>
          <p>
            Turn supplier lists into reviewable catalog mappings. Spend model
            effort where it matters.
          </p>
          <div className="trust">
            <ShieldCheck size={18} /> Reviewed exports. No automatic store
            writes.
          </div>
        </div>
        <form
          className="login-card"
          onSubmit={(e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            act(async () => {
              const u = await api("/api/session", {
                username: data.get("username"),
                password: data.get("password"),
              });
              setUser(u);
              setCsrf(u.csrf);
            });
          }}
        >
          <span className="eyebrow">WORKSPACE ACCESS</span>
          <h2>Welcome to your desk</h2>
          <p>Sign in with your configured service account.</p>
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
          <button disabled={busy}>
            Open workspace <ArrowRight size={16} />
          </button>
          <small>
            The service runs on your host. Model inference may leave it only
            with approved egress.
          </small>
        </form>
      </main>
    );
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="wordmark">
          <Layers3 /> CatalogBridge
        </div>
        <div className="workspace">
          CB{" "}
          <span>
            Catalog workspace<small>{user.role} access</small>
          </span>
        </div>
        <span className="nav-label">OPERATIONS</span>
        <nav>
          <button
            className={view === "workbench" ? "selected" : ""}
            onClick={() => setView("workbench")}
          >
            <Boxes size={18} /> Matching desk
          </button>
          <button
            className={view === "analytics" ? "selected" : ""}
            onClick={() => setView("analytics")}
          >
            <Wallet size={18} /> Usage & cost
          </button>
          <button
            className={view === "audit" ? "selected" : ""}
            onClick={() => setView("audit")}
          >
            <ClipboardCheck size={18} /> Activity trail
          </button>
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={22} />
          <strong>Evidence before action</strong>
          <p>
            Recommendations are not approvals. Only reviewed links enter the
            default export.
          </p>
        </div>
        <button
          className="logout"
          onClick={() =>
            act(async () => {
              await api("/api/session", {}, "DELETE");
              setUser(null);
            })
          }
        >
          <LogOut size={16} />
          {user.name} · Sign out
        </button>
      </aside>
      <main className="main">
        <header>
          <div>
            <p className="eyebrow">
              CATALOG OPERATIONS /{" "}
              {view === "analytics" ? "ANALYTICS" : "MATCHING DESK"}
            </p>
            <h1>
              {view === "analytics"
                ? "Every decision, accounted for."
                : view === "audit"
                  ? "A traceable chain of decisions."
                  : "From supplier list to verified link."}
            </h1>
            <p className="muted">
              Evidence-linked matching, explicit exceptions and a budget you can
              inspect.
            </p>
          </div>
          <button onClick={() => setSetup(!setup)} className="primary">
            <Plus size={16} /> New batch
          </button>
        </header>
        {error && (
          <div role="alert" className="error">
            {error}
            <button onClick={() => setError("")} className="text-button">
              Dismiss
            </button>
          </div>
        )}
        {setup && (
          <section className="setup card">
            <div className="section-heading">
              <h2>Prepare a matching batch</h2>
              <span className="chip">Immutable feed revisions</span>
            </div>
            <div className="setup-grid">
              <div>
                <h3>01 / Import source data</h3>
                <label>
                  Feed role
                  <select
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    <option value="master">Master catalog</option>
                    <option value="supplier">Supplier feed</option>
                  </select>
                </label>
                <label>
                  CSV or JSON
                  <input
                    type="file"
                    accept=".csv,.json"
                    onChange={(e) => {
                      const f = e.target.files?.[0] || null;
                      setFile(f);
                      if (f) f.text().then((t) => setPreview(t.slice(0, 500)));
                    }}
                  />
                </label>
                {preview && <pre className="preview">{preview}</pre>}
                <p className="muted">
                  Required fields: id, title. Optional: brand, description,
                  model, gtin, price, currency. Unknown columns are rejected.
                </p>
                <button
                  disabled={!file || busy}
                  onClick={() =>
                    act(async () => {
                      await api(
                        `/api/feeds?kind=${kind}&format=${file!.name.endsWith(".json") ? "json" : "csv"}`,
                        await file!.text(),
                        undefined,
                        true,
                      );
                      setFile(null);
                      setPreview("");
                      await refresh();
                    })
                  }
                >
                  <Upload size={16} /> Import & freeze
                </button>
              </div>
              <div>
                <h3>02 / Define the workload</h3>
                <label>
                  Master revision
                  <select
                    value={master}
                    onChange={(e) => setMaster(e.target.value)}
                  >
                    <option value="">Choose master</option>
                    {feeds
                      .filter((f) => f.kind === "master")
                      .map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.id.slice(0, 10)} · {f.hash.slice(0, 8)}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Supplier revision
                  <select
                    value={supplier}
                    onChange={(e) => setSupplier(e.target.value)}
                  >
                    <option value="">Choose supplier</option>
                    {feeds
                      .filter((f) => f.kind === "supplier")
                      .map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.id.slice(0, 10)} · {f.hash.slice(0, 8)}
                        </option>
                      ))}
                  </select>
                </label>
                <div className="two-col">
                  <label>
                    Economy model
                    <input
                      value={economy}
                      onChange={(e) => setEconomy(e.target.value)}
                    />
                  </label>
                  <label>
                    Stronger model
                    <input
                      value={strong}
                      onChange={(e) => setStrong(e.target.value)}
                    />
                  </label>
                </div>
              </div>
              <div>
                <h3>03 / Authorize the allowance</h3>
                <label>
                  Batch token allowance
                  <input
                    type="number"
                    min={1}
                    max={100000000}
                    value={tokens}
                    onChange={(e) => setTokens(Number(e.target.value))}
                  />
                </label>
                <div className="notice">
                  <CircleHelp size={18} />
                  <span>
                    Advisory token mode. CLI calls can exceed estimates. Strict
                    token enforcement is unavailable and refused.
                  </span>
                </div>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={egress}
                    onChange={(e) => setEgress(e.target.checked)}
                  />{" "}
                  I authorize these source fields to go to the configured model
                  service.
                </label>
                <p className="muted">
                  Unchecked: manual matching only. Model availability and
                  effective identity are not yet verified.
                </p>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={reuseDrafts}
                    onChange={(e) => setReuseDrafts(e.target.checked)}
                  />{" "}
                  Reuse exact-context drafts for up to 24 hours. Review is still required.
                </label>
                <label className="checkbox">
                  <input type="checkbox" checked={localRouting}
                    disabled={!routingProfile?.available}
                    onChange={(e) => setLocalRouting(e.target.checked)} />{" "}
                  Use the configured local pair scorer for qualified review drafts.
                </label>
                <p className="muted">
                  {routingProfile?.available ? "Ambiguous rows still use Codex. Local drafts are not automatic links." : "No valid local routing profile is configured."}
                </p>
                <button
                  disabled={busy || user.role !== "owner"}
                  onClick={() =>
                    act(async () => {
                      const problem = validateBatch(
                        master,
                        supplier,
                        economy,
                        strong,
                      );
                      if (problem) throw Error(problem);
                      const b = await api("/api/batches", {
                        master_id: master,
                        supplier_id: supplier,
                        token_budget: tokens,
                        economy_model: economy,
                        strong_model: strong,
                        egress,
                        reuse_validated_drafts: reuseDrafts,
                        routing_policy: localRouting && routingProfile?.available ? "local_review_v1" : "llm_only",
                        local_router_sha256: localRouting && routingProfile?.available ? routingProfile.sha256 : null,
                      });
                      await api(`/api/batches/${b.id}/start`, {});
                      setActive(b.id);
                      setOffset(0);
                      setSetup(false);
                      await refresh();
                    })
                  }
                >
                  Create & start batch <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </section>
        )}
        <div className="batch-bar">
          <label>
            ACTIVE BATCH
            <select
              aria-label="Active batch"
              value={active}
              onChange={(e) => {
                setActive(e.target.value);
                setTaskId("");
                setOffset(0);
              }}
            >
              <option value="">Select a batch</option>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.id.slice(0, 10)} · {prettyState(b.state)}
                </option>
              ))}
            </select>
          </label>
          {batch && (
            <>
              <span className="chip">{prettyState(batch.state)}</span>
              <button
                className="secondary"
                disabled={busy}
                onClick={() => act(download)}
              >
                <FileDown size={16} /> Export reviewed
              </button>
              {lastExport?.batch === active && (
                <button
                  className="secondary"
                  onClick={() => {
                    const url = URL.createObjectURL(
                      new Blob([JSON.stringify(lastExport.manifest, null, 2)], {
                        type: "application/json",
                      }),
                    );
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `catalogbridge-${active.slice(0, 8)}-coverage.json`;
                    link.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Download same-snapshot coverage
                </button>
              )}
              {batch.state === "partial" && metrics && (
                <button
                  className="secondary"
                  disabled={busy || !canContinue(batch.state, metrics)}
                  onClick={() =>
                    act(async () => {
                      await api(`/api/batches/${active}/continue`, {});
                      await refresh();
                    })
                  }
                >
                  Continue within existing allowance
                </button>
              )}
              {batch.state === "partial" && user.role === "owner" && (
                <label>
                  Additional advisory tokens (no row/call reset)
                  <input
                    type="number"
                    min="0"
                    max="100000000"
                    value={topUp}
                    onChange={(e) => setTopUp(Number(e.target.value))}
                  />
                  <button
                    disabled={busy || topUp <= 0}
                    onClick={() =>
                      act(async () => {
                        await api(`/api/batches/${active}/budget-increases`, {
                          tokens: topUp,
                        });
                        setTopUp(0);
                        await refresh();
                      })
                    }
                  >
                    Authorize budget increase
                  </button>
                </label>
              )}
              {["queued", "running"].includes(batch.state) && (
                <button
                  className="secondary"
                  onClick={() =>
                    act(async () => {
                      await api(`/api/batches/${active}/cancel`, {});
                      await refresh();
                    })
                  }
                >
                  Cancel dispatch
                </button>
              )}
            </>
          )}
        </div>
        {metrics && (
          <section className="metrics" aria-live="polite">
            <article>
              <span>INPUT ROWS</span>
              <strong>{metrics.rows.toLocaleString()}</strong>
              <small>All rows stay in the denominator</small>
            </article>
            <article>
              <span>MODEL ATTEMPTS</span>
              <strong>{metrics.attempts}</strong>
              <small>Including retries and failures</small>
            </article>
            <article>
              <span>MEASURED TOKENS</span>
              <strong>{metrics.tokens.toLocaleString()}</strong>
              <small>
                {metrics.reserved_tokens.toLocaleString()} reserved / held
              </small>
            </article>
            <article className={metrics.unknown_attempts ? "warning" : ""}>
              <span>REMAINING ADVISORY</span>
              <strong>{metrics.remaining_tokens.toLocaleString()}</strong>
              <small>
                {metrics.unknown_attempts
                  ? `${metrics.unknown_attempts} unknown usage liabilities`
                  : "Not a provider-side hard cap"}
              </small>
            </article>
          </section>
        )}
        {metrics?.runtime_circuit?.open && (
          <section className="card warning" role="alert">
            <h3>Inference paused across this workspace</h3>
            <p>
              Provider failure or unknown usage has opened the runtime circuit.
              {" "}{metrics.runtime_circuit.unknown_attempts} unknown usage liabilities remain held.
              Manual review and exports remain available. Budget increases and restarts
              do not clear this safety hold; operator investigation is required.
            </p>
          </section>
        )}
        {!active ? (
          <section className="empty card">
            <div className="empty-icon">
              <Boxes size={36} />
            </div>
            <span className="eyebrow">A CLEAN START</span>
            <h2>Your next supplier list belongs here.</h2>
            <p>
              Import a master catalog and a supplier feed, define the allowance,
              then review evidence-backed mappings.
            </p>
            <button onClick={() => setSetup(true)}>
              <Plus size={16} /> Prepare first batch
            </button>
            <small>No sample results or savings have been fabricated.</small>
          </section>
        ) : view === "analytics" ? (
          <section className="card analytics">
            <h2>Usage, without the guesswork</h2>
            <p>{metrics && budgetLabel(metrics)}</p>
            <div className="notice">
              {metrics?.cost_basis === "unpriced"
                ? "No applicable rate card. Monetary cost is unknown—not zero."
                : `Cost basis: ${metrics?.cost_basis}. Not an actual subscription invoice.`}
            </div>
            {metrics && (
              <div className="route">
                <span>Estimated total / cost per input row</span>
                <strong>
                  {formatCost(metrics.estimated_microunits, metrics.cost_unit)}{" "}
                  /{" "}
                  {formatCost(
                    metrics.cost_per_input_row_microunits,
                    metrics.cost_unit,
                  )}
                </strong>
              </div>
            )}
            <h3>Dispatches by route</h3>
            {Object.entries(metrics?.routes || {}).map(([route, n]) => (
              <div className="route" key={route}>
                <span>{route}</span>
                <strong>{n}</strong>
              </div>
            ))}
            <h3>Row coverage</h3>
            {Object.entries(metrics?.states || {}).map(([state, n]) => (
              <div className="route" key={state}>
                <span>{prettyState(state)}</span>
                <strong>{n}</strong>
              </div>
            ))}
            <p className="muted">
              No paired baseline measured. Savings and correctness-adjusted cost
              are unavailable. Reviewer acceptance is not independent ground
              truth.
            </p>
          </section>
        ) : view === "audit" ? (
          <section className="card audit">
            <h2>Batch activity</h2>
            {audit.map((a) => (
              <div className="route" key={a.seq}>
                <span>
                  #{a.seq} · {a.kind.replaceAll("_", " ")}
                </span>
                <time>{new Date(a.created * 1000).toLocaleString()}</time>
              </div>
            ))}
          </section>
        ) : (
          <section className="workbench">
            <div className="card rows-panel">
              <div className="section-heading">
                <h2>Supplier rows</h2>
                <span className="chip">{tasks.length} on this page</span>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>PRODUCT / SOURCE ID</th>
                    <th>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((t) => (
                    <tr
                      key={t.id}
                      className={taskId === t.id ? "active-row" : ""}
                    >
                      <td>
                        <button
                          className="row-link"
                          onClick={() => setTaskId(t.id)}
                        >
                          {t.source.title}
                          <small>
                            {t.source.id}{" "}
                            {t.source.brand && `· ${t.source.brand}`}
                          </small>
                        </button>
                      </td>
                      <td>
                        <span
                          className={`status ${t.review ? "reviewed" : t.state}`}
                        >
                          {t.review
                            ? `Reviewed · ${t.review.action}`
                            : prettyState(t.state)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="pagination">
                <button
                  className="secondary"
                  disabled={!offset}
                  onClick={() => {
                    setOffset(Math.max(0, offset - 50));
                    setTaskId("");
                  }}
                >
                  <ChevronLeft size={14} /> Previous
                </button>
                <span>
                  {offset + 1}–{offset + tasks.length}
                </span>
                <button
                  className="secondary"
                  disabled={tasks.length < 50}
                  onClick={() => {
                    setOffset(offset + 50);
                    setTaskId("");
                  }}
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
            <div className="card evidence-panel">
              {!task ? (
                <div className="evidence-empty">
                  <ClipboardCheck size={32} />
                  <h2>Inspect before you link.</h2>
                  <p>
                    Select a row to compare its original fields, candidate
                    products and matching evidence.
                  </p>
                </div>
              ) : (
                <>
                  <span className="eyebrow">
                    SOURCE EVIDENCE / REVISION {task.revision}
                  </span>
                  <h2>{task.source.title}</h2>
                  <div className="source-fields">
                    <strong>Supplier · {task.source.id}</strong>
                    <p>
                      {task.source.brand || "Brand not supplied"} ·{" "}
                      {task.source.model || "Model not supplied"}
                    </p>
                    <p>
                      {task.source.description || "No description supplied"}
                    </p>
                  </div>
                  <div className="notice">
                    {task.result.reason || prettyState(task.state)}
                  </div>
                  <label>
                    Master candidate
                    <select
                      value={choice}
                      onChange={(e) => setChoice(e.target.value)}
                    >
                      <option value="">Choose a candidate</option>
                      {task.result.candidates?.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.title} · {c.id}
                        </option>
                      ))}
                    </select>
                  </label>
                  {task.result.candidates
                    ?.filter((c) => c.id === choice)
                    .map((c) => (
                      <div className="source-fields" key={c.id}>
                        <strong>{c.title}</strong>
                        <p>
                          {c.brand || "Brand not supplied"} ·{" "}
                          {c.model || "Model not supplied"}
                        </p>
                        <p>{c.description || "No description supplied"}</p>
                        {!!task.result.conflicts?.[c.id]?.length && (
                          <p className="conflict">
                            Attribute conflicts:{" "}
                            {task.result.conflicts[c.id].join(", ")}
                          </p>
                        )}
                      </div>
                    ))}
                  {task.result.proposal?.evidence.map((e, i) => (
                    <blockquote key={i}>
                      <small>
                        {e.side} / {e.field}
                      </small>
                      “{e.quote}”
                    </blockquote>
                  ))}
                  <small className="muted">
                    {task.result.local_routing && <>Local pair scorer · no Codex call · benchmark draft band, review required. </>}
                    {task.result.cached_from && (
                      <>Reused draft · no new model call. Source task: {task.result.cached_from.task_id}. </>
                    )}
                    {task.result.calibrated
                      ? "Applicable acceptance calibration recorded."
                      : "No qualified automatic acceptance. Review required."}{" "}
                    Requested: {task.result.model_requested || "none"};
                    effective: {task.result.effective_model || "unverified"}.
                  </small>
                  <label>
                    Review rationale
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="What source evidence supports your decision?"
                    />
                  </label>
                  <label>
                    Candidate missed by retrieval? Look up a master ID
                    <input
                      value={manualId}
                      onChange={(e) => setManualId(e.target.value)}
                      placeholder="Exact master product ID"
                    />
                  </label>
                  <button
                    className="secondary"
                    disabled={!manualId || busy}
                    onClick={() =>
                      act(async () => {
                        const row = await api(
                          `/api/feeds/${batch!.spec.master_id}/record?id=${encodeURIComponent(manualId)}`,
                        );
                        setTasks((current) =>
                          current.map((t) =>
                            t.id === task.id
                              ? {
                                  ...t,
                                  result: {
                                    ...t.result,
                                    candidates: [
                                      ...(t.result.candidates || []).filter(
                                        (c) => c.id !== row.id,
                                      ),
                                      row,
                                    ],
                                  },
                                }
                              : t,
                          ),
                        );
                        setChoice(row.id);
                        setManualId("");
                      })
                    }
                  >
                    Inspect master record
                  </button>
                  {isReviewStale(reviewRevision, task.revision) && (
                    <div className="notice" role="alert">
                      This review context has changed. Inspect the current
                      evidence before refreshing the form.
                      <button
                        className="secondary"
                        onClick={() => {
                          setReviewRevision(task.revision);
                          setChoice(
                            task.review?.candidate_id ||
                              task.result.candidate_id ||
                              "",
                          );
                          setReason("");
                        }}
                      >
                        Refresh review context
                      </button>
                    </div>
                  )}
                  <div className="review-actions">
                    <button
                      disabled={
                        busy ||
                        !canReview(task) ||
                        isReviewStale(reviewRevision, task.revision) ||
                        !choice ||
                        !reason ||
                        !["owner", "reviewer"].includes(user.role)
                      }
                      onClick={() =>
                        act(async () => {
                          await api(`/api/tasks/${task.id}/review`, {
                            expected_revision: reviewRevision,
                            action:
                              task.result.candidate_id === choice
                                ? "accept"
                                : "correct",
                            candidate_id: choice,
                            reason,
                          });
                          setReason("");
                          await refresh();
                        })
                      }
                    >
                      Approve this link
                    </button>
                    <button
                      className="secondary"
                      disabled={
                        busy ||
                        !canReview(task) ||
                        isReviewStale(reviewRevision, task.revision) ||
                        !reason ||
                        !["owner", "reviewer"].includes(user.role)
                      }
                      onClick={() =>
                        act(async () => {
                          await api(`/api/tasks/${task.id}/review`, {
                            expected_revision: reviewRevision,
                            action: "reject",
                            reason,
                          });
                          setReason("");
                          await refresh();
                        })
                      }
                    >
                      Reject link
                    </button>
                  </div>
                  <p className="muted">
                    This records your review. It does not update a store or
                    certify product identity.
                  </p>
                </>
              )}
            </div>
          </section>
        )}
        <footer>
          <span>
            <ShieldCheck size={14} /> No automatic catalog writes
          </span>
          <span>
            Installed Codex adapter · Windows service target · Pilot acceptance
            pending
          </span>
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
