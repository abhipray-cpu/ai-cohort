import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ShieldCheck,
  Activity,
  GitBranch,
  Radio,
  Layers,
  Bell,
  Settings,
  ArrowUpRight,
  RefreshCw,
  LogOut,
  ChevronRight,
  LockKeyhole,
  Download,
  CheckCircle2,
  Clock3,
} from "lucide-react";
import {
  type Row,
  canAct,
  canApprove,
  display,
  duration,
  tone,
  traceProfiles,
  tracePolicy,
} from "./domain";
import "./style.css";

type Data = Record<string, Row[]>;
const kinds = [
  "release",
  "environment",
  "enrollment",
  "rollout",
  "approval",
  "command",
  "incident",
  "notification",
  "window",
  "decision",
  "audit",
  "destination",
  "health",
  "registration",
  "backend",
  "trace_export",
];
const views = [
  ["Overview", Activity],
  ["Releases", Layers],
  ["Canaries", GitBranch],
  ["Incidents", Bell],
  ["Connections", Radio],
  ["Audit", ShieldCheck],
  ["Settings", Settings],
] as const;
const compact = (s: string) => (s ? s.slice(0, 12) + "…" : "—");
const when = (s: number) => (s ? new Date(s * 1000).toLocaleString() : "Never");
function Badge({ value }: { value: string }) {
  return (
    <span className={"badge " + tone(value)}>
      <i />
      {value.replaceAll("_", " ")}
    </span>
  );
}
function Json({ value }: { value: unknown }) {
  return <pre>{JSON.stringify(value, null, 2)}</pre>;
}
function App() {
  const [actor, setActor] = useState(""),
    [ready, setReady] = useState(false),
    [orgs, setOrgs] = useState<Row[]>([]),
    [tenant, setTenant] = useState(""),
    [view, setView] = useState("Overview"),
    [data, setData] = useState<Data>({}),
    [selected, setSelected] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [revision, setRevision] = useState(0),
    [metrics, setMetrics] = useState<Record<string, any>>({}),
    [metricEnv, setMetricEnv] = useState(""),
    [receipt, setReceipt] = useState<unknown>(null);
  const csrf = useRef("");
  const currentOrg = orgs.find((o) => o.id === tenant),
    role = currentOrg?.role || "observer";
  async function api(path: string, method = "GET", body?: unknown) {
    const r = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf.current,
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Request failed");
    return d;
  }
  async function refreshOrgs() {
    const o = await api("/api/orgs");
    setOrgs(o);
    setTenant((t) => (o.some((x: Row) => x.id === t) ? t : o[0]?.id || ""));
  }
  useEffect(() => {
    api("/api/session")
      .then((d) => {
        setActor(d.actor);
        csrf.current = d.csrf;
        return refreshOrgs();
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);
  useEffect(() => {
    setData({});
    setSelected("");
    setMetrics({});
    setReceipt(null);
    setMetricEnv("");
  }, [tenant]);
  useEffect(() => {
    if (!tenant || !actor) return;
    let active = true;
    const load = () =>
      Promise.all(
        kinds.map(
          async (k) => [k, await api(`/api/orgs/${tenant}/${k}`)] as const,
        ),
      )
        .then((rows) => {
          if (active) setData(Object.fromEntries(rows));
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    load();
    const timer = setInterval(load, 10000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [tenant, actor, revision]);
  const roll =
    (data.rollout || []).find((r) => r.id === selected) ||
    (data.rollout || [])[0];
  const env =
    (data.environment || []).find((r) => r.id === metricEnv) ||
    (data.environment || [])[0];
  useEffect(() => {
    if (!tenant || !env) {
      setMetrics({});
      return;
    }
    let active = true;
    api(
      `/api/orgs/${tenant}/views/metrics?application=${encodeURIComponent(env.application)}&environment=${encodeURIComponent(env.environment)}`,
    )
      .then((v) => {
        if (active) setMetrics(v);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [tenant, env?.id, revision, data.environment]);
  async function act(path: string, body?: unknown, confirm = false) {
    if (
      confirm &&
      !window.confirm(
        "Apply this exact scoped action? The server will recheck authority and revision.",
      )
    )
      return;
    setError("");
    setBusy(true);
    try {
      const result = await api(path, "POST", body);
      setReceipt(result);
      setRevision((x) => x + 1);
      return result;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function form(
    resource: string,
    fields: {
      name: string;
      label: string;
      type?: string;
      value?: string;
      options?: string[];
    }[],
    build?: (v: Record<string, string>) => unknown,
  ) {
    return (
      <form
        className="form"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = e.currentTarget;
          const v = Object.fromEntries(new FormData(f)) as Record<
            string,
            string
          >;
          try {
            const result = await act(resource, build ? build(v) : v);
            if (result) {
              f.reset();
              if (resource === "/api/orgs") await refreshOrgs();
            }
          } catch {
            setError(
              "Invalid configuration. Check the JSON and required fields.",
            );
          }
        }}
      >
        {fields.map((f) => (
          <label key={f.name}>
            {f.label}
            {f.options ? (
              <select name={f.name} defaultValue={f.value} required>
                {f.options.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            ) : f.type === "textarea" ? (
              <textarea
                name={f.name}
                defaultValue={f.value}
                required
                spellCheck={false}
              />
            ) : (
              <input
                name={f.name}
                type={f.type || "text"}
                defaultValue={f.value}
                required
                autoComplete="off"
              />
            )}
          </label>
        ))}
        <button disabled={busy} className="primary">
          Save configuration <ArrowUpRight size={14} />
        </button>
      </form>
    );
  }
  const prefix = `/api/orgs/${tenant}`;
  if (!ready)
    return (
      <div className="auth">
        <ShieldCheck size={36} />
        <p>Connecting to your release desk…</p>
      </div>
    );
  if (!actor)
    return (
      <div className="auth">
        <div className="login">
          <div className="brand">
            <ShieldCheck />
            ReleaseFence
          </div>
          <p className="eyebrow">AGENT RELEASE ASSURANCE</p>
          <h1>
            Ship changes.
            <br />
            Keep control.
          </h1>
          <p className="muted">
            Observe your agents. Contain regressions. Verify what is actually
            running.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              try {
                const d = await api(
                  "/api/session",
                  "POST",
                  Object.fromEntries(f),
                );
                csrf.current = d.csrf;
                setActor(d.actor);
                setError("");
                await refreshOrgs();
              } catch (e) {
                setError((e as Error).message);
              }
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
                required
              />
            </label>
            <button className="primary">
              Open release desk <ArrowUpRight size={16} />
            </button>
          </form>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <small>
            <LockKeyhole size={12} /> Authenticated access · No deployment on
            sign-in
          </small>
        </div>
      </div>
    );
  const active = (data.rollout || []).filter(
    (r) => !["promoted", "rollback_verified", "cancelled"].includes(r.state),
  );
  const open = (data.incident || []).filter((r) => r.state === "open");
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <ShieldCheck />
          ReleaseFence
        </div>
        <p className="eyebrow">WORKSPACE</p>
        <select
          aria-label="Organization"
          value={tenant}
          onChange={(e) => setTenant(e.target.value)}
        >
          <option value="">Select organization</option>
          {orgs.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
        <span className="role">{role} access</span>
        <nav>
          {views.map(([v, Icon]) => (
            <button
              key={v}
              className={view === v ? "current" : ""}
              onClick={() => setView(v)}
            >
              <Icon size={18} />
              {v}
              {v === "Incidents" && open.length > 0 && <em>{open.length}</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <LockKeyhole size={16} />
          <strong>Evidence before action</strong>
          <p>A deployment acknowledgement is not a verified rollback.</p>
        </div>
        <button
          className="signout"
          onClick={async () => {
            await api("/api/session/logout", "POST");
            csrf.current = "";
            setActor("");
            setData({});
            setReceipt(null);
          }}
        >
          <LogOut size={16} />
          {actor} · Sign out
        </button>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            {currentOrg?.name || "Your workspace"} <ChevronRight size={13} />
            <span>{view}</span>
          </div>
          <div className="header-actions">
            <span>
              <i className="dot" />
              Authenticated session
            </span>
            <button
              aria-label="Refresh data"
              onClick={() => setRevision((v) => v + 1)}
              disabled={busy}
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>
        <section className="content">
          <div className="page-title">
            <div>
              <p className="eyebrow">PRODUCTION AGENT OPERATIONS</p>
              <h1>
                {view === "Overview" ? "Your release control room" : view}
              </h1>
              <p className="muted">
                {view === "Overview"
                  ? "A clear view of agent health, release evidence and operational risk."
                  : "Scoped to this organization. All control actions require server-side authority."}
              </p>
            </div>
            <span className="tag">
              {new Date().toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          </div>
          {error && (
            <div className="error" role="alert">
              {error}
              <button onClick={() => setError("")}>Dismiss</button>
            </div>
          )}
          {!tenant && (
            <div className="panel empty">
              <Layers size={30} />
              <h2>Create your first organization</h2>
              <p>
                Start with a private workspace. No telemetry or deployments are
                created automatically.
              </p>
              {form("/api/orgs", [
                { name: "name", label: "Organization name" },
              ])}
            </div>
          )}
          {tenant && (
            <>
              {view === "Overview" && (
                <>
                  <div className="stats">
                    {[
                      [
                        "Registered releases",
                        (data.release || []).length,
                        Layers,
                      ],
                      ["Active rollouts", active.length, GitBranch],
                      ["Open incidents", open.length, Bell],
                      [
                        "Fresh runtimes",
                        (data.enrollment || []).filter(
                          (r) =>
                            !r.revoked &&
                            r.last_seen &&
                            Date.now() / 1000 - r.last_seen < 60,
                        ).length,
                        Radio,
                      ],
                    ].map(([label, value, Icon]) => {
                      const I = Icon as typeof Layers;
                      return (
                        <div className="stat" key={String(label)}>
                          <div>
                            <span>{String(label)}</span>
                            <I size={18} />
                          </div>
                          <strong>{String(value)}</strong>
                          <small>Current loaded page · up to 100 records</small>
                        </div>
                      );
                    })}
                  </div>
                  <div className="grid">
                    <div className="panel">
                      <div className="panel-heading">
                        <h2>Performance & spend</h2>
                        <select
                          aria-label="Metric environment"
                          value={env?.id || ""}
                          onChange={(e) => {
                            setMetricEnv(e.target.value);
                            setRevision((x) => x + 1);
                          }}
                        >
                          {(data.environment || []).map((e) => (
                            <option key={e.id} value={e.id}>
                              {e.application} / {e.environment}
                            </option>
                          ))}
                        </select>
                      </div>
                      {!Object.keys(metrics).length ? (
                        <div className="empty">
                          <Activity />
                          <h3>No measured traffic yet</h3>
                          <p>
                            Enrol a runtime and ingest lifecycle events. Missing
                            data will never appear as healthy zeroes.
                          </p>
                        </div>
                      ) : (
                        Object.entries(metrics).map(([id, m]) => (
                          <div className="metric-row" key={id}>
                            <code>{compact(id)}</code>
                            <small>
                              Retained lifecycle window · since{" "}
                              {when(m.window_from)} · last event{" "}
                              {when(m.last_event_at)}
                            </small>
                            <div className="mini-grid">
                              <span>
                                Task p95<strong>{duration(m.p95_ms)} ms</strong>
                              </span>
                              <span>
                                Success / accepted
                                <strong>
                                  {m.successful} / {m.accepted}
                                </strong>
                              </span>
                              <span>
                                Reported USD<strong>{m.known_cost}</strong>
                              </span>
                              <span>
                                Estimated USD<strong>{m.estimated_cost}</strong>
                              </span>
                              <span>
                                Unknown calls<strong>{m.unknown_calls}</strong>
                              </span>
                              <span>
                                Input / output tokens
                                <strong>
                                  {display(m.input_tokens)} /{" "}
                                  {display(m.output_tokens)}
                                </strong>
                              </span>
                              <span>
                                Cached input (subset)
                                <strong>
                                  {display(m.cached_input_tokens)}
                                </strong>
                              </span>
                              <span>
                                USD per successful task
                                <strong>{display(m.cost_per_success)}</strong>
                              </span>
                              <span>
                                Coverage
                                <strong>
                                  {m.coverage === null
                                    ? "—"
                                    : (m.coverage * 100).toFixed(1) + "%"}
                                </strong>
                              </span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                    <div className="panel">
                      <div className="panel-heading">
                        <h2>Attention required</h2>
                        <span className="tag">{open.length} open</span>
                      </div>
                      {!open.length ? (
                        <div className="empty">
                          <CheckCircle2 />
                          <h3>No open incidents in this page</h3>
                          <p>
                            This is not proof of healthy telemetry. Verify
                            connector freshness and lifecycle coverage.
                          </p>
                        </div>
                      ) : (
                        open.slice(0, 5).map((i) => (
                          <button
                            className="incident-card"
                            key={i.id}
                            onClick={() => setView("Incidents")}
                          >
                            <Bell size={16} />
                            <span>
                              <strong>{i.rule.replaceAll("_", " ")}</strong>
                              <small>
                                {i.application} / {i.environment}
                              </small>
                            </span>
                            <Badge value={i.severity} />
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="panel">
                    <div className="panel-heading">
                      <h2>Recent rollouts</h2>
                      <button onClick={() => setView("Canaries")}>
                        View all <ArrowUpRight size={14} />
                      </button>
                    </div>
                    {rolloutTable()}
                  </div>
                </>
              )}
              {view === "Releases" && (
                <div className="grid">
                  <div className="panel">
                    <h2>Immutable release registry</h2>
                    <p className="muted">
                      Code, prompt, model, tools and compatible data form one
                      release.
                    </p>
                    {(data.release || []).map((r) => (
                      <details key={r.id}>
                        <summary>
                          <code>{compact(r.id)}</code> {r.application}
                        </summary>
                        <Json value={r} />
                      </details>
                    ))}
                    {!(data.release || []).length && (
                      <p className="empty">No release bundles registered.</p>
                    )}
                  </div>
                  <div className="panel">
                    <h2>Register a release</h2>
                    {["owner", "operator"].includes(role) ? (
                      form(
                        prefix + "/release",
                        [
                          {
                            name: "manifest",
                            label: "Release manifest JSON",
                            type: "textarea",
                            value: JSON.stringify(
                              {
                                application: "support",
                                code_digest: "",
                                prompt_digest: "",
                                model_config_digest: "",
                                tools_digest: "",
                                policy_revision: "one",
                              },
                              null,
                              2,
                            ),
                          },
                        ],
                        (v) => JSON.parse(v.manifest),
                      )
                    ) : (
                      <p>Owner or release operator access required.</p>
                    )}
                  </div>
                </div>
              )}
              {view === "Canaries" && (
                <>
                  <div className="panel">{rolloutTable()}</div>
                  <div className="grid">
                    <div className="panel">
                      <h2>
                        {roll ? "Release decision desk" : "Select a rollout"}
                      </h2>
                      {roll && (
                        <>
                          <Badge value={roll.state} />
                          <div className="mini-grid">
                            <span>
                              Application<strong>{roll.application}</strong>
                            </span>
                            <span>
                              Environment<strong>{roll.environment}</strong>
                            </span>
                            <span>
                              Candidate weight<strong>{roll.stage}%</strong>
                            </span>
                            <span>
                              Revision<strong>{roll.revision}</strong>
                            </span>
                          </div>
                          <p>
                            <code>{compact(roll.stable)}</code>{" "}
                            <ChevronRight size={12} />{" "}
                            <code>{compact(roll.candidate)}</code>
                          </p>
                          <div className="actions">
                            {(["canary", "promote", "rollback"] as const).map(
                              (action) => (
                                <button
                                  className={
                                    action === "rollback" ? "danger" : "primary"
                                  }
                                  key={action}
                                  disabled={
                                    busy ||
                                    !canAct(
                                      role,
                                      roll,
                                      data.approval || [],
                                      action,
                                    )
                                  }
                                  onClick={() =>
                                    act(
                                      prefix + `/rollout/${roll.id}/control`,
                                      {
                                        action,
                                        expected_revision: roll.revision,
                                      },
                                      true,
                                    )
                                  }
                                >
                                  {action === "canary"
                                    ? "Start / expand canary"
                                    : action === "promote"
                                      ? "Promote candidate"
                                      : "Request rollback"}
                                </button>
                              ),
                            )}
                            <button
                              disabled={
                                busy ||
                                !["owner", "operator"].includes(role) ||
                                roll.state !== "canary_running"
                              }
                              onClick={() =>
                                act(prefix + `/rollout/${roll.id}/analyze`)
                              }
                            >
                              Analyze closed window
                            </button>
                            <button
                              onClick={async () => {
                                try {
                                  const value = await api(
                                    prefix + `/rollout/${roll.id}/evidence`,
                                  );
                                  const url = URL.createObjectURL(
                                    new Blob([JSON.stringify(value, null, 2)], {
                                      type: "application/json",
                                    }),
                                  );
                                  const a = document.createElement("a");
                                  a.href = url;
                                  a.download = `releasefence-${roll.id}.json`;
                                  a.click();
                                  URL.revokeObjectURL(url);
                                } catch (e) {
                                  setError((e as Error).message);
                                }
                              }}
                            >
                              <Download size={14} /> Evidence
                            </button>
                          </div>
                          <p className="notice">
                            Low samples or incomplete telemetry hold promotion.
                            Rollback is verified only after all scoped runtimes
                            and fresh probes agree; in-flight exposure stays
                            visible.
                          </p>
                          {canApprove(role, actor, roll) && (
                            <div className="approval">
                              <h3>Independent approval</h3>
                              <p>
                                Authorize the exact release pair and policy
                                until {when(roll.expires)}. Automatic action is
                                off by default.
                              </p>
                              <button
                                disabled={busy}
                                onClick={() =>
                                  act(
                                    prefix + `/rollout/${roll.id}/approve`,
                                    {
                                      expected_revision: roll.revision,
                                      actions: ["canary", "rollback"],
                                      expires: roll.expires,
                                      auto_rollback: false,
                                    },
                                    true,
                                  )
                                }
                              >
                                Approve canary + manual rollback
                              </button>
                              <button
                                disabled={busy}
                                onClick={() =>
                                  act(
                                    prefix + `/rollout/${roll.id}/approve`,
                                    {
                                      expected_revision: roll.revision,
                                      actions: ["canary", "rollback"],
                                      expires: roll.expires,
                                      auto_rollback: true,
                                    },
                                    true,
                                  )
                                }
                              >
                                Preauthorize critical-rule rollback
                              </button>
                              {roll.stage === 25 && (
                                <button
                                  disabled={busy}
                                  onClick={() =>
                                    act(
                                      prefix + `/rollout/${roll.id}/approve`,
                                      {
                                        expected_revision: roll.revision,
                                        actions: ["promote"],
                                        expires: roll.expires,
                                        auto_rollback: false,
                                      },
                                      true,
                                    )
                                  }
                                >
                                  Approve final promotion
                                </button>
                              )}
                            </div>
                          )}
                          <h3>Runtime verification</h3>
                          {(data.command || [])
                            .filter((c) => c.rollout === roll.id)
                            .map((c) => (
                              <details key={c.id}>
                                <summary>
                                  <Badge value={c.state} />{" "}
                                  {compact(c.enrollment)} ·{" "}
                                  {c.envelope.body.action}
                                </summary>
                                <Json
                                  value={{
                                    requested: c.envelope.body,
                                    observed: c.proof,
                                  }}
                                />
                              </details>
                            ))}
                          <h3>Analysis evidence</h3>
                          {(data.decision || [])
                            .filter((d) => d.rollout === roll.id)
                            .map((d) => (
                              <details key={d.id}>
                                <summary>
                                  <Badge value={d.decision} />{" "}
                                  {d.reasons.join(", ") ||
                                    "All configured bounds met"}
                                </summary>
                                <Json value={d} />
                              </details>
                            ))}
                        </>
                      )}
                    </div>
                    <div className="panel">
                      <h2>Create a bounded canary</h2>
                      <p className="muted">
                        Registered manifests and controlled connectors only.
                        Initial policy defaults are conservative; this form does
                        not grant execution authority.
                      </p>
                      {["owner", "operator"].includes(role) ? (
                        form(
                          prefix + "/rollout",
                          [
                            {
                              name: "application",
                              label: "Application",
                              value: "support",
                            },
                            {
                              name: "environment",
                              label: "Environment",
                              value: "staging",
                            },
                            { name: "stable", label: "Stable digest" },
                            { name: "candidate", label: "Candidate digest" },
                            {
                              name: "trace_profile",
                              label: "Required trace backends",
                              value: "mlflow-phoenix-v1",
                              options: traceProfiles,
                            },
                            {
                              name: "enrollments",
                              label: "Enrollment IDs (comma separated)",
                            },
                            {
                              name: "minutes",
                              label: "Authority duration (minutes)",
                              type: "number",
                              value: "60",
                            },
                          ],
                          (v) => ({
                            application: v.application,
                            environment: v.environment,
                            stable: v.stable,
                            candidate: v.candidate,
                            enrollments: v.enrollments
                              .split(",")
                              .map((x) => x.trim()),
                            policy: tracePolicy(v.trace_profile),
                            expires: Date.now() / 1000 + Number(v.minutes) * 60,
                          }),
                        )
                      ) : (
                        <p>Release operator access required.</p>
                      )}
                    </div>
                  </div>
                </>
              )}
              {view === "Incidents" && (
                <div className="grid">
                  <div className="panel">
                    <h2>Incident episodes</h2>
                    {!(data.incident || []).length && (
                      <p className="empty">No incident episodes recorded.</p>
                    )}
                    {(data.incident || []).map((i) => (
                      <details key={i.id}>
                        <summary>
                          <Badge value={i.state} />{" "}
                          {i.rule.replaceAll("_", " ")} · {i.application}
                        </summary>
                        <Json value={i} />
                        <button
                          disabled={
                            busy || !["owner", "operator"].includes(role)
                          }
                          onClick={() =>
                            act(prefix + `/incident/${i.id}/acknowledge`)
                          }
                        >
                          Acknowledge (not resolve)
                        </button>
                        {i.state === "acknowledged" &&
                          ["owner", "operator"].includes(role) &&
                          form(prefix + `/incident/${i.id}/resolve`, [
                            {
                              name: "note",
                              label:
                                "Resolution reason (fresh mitigation evidence is required)",
                            },
                          ])}
                      </details>
                    ))}
                  </div>
                  <div className="panel">
                    <h2>Notification delivery</h2>
                    <p className="muted">
                      Receiver acknowledgement and retries, not merely queued
                      alerts.
                    </p>
                    {(data.notification || []).map((n) => (
                      <details key={n.id}>
                        <summary>
                          <Badge value={n.state} /> {n.attempts.length} attempts
                        </summary>
                        <Json value={n} />
                        {n.state === "dead_letter" && (
                          <button
                            disabled={busy || role !== "owner"}
                            onClick={() =>
                              act(
                                prefix + `/notification/${n.id}/replay`,
                                {},
                                true,
                              )
                            }
                          >
                            One bounded replay
                          </button>
                        )}
                      </details>
                    ))}
                  </div>
                </div>
              )}
              {view === "Connections" && (
                <div className="grid">
                  <div className="panel">
                    <h2>Enrolled runtimes</h2>
                    <p className="notice">
                      Collector export and runtime control are separate
                      permissions. Backend trace qualification is not
                      established by an enrollment.
                    </p>
                    {(data.enrollment || []).map((e) => (
                      <details key={e.id}>
                        <summary>
                          <Badge value={e.revoked ? "revoked" : e.mode} />{" "}
                          {e.application} / {e.environment}
                        </summary>
                        <p>Last runtime evidence: {when(e.last_seen)}</p>
                        <Json value={e} />
                        <button
                          className="danger"
                          disabled={busy || role !== "owner" || e.revoked}
                          onClick={() =>
                            act(prefix + `/enrollment/${e.id}/revoke`, {}, true)
                          }
                        >
                          Revoke connector
                        </button>
                      </details>
                    ))}
                    <h3>Backend deployment contract</h3>
                    <p className="muted">
                      Instrument the customer application with the supplied
                      Python SDK or send OTLP to the authenticated ingestion
                      endpoint. The durable export worker fans out
                      privacy-filtered spans to customer-owned LangSmith and
                      Arize Phoenix endpoints and reads them back. Per-backend
                      proof appears below.
                    </p>
                  </div>
                  <div className="panel">
                    <h2>Enroll a connector</h2>
                    {role === "owner" ? (
                      form(prefix + "/enrollment", [
                        {
                          name: "application",
                          label: "Application",
                          value: "support",
                        },
                        {
                          name: "environment",
                          label: "Environment",
                          value: "staging",
                        },
                        {
                          name: "public_key",
                          label: "Customer runtime Ed25519 public key",
                        },
                        {
                          name: "mode",
                          label: "Mode: observe or controlled",
                          value: "observe",
                        },
                      ])
                    ) : (
                      <p>Owner access required.</p>
                    )}
                    <h3>Notification destination</h3>
                    {role === "owner" &&
                      form(prefix + "/destination", [
                        {
                          name: "url",
                          label: "Approved HTTPS webhook URL",
                          type: "url",
                        },
                        {
                          name: "secret",
                          label: "Signing secret (at least 24 characters)",
                          type: "password",
                        },
                      ])}
                  </div>
                </div>
              )}
              {view === "Audit" && (
                <div className="panel">
                  <div className="panel-heading">
                    <h2>Decision & authority trail</h2>
                    <span className="tag">Latest 100 · immutable events</span>
                  </div>
                  {(data.audit || []).map((a) => (
                    <details key={a.id}>
                      <summary>
                        <Clock3 size={14} />
                        <time>{when(a.at)}</time>
                        <strong>{a.event.replaceAll("_", " ")}</strong>
                        <span className="muted">{a.actor}</span>
                      </summary>
                      <Json value={a} />
                    </details>
                  ))}
                </div>
              )}
              {view === "Settings" && (
                <div className="grid">
                  <div className="panel">
                    <h2>Register an environment</h2>
                    {role === "owner" &&
                      form(prefix + "/environment", [
                        {
                          name: "application",
                          label: "Application",
                          value: "support",
                        },
                        {
                          name: "environment",
                          label: "Environment",
                          value: "staging",
                        },
                        {
                          name: "stable",
                          label: "Registered stable release digest",
                        },
                      ])}
                    <h3>Organization membership</h3>
                    {role === "owner" &&
                      form(prefix + "/members", [
                        { name: "username", label: "Existing username" },
                        {
                          name: "role",
                          label: "Role: owner / operator / approver / observer",
                          value: "observer",
                        },
                      ])}
                    <h3>Platform user provisioning</h3>
                    <p className="muted">
                      Only the configured platform administrator can provision
                      accounts.
                    </p>
                    {form("/api/users", [
                      { name: "username", label: "New username" },
                      {
                        name: "password",
                        label: "Strong initial password",
                        type: "password",
                      },
                    ])}
                  </div>
                  <div className="panel">
                    <h2>New organization</h2>
                    {form("/api/orgs", [
                      { name: "name", label: "Organization name" },
                    ])}
                    <h3>Operating boundaries</h3>
                    <p className="notice">
                      No raw prompts or secrets in default telemetry. No
                      implicit rollback rights. No automatic model calls on
                      startup. A running UI is not deployment or security
                      acceptance.
                    </p>
                  </div>
                </div>
              )}
              {view === "Connections" && (
                <div className="grid">
                  <div className="panel">
                    <h2>Customer-owned trace backends</h2>
                    <p className="notice">
                      Export success is not verification. The worker reads back
                      exact trace, span, parent and release identities. A proof
                      covers only its listed spans and time, not all future
                      traffic.
                    </p>
                    {(data.backend || []).map((b) => (
                      <details key={b.id}>
                        <summary>
                          {b.kind} · {b.project} <Badge value={b.status} />
                        </summary>
                        <Json value={b.proof} />
                        <button
                          disabled={busy || role !== "owner"}
                          onClick={() =>
                            act(
                              prefix + `/connection/backend/${b.id}/state`,
                              { enabled: !b.enabled },
                              true,
                            )
                          }
                        >
                          {b.enabled
                            ? "Disable destination"
                            : "Enable destination"}
                        </button>
                      </details>
                    ))}
                    {!(data.backend || []).length && (
                      <p>
                        No backend enrolled. Live integration qualification is
                        pending.
                      </p>
                    )}
                    <h3>Trace delivery</h3>
                    {(data.trace_export || []).map((e) => (
                      <details key={e.id}>
                        <summary>
                          <Badge value={e.state} /> {e.attempts} attempts
                        </summary>
                        <Json value={e} />
                        {e.state === "dead_letter" && !e.replayed && (
                          <button
                            disabled={busy || role !== "owner"}
                            onClick={() =>
                              act(
                                prefix + `/trace_export/${e.id}/replay`,
                                {},
                                true,
                              )
                            }
                          >
                            One bounded trace replay
                          </button>
                        )}
                      </details>
                    ))}
                  </div>
                  <div className="panel">
                    <h2>Enroll trace destination</h2>
                    {role === "owner" &&
                      form(prefix + "/backend", [
                        {
                          name: "kind",
                          label: "Trace backend",
                          value: "phoenix",
                          options: ["mlflow", "phoenix", "langsmith"],
                        },
                        {
                          name: "export_url",
                          label: "Authorized OTLP HTTP traces URL",
                          type: "url",
                        },
                        {
                          name: "read_url",
                          label: "Backend API base URL",
                          type: "url",
                        },
                        {
                          name: "secret",
                          label: "Scoped API key (MLflow: username:password)",
                          type: "password",
                        },
                        { name: "project", label: "Project name / identifier" },
                      ])}
                  </div>
                </div>
              )}
              {view === "Connections" && role === "owner" && (
                <div className="panel">
                  <h2>CI release registration</h2>
                  <p className="muted">
                    A one-hour application-scoped token can register manifests,
                    but cannot observe or control runtimes. Copy its receipt
                    once and store it in your CI secret store.
                  </p>
                  {form(
                    prefix + "/registration",
                    [
                      {
                        name: "application",
                        label: "Application",
                        value: "support",
                      },
                      {
                        name: "environment",
                        label: "Environment",
                        value: "staging",
                      },
                    ],
                    (v) => ({ ...v, expires: Date.now() / 1000 + 3600 }),
                  )}
                </div>
              )}
              {view === "Connections" && role === "owner" && (
                <div className="panel">
                  <h2>CI credential scopes</h2>
                  {(data.registration || []).map((r) => (
                    <details key={r.id}>
                      <summary>
                        <Badge
                          value={
                            r.revoked
                              ? "revoked"
                              : r.expires < Date.now() / 1000
                                ? "expired"
                                : "active"
                          }
                        />
                        {r.application} / {r.environment}
                      </summary>
                      <Json value={r} />
                      <button
                        disabled={busy || r.revoked}
                        onClick={() =>
                          act(prefix + `/registration/${r.id}/revoke`, {}, true)
                        }
                      >
                        Revoke CI grant
                      </button>
                    </details>
                  ))}
                </div>
              )}
              {view === "Canaries" &&
                roll &&
                ["owner", "operator"].includes(role) && (
                  <div className="panel">
                    <h2>Recovery desk</h2>
                    <p className="notice">
                      Cancelling is allowed only before routing starts. Recovery
                      requires fresh signed post-expiry runtime evidence,
                      invalidates previous approvals and permits only a newly
                      approved rollback.
                    </p>
                    <button
                      disabled={busy || roll.state !== "ready"}
                      onClick={() =>
                        act(
                          prefix + `/rollout/${roll.id}/cancel`,
                          { expected_revision: roll.revision },
                          true,
                        )
                      }
                    >
                      Cancel unstarted rollout
                    </button>
                    <button
                      disabled={
                        busy ||
                        role !== "owner" ||
                        [
                          "ready",
                          "promoted",
                          "rollback_verified",
                          "cancelled",
                        ].includes(roll.state)
                      }
                      onClick={() =>
                        act(
                          prefix + `/rollout/${roll.id}/recover`,
                          { expires: Date.now() / 1000 + 3600 },
                          true,
                        )
                      }
                    >
                      Reconcile expired command for rollback
                    </button>
                  </div>
                )}
              {receipt !== null && (
                <details className="panel receipt" open>
                  <summary>
                    Latest operation receipt · copy enrollment credentials now,
                    if present
                  </summary>
                  <Json value={receipt} />
                  <button onClick={() => setReceipt(null)}>
                    Clear from this view
                  </button>
                </details>
              )}
            </>
          )}
          <footer>
            <ShieldCheck size={14} /> Evidence-based operations{" "}
            <span>Observe → compare → authorize → verify</span>
          </footer>
        </section>
      </main>
    </div>
  );
  function rolloutTable() {
    return !(data.rollout || []).length ? (
      <div className="empty">
        <GitBranch />
        <h3>No rollouts registered</h3>
        <p>
          Connect a runtime and register two immutable release bundles to start.
        </p>
      </div>
    ) : (
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Application / environment</th>
              <th>Candidate</th>
              <th>Traffic</th>
              <th>State</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(data.rollout || []).map((r) => (
              <tr key={r.id}>
                <td>
                  <strong>{r.application}</strong>
                  <small>{r.environment}</small>
                </td>
                <td>
                  <code>{compact(r.candidate)}</code>
                </td>
                <td>{r.stage}%</td>
                <td>
                  <Badge value={r.state} />
                </td>
                <td>
                  <button
                    aria-label={"Inspect rollout " + r.id}
                    onClick={() => {
                      setSelected(r.id);
                      setView("Canaries");
                    }}
                  >
                    <ArrowUpRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
