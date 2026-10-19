import React, { useState, useEffect, useCallback } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowUpRight,
  Layers,
  RefreshCw,
  ShieldCheck,
  Inbox,
  Settings,
  LogOut,
  CheckCircle2,
  AlertTriangle,
  Radio,
} from "lucide-react";
import { canReplay, counters, stateLabel, safeRunUrl } from "./domain";
import "./style.css";

type Actor = { name: string; role: string; csrf: string };
type Repo = {
  id: string;
  name: string;
  client_id: string;
  github_id: number;
  owner: string;
  issues: number;
  secret_ref: string;
  token_ref: string;
};
type Triage = {
  summary: string;
  hypothesis: string;
  confidence: number;
  next_steps: string[];
  citations: { line: number; quote: string }[];
  client_update: string;
  fallback_reason?: string;
};
type Incident = {
  id: string;
  repo_id: string;
  run_id: number;
  attempt: number;
  state: string;
  owner: string;
  source_url: string;
  triage: Triage | null;
};
type Event = {
  id: string;
  repo_id: string;
  state: string;
  attempts: number;
  error: string | null;
  due: number;
  payload: string;
};
type Snapshot = {
  clients: { id: string; name: string }[];
  repos: Repo[];
  incidents: Incident[];
  events: Event[];
  audit: {
    seq: number;
    occurred: number;
    action: string;
    detail: string;
    actor: string;
  }[];
  heartbeat: { name: string; updated: number; detail: string }[];
  queue_enabled: boolean;
};
type Detail = {
  incident_id: string;
  effect: { state: string; external_id: number | null } | null;
  payload: { workflow: string; attempt: number; source_url: string };
  checkpoint: {
    evidence?: { text: string; truncated: boolean; selection: string };
    triage?: Triage;
  };
  state: string;
  error: string | null;
};

function App() {
  const [actor, setActor] = useState<Actor | null>(null),
    [data, setData] = useState<Snapshot | null>(null),
    [tab, setTab] = useState("Response desk"),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [incident, setIncident] = useState<Incident | null>(null),
    [detail, setDetail] = useState<Detail | null>(null),
    [team, setTeam] = useState<{name:string;role:string;clients:string[]}[]>([]),
    [filter, setFilter] = useState("all");
  const api = useCallback(
    async (path: string, method = "GET", body?: unknown) => {
      const r = await fetch("/api/" + path, {
        method,
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": actor?.csrf || "",
        },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      const value = await r.json();
      if (!r.ok) {
        if (r.status === 401) {
          setActor(null);
          setData(null);
        }
        throw new Error(value.detail || "Request failed");
      }
      return value;
    },
    [actor],
  );
  const refresh = useCallback(async () => {
    if (actor) setData(await api("overview"));
  }, [actor, api]);
  useEffect(() => {
    fetch("/api/session")
      .then((r) => (r.ok ? r.json() : null))
      .then(setActor)
      .catch(() => setError("Cannot reach BuildRelay."));
  }, []);
  useEffect(() => {
    if (!actor) return;
    refresh().catch((e) => setError(e.message));
    const timer = setInterval(
      () => refresh().catch((e) => setError(e.message)),
      5000,
    );
    return () => clearInterval(timer);
  }, [actor, refresh]);
  useEffect(() => {
    if (actor?.role === "owner" && tab === "Workspace") api("users").then(setTeam).catch(e => setError(e.message));
  }, [actor, tab, api]);
  const drawerOpen = !!(incident || detail);
  useEffect(() => {
    if (!drawerOpen) return;
    const before = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>(".drawer");
    dialog?.focus();
    function keyboard(e: KeyboardEvent) {
      if (e.key === "Escape") {setIncident(null);setDetail(null);}
      if (e.key === "Tab" && dialog) {
        const items = Array.from(dialog.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input,select,[tabindex="0"]'));
        const first = items[0], last = items[items.length-1];
        if (e.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {e.preventDefault();last?.focus();}
        else if (!e.shiftKey && document.activeElement === last) {e.preventDefault();first?.focus();}
      }
    }
    document.addEventListener("keydown",keyboard);
    return () => {document.removeEventListener("keydown",keyboard);before?.focus();};
  }, [drawerOpen]);
  async function action(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operation failed");
    } finally {
      setBusy(false);
    }
  }
  const fields = (form: HTMLFormElement) =>
    Object.fromEntries(new FormData(form));
  if (!actor)
    return (
      <div className="signin">
        <div className="signin-story">
          <div className="brand">
            <Layers /> BuildRelay<span>DAY 08</span>
          </div>
          <p className="eyebrow">FROM FAILED BUILD TO OWNED RESPONSE</p>
          <h1>
            Every failure.
            <br />A clear next move.
          </h1>
          <p>
            One response desk for your clients’ builds. Grounded evidence,
            accountable ownership, and automation you can inspect.
          </p>
          <div className="promise">
            <ShieldCheck /> Durable handoffs. No autonomous deployments.
          </div>
        </div>
        <form
          className="login"
          onSubmit={(e) => {
            e.preventDefault();
            const f = fields(e.currentTarget);
            action(async () => {
              await api("session", "POST", f);
              setActor(await api("session"));
            });
          }}
        >
          <p className="eyebrow">YOUR ENGINEERING WORKSPACE</p>
          <h2>Welcome back</h2>
          <p>Sign in with your configured BuildRelay account.</p>
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
            {busy ? "Signing in…" : "Open response desk →"}
          </button>
          <small>
            AI drafts require review. Confidence is not a verified diagnosis.
          </small>
        </form>
      </div>
    );
  const counts = data
    ? counters(data.incidents, data.events)
    : { open: 0, retrying: 0, dead: 0, done: 0 };
  const repoName = (id: string) =>
    data?.repos.find((r) => r.id === id)?.name || "Repository";
  const visible = (repo: string) =>
    filter === "all" ||
    data?.repos.find((r) => r.id === repo)?.client_id === filter;
  const openDetail = (id: string) =>
    action(async () => {
      setDetail(await api("events/" + id));
      setIncident(null);
    });
  const isOwner = actor.role === "owner";
  return (
    <div className="shell">
      <aside>
        <a className="brand" href="/">
          <Layers />
          BuildRelay
        </a>
        <p className="sidebar-label">ENGINEERING OPERATIONS</p>
        <nav>
          {[
            ["Response desk", Activity],
            ["Event inbox", Inbox],
            ["Dead letters", AlertTriangle],
            ["Connections", Radio],
            ["Audit trail", ShieldCheck],
            ["Workspace", Settings],
          ].map(([label, Icon]) => {
            const I = Icon as typeof Activity;
            return (
              <button
                key={String(label)}
                className={tab === label ? "active" : ""}
                onClick={() => {
                  setTab(String(label));
                  setIncident(null);
                  setDetail(null);
                }}
              >
                <I size={18} />
                {String(label)}
                {label === "Dead letters" && counts.dead > 0 && (
                  <b>{counts.dead}</b>
                )}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="environment">
            <span className="dot" /> SELF-HOSTED WORKSPACE
          </div>
          <small>
            Installed Codex adapter
            <br />
            No direct model API in product code
          </small>
          <button
            onClick={() =>
              action(async () => {
                await api("session", "DELETE");
                setActor(null);
                setData(null);
              })
            }
          >
            <LogOut size={16} />
            {actor.name} · Sign out
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <span>/</span> {tab}
          </div>
          <div className="header-actions">
            <span className="role">{actor.role}</span>
            <button
              className="quiet"
              disabled={busy}
              onClick={() => action(refresh)}
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>
        </header>
        <section className="content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">BUILD SIGNALS → ACCOUNTABLE ACTION</p>
              <h1>{tab}</h1>
              <p>
                {tab === "Response desk"
                  ? "Keep client builds moving. Give every failure an owner and an evidence-backed next step."
                  : tab === "Dead letters"
                    ? "Processing failures are visible, inspectable, and recoverable—not silently dropped."
                    : tab === "Connections"
                      ? "Signed webhooks and durable queue events enter the same workflow."
                      : "Inspect the state behind every automated handoff."}
              </p>
            </div>
            <select
              aria-label="Filter by client"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All permitted clients</option>
              {data?.clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
          {notice && (
            <div role="status" className="notice">
              {notice}
            </div>
          )}
          <div className="metrics">
            {[
              [
                "Open incidents",
                counts.open,
                "Awaiting an engineering response",
              ],
              [
                "Retry scheduled",
                counts.retrying,
                "Transient processing failures",
              ],
              ["Dead letters", counts.dead, "Operator action required"],
              [
                "Completed workflows",
                counts.done,
                "In the latest 1,000 events",
              ],
            ].map(([label, value, sub]) => (
              <div className="metric" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
                <small>{sub}</small>
              </div>
            ))}
          </div>
          <div className="verification">
            <ShieldCheck size={17} />
            <span>
              Evidence-backed drafts, not verified fixes. Live AI acceptance and
              Windows deployment remain unverified.
            </span>
          </div>
          {!data ? (
            <div className="empty">Loading your workspace…</div>
          ) : (
            <>
              {tab === "Response desk" && (
                <div className="panel">
                  <div className="panel-heading">
                    <h2>Client build incidents</h2>
                    <span>Latest observed run state</span>
                  </div>
                  {data.incidents.filter((i) => visible(i.repo_id)).length ===
                  0 ? (
                    <Empty
                      title="No incidents yet"
                      text="Connect a repository. Completed failure events will create owned incidents here; successful builds alone won’t."
                    />
                  ) : (
                    <div className="incident-list">
                      {data.incidents
                        .filter((i) => visible(i.repo_id))
                        .map((i) => (
                          <button
                            className="incident-row"
                            key={i.id}
                            onClick={() => {
                              setIncident(i);
                              setDetail(null);
                            }}
                          >
                            <span className={"status-icon " + i.state}>
                              {i.state === "recovered" ? (
                                <CheckCircle2 />
                              ) : (
                                <Activity />
                              )}
                            </span>
                            <div>
                              <strong>
                                {i.triage?.summary || "Run state update"}
                              </strong>
                              <small>
                                {repoName(i.repo_id)} · run #{i.run_id} ·
                                attempt {i.attempt}
                              </small>
                            </div>
                            <span className={"badge " + i.state}>
                              {stateLabel(i.state)}
                            </span>
                            <span className="owner">{i.owner}</span>
                            <ArrowUpRight size={18} />
                          </button>
                        ))}
                    </div>
                  )}
                </div>
              )}
              {(tab === "Event inbox" || tab === "Dead letters") && (
                <div className="panel">
                  <div className="panel-heading">
                    <h2>
                      {tab === "Dead letters"
                        ? "Recoverable processing failures"
                        : "Durable event inbox"}
                    </h2>
                    <span>Duplicates share one canonical event</span>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Repository / run</th>
                          <th>Status</th>
                          <th>Attempts</th>
                          <th>Last error</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.events
                          .filter(
                            (e) =>
                              visible(e.repo_id) &&
                              (tab !== "Dead letters" || e.state === "dead"),
                          )
                          .map((e) => {
                            const p = JSON.parse(e.payload);
                            return (
                              <tr key={e.id}>
                                <td>
                                  <strong>{repoName(e.repo_id)}</strong>
                                  <small>
                                    Run #{p.run_id} · attempt {p.attempt}
                                  </small>
                                </td>
                                <td>
                                  <span className={"badge " + e.state}>
                                    {stateLabel(e.state)}
                                  </span>
                                </td>
                                <td>{e.attempts}</td>
                                <td>{e.error || "—"}</td>
                                <td>
                                  <button
                                    className="quiet"
                                    onClick={() => openDetail(e.id)}
                                  >
                                    Inspect
                                  </button>
                                  {canReplay(e.state, actor.role) && (
                                    <button
                                      className="quiet"
                                      disabled={busy}
                                      onClick={() => {
                                        const reason = prompt(
                                          "Explain what was fixed before replaying (at least 10 characters):",
                                        );
                                        if (reason && reason.length >= 10)
                                          action(async () => {
                                            await api(
                                              "events/" + e.id + "/replay",
                                              "POST",
                                              { reason },
                                            );
                                            setNotice(
                                              "Replay queued. Original identity and completed checkpoints are preserved.",
                                            );
                                          });
                                      }}
                                    >
                                      Replay
                                    </button>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
                  {data.events.filter(
                    (e) =>
                      visible(e.repo_id) &&
                      (tab !== "Dead letters" || e.state === "dead"),
                  ).length === 0 && (
                    <Empty
                      title={
                        tab === "Dead letters"
                          ? "No dead letters"
                          : "No accepted events"
                      }
                      text="This view shows actual persisted workflow state. No demo records are inserted."
                    />
                  )}
                </div>
              )}
              {tab === "Connections" && (
                <>
                  <div className="connection-grid">
                    <div className="panel connection">
                      <Radio />
                      <h2>GitHub webhooks</h2>
                      <p>
                        Subscribe to completed workflow runs. Configure each
                        repository’s secret on the service host.
                      </p>
                      <span className="badge">HMAC SHA-256 verified</span>
                    </div>
                    <div className="panel connection">
                      <Layers />
                      <h2>NATS JetStream</h2>
                      <p>
                        Independent durable consumer. Provision the stream and
                        scoped broker credentials before enabling.
                      </p>
                      <span className="badge">
                        {data.queue_enabled
                          ? "Configured · inspect heartbeat below"
                          : "Not configured"}
                      </span>
                    </div>
                  </div>
                  <div className="panel">
                    <div className="panel-heading">
                      <h2>Connected repositories</h2>
                      <span>Issue writes are opt-in</span>
                    </div>
                    {data.repos
                      .filter((r) => visible(r.id))
                      .map((r) => (
                        <div className="repo-card" key={r.id}>
                          <strong>{r.name}</strong>
                          <span>
                            {r.owner} ·{" "}
                            {r.issues
                              ? "GitHub issue sync enabled"
                              : "Internal incidents only"}
                          </span>
                          <code>/hooks/github/{r.id}</code>
                          {actor.role !== "viewer" && (
                            <button
                              className="quiet"
                              onClick={() =>
                                action(async () => {
                                  await api(
                                    "repos/" + r.id + "/reconcile",
                                    "POST",
                                    {
                                      reason:
                                        "Operator requested recent run reconciliation",
                                    },
                                  );
                                  setNotice(
                                    "Recent-run scan scheduled. Historical coverage is bounded; check audit for gaps.",
                                  );
                                })
                              }
                            >
                              Request recovery scan
                            </button>
                          )}
                        </div>
                      ))}
                    {data.repos.length === 0 && (
                      <Empty
                        title="Connect your first client repository"
                        text="Create a client and repository from Workspace. Tokens stay in the service environment."
                      />
                    )}
                  </div>
                  <div className="panel heartbeat">
                    <h2>Worker signals</h2>
                    {data.heartbeat.length ? (
                      data.heartbeat.map((h) => (
                        <p key={h.name}>
                          <strong>{h.name}</strong> · {h.detail} ·{" "}
                          {new Date(h.updated * 1000).toLocaleString()}
                        </p>
                      ))
                    ) : (
                      <p>
                        No worker heartbeat visible. Start the worker or ask
                        your workspace owner.
                      </p>
                    )}
                    <small>
                      A tunnel is not a durable buffer. Recovery scans have
                      explicit historical coverage limits.
                    </small>
                  </div>
                </>
              )}
              {tab === "Audit trail" && (
                <div className="panel">
                  <div className="panel-heading">
                    <h2>Workflow & operator history</h2>
                    <span>
                      Latest 1,000 application audit entries · not tamper-proof
                      storage
                    </span>
                  </div>
                  {data.audit.map((a) => (
                    <div className="audit-row" key={a.seq}>
                      <ShieldCheck size={16} />
                      <div>
                        <strong>{a.action.replaceAll("_", " ")}</strong>
                        <small>
                          {a.actor} ·{" "}
                          {new Date(a.occurred * 1000).toLocaleString()}
                        </small>
                        <code>{a.detail}</code>
                      </div>
                    </div>
                  ))}
                  {!data.audit.length && (
                    <Empty
                      title="No visible audit entries"
                      text="Accepted events, retries, validation failures, and operator actions appear here."
                    />
                  )}
                </div>
              )}
              {tab === "Workspace" &&
                (isOwner ? (
                  <div className="forms">
                    <form
                      className="panel"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const form = e.currentTarget;
                        action(async () => {
                          await api("clients", "POST", fields(form));
                          form.reset();
                          setNotice("Client created.");
                        });
                      }}
                    >
                      <h2>Create client</h2>
                      <label>
                        Client name
                        <input name="name" required maxLength={150} />
                      </label>
                      <button disabled={busy}>Create client</button>
                    </form>
                    <form
                      className="panel"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const form = e.currentTarget,
                          f = fields(form);
                        action(async () => {
                          await api("repos", "POST", {
                            ...f,
                            github_id: Number(f.github_id),
                            issues: f.issues === "on",
                          });
                          form.reset();
                          setNotice(
                            "Repository connected. Configure its webhook and environment references before use.",
                          );
                        });
                      }}
                    >
                      <h2>Connect repository</h2>
                      <label>
                        Client
                        <select name="client_id" required>
                          <option value="">Choose client</option>
                          {data.clients.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        GitHub repository
                        <input
                          name="name"
                          placeholder="agency/client-app"
                          required
                        />
                      </label>
                      <label>
                        Numeric GitHub repository ID
                        <input
                          name="github_id"
                          type="number"
                          min="1"
                          required
                        />
                      </label>
                      <label>
                        Response owner / team
                        <input name="owner" required />
                      </label>
                      <label>
                        Webhook secret environment name
                        <input
                          name="secret_ref"
                          placeholder="BUILDRELAY_SHOP_SECRET"
                          pattern="BUILDRELAY_[A-Z0-9_]+_SECRET"
                          required
                        />
                      </label>
                      <label>
                        GitHub token environment name
                        <input
                          name="token_ref"
                          placeholder="BUILDRELAY_SHOP_TOKEN"
                          pattern="BUILDRELAY_[A-Z0-9_]+_TOKEN"
                          required
                        />
                      </label>
                      <label className="check">
                        <input type="checkbox" name="issues" />
                        Enable automatic GitHub issue writes to this repository
                      </label>
                      <button disabled={busy}>Connect repository</button>
                    </form>
                    <form
                      className="panel"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const form = e.currentTarget,
                          f = fields(form),
                          selected = new FormData(form).getAll("clients");
                        action(async () => {
                          await api("users", "POST", {
                            username: f.username,
                            password: f.password,
                            role: f.role,
                            clients: selected,
                          });
                          form.reset();
                          setTeam(await api("users"));
                          setNotice(
                            "User created with the selected client grants.",
                          );
                        });
                      }}
                    >
                      <h2>Add teammate</h2>
                      <label>
                        Username
                        <input name="username" required />
                      </label>
                      <label>
                        Initial password
                        <input
                          name="password"
                          type="password"
                          minLength={12}
                          autoComplete="new-password"
                          required
                        />
                      </label>
                      <label>
                        Role
                        <select name="role">
                          <option value="viewer">Viewer</option>
                          <option value="operator">Operator</option>
                          <option value="owner">Owner · all clients</option>
                        </select>
                      </label>
                      <label>
                        Client grants
                        <select name="clients" multiple>
                          {data.clients.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button disabled={busy}>Add teammate</button>
                    </form>
                    <div className="panel"><h2>Access control</h2><p>Client grants apply immediately to existing sessions. Owners can access all clients.</p>{team.map(u=><form key={u.name+u.clients.join(',')} onSubmit={e=>{
                      e.preventDefault();const clients=new FormData(e.currentTarget).getAll('clients');
                      action(async()=>{await api(`users/${encodeURIComponent(u.name)}/grants`,'PUT',{clients});setTeam(await api('users'));setNotice('Client grants updated immediately.');});
                    }}><h3>{u.name} · {u.role}</h3>{u.role!=='owner'&&<><label>Client grants<select name="clients" multiple defaultValue={u.clients}>{data.clients.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label><button className="quiet" disabled={busy}>Save grants</button></>}
                      {u.name!==actor.name&&<button type="button" className="quiet" disabled={busy} onClick={()=>{if(confirm(`Revoke ${u.name} and all their sessions?`)) action(async()=>{await api(`users/${encodeURIComponent(u.name)}`,'DELETE');setTeam(await api('users'));setNotice('Access revoked.');});}}>Revoke access</button>}
                    </form>)}</div>
                  </div>
                ) : (
                  <Empty
                    title="Owner-managed workspace"
                    text="Only workspace owners can configure repositories, identities, and client grants."
                  />
                ))}
            </>
          )}
          {(incident || detail) && (
            <div
              className="drawer-backdrop"
              onClick={() => {
                setIncident(null);
                setDetail(null);
              }}
            >
              <section
                role="dialog"
                aria-modal="true"
                tabIndex={-1}
                aria-label="Response evidence"
                className="drawer"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  className="quiet close"
                  onClick={() => {
                    setIncident(null);
                    setDetail(null);
                  }}
                >
                  Close ×
                </button>
                {incident ? (
                  <>
                    <p className="eyebrow">ENGINEERING HANDOFF</p>
                    <h2>{repoName(incident.repo_id)}</h2>
                    <span className={"badge " + incident.state}>
                      {stateLabel(incident.state)}
                    </span>
                    <p>
                      Owner: <strong>{incident.owner}</strong> · Attempt{" "}
                      {incident.attempt}
                    </p>
                    {actor.role !== "viewer" && <button className="quiet" disabled={busy} onClick={() => {
                      const owner = prompt("Who owns the next action?", incident.owner);
                      if (!owner?.trim()) return;
                      const reason = prompt("Investigation note (at least 10 characters):");
                      if (reason && reason.length >= 10) action(async () => {
                        await api(`incidents/${incident.id}/acknowledge`, "POST", {owner, reason});
                        setIncident({...incident, owner});
                        setNotice("Ownership acknowledged and audited. Issue text updates on the next run event.");
                      });
                    }}>Acknowledge / assign response</button>}
                    <a className="quiet" href={`/api/incidents/${incident.id}/export`}>Download handoff JSON</a>
                    {safeRunUrl(incident.source_url) && (
                      <a
                        href={safeRunUrl(incident.source_url)!}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open original run ↗
                      </a>
                    )}
                    {incident.triage && (
                      <>
                        <h3>Observed failure</h3>
                        <p>{incident.triage.summary}</p>
                        <h3>Hypothesis · unverified</h3>
                        <p>{incident.triage.hypothesis}</p>
                        <small>
                          Self-assessed confidence:{" "}
                          {Math.round(incident.triage.confidence * 100)}% · not
                          calibrated
                        </small>
                        <h3>Next steps</h3>
                        <ol>
                          {incident.triage.next_steps.map((s, n) => (
                            <li key={n}>{s}</li>
                          ))}
                        </ol>
                        <h3>Captured evidence</h3>
                        {incident.triage.citations.map((c, n) => (
                          <blockquote key={n}>
                            <small>Captured evidence line {c.line}</small>
                            <code>{c.quote}</code>
                          </blockquote>
                        ))}
                        <h3>Client update · unapproved draft</h3>
                        <div className="draft">
                          {incident.triage.client_update}
                        </div>
                      </>
                    )}
                    {data?.events
                      .filter((e) => {
                        const p = JSON.parse(e.payload);
                        return (
                          e.repo_id === incident.repo_id &&
                          p.run_id === incident.run_id
                        );
                      })
                      .map((e) => (
                        <button
                          key={e.id}
                          className="quiet"
                          onClick={() => openDetail(e.id)}
                        >
                          Inspect {stateLabel(e.state)} event
                        </button>
                      ))}
                  </>
                ) : (
                  detail && (
                    <>
                      <p className="eyebrow">DURABLE EXECUTION RECORD</p>
                      <h2>{detail.payload.workflow}</h2>
                      <p>
                        {stateLabel(detail.state)} ·{" "}
                        {detail.error || "No processing error"}
                      </p>
                      <h3>Evidence coverage</h3>
                      <p>
                        {detail.checkpoint.evidence?.selection ||
                          "No evidence checkpoint yet."}
                      </p>
                      {detail.checkpoint.evidence?.truncated && (
                        <div className="error">
                          Partial log coverage. Diagnosis requires manual
                          review.
                        </div>
                      )}
                      <pre>
                        {detail.checkpoint.evidence?.text ||
                          "No captured evidence."}
                      </pre>
                      <h3>Checkpointed analysis</h3>
                      <pre>
                        {JSON.stringify(
                          detail.checkpoint.triage || {},
                          null,
                          2,
                        )}
                      </pre>
                      {detail.effect && <><h3>External issue delivery</h3><p>{detail.effect.state} · {detail.effect.external_id ? `Issue #${detail.effect.external_id}` : "No confirmed external issue ID"}</p>
                        {isOwner && ["sending", "uncertain"].includes(detail.effect.state) && !detail.effect.external_id &&
                          <button className="quiet" disabled={busy} onClick={() => {
                            if (!confirm("Only continue after checking GitHub directly and verifying that no issue was created. An incorrect confirmation can cause a duplicate.")) return;
                            const reason = prompt("Record your external verification (at least 10 characters):");
                            if (reason && reason.length >= 10) action(async () => {
                              await api(`effects/${detail.incident_id}/confirm-not-created`, "POST", {reason, confirmed_not_created: true});
                              setDetail(null);setNotice("Effect rearmed after your verification. Replay the dead letter to continue.");
                            });
                          }}>I verified no issue exists · rearm</button>}
                      </>}
                    </>
                  )
                )}
              </section>
            </div>
          )}
          <footer>
            BuildRelay / Day 08{" "}
            <span>
              Durable events. Grounded handoffs. Human-owned decisions.
            </span>
          </footer>
        </section>
      </main>
    </div>
  );
}
function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <Inbox size={30} />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
