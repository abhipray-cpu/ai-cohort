import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  Check,
  FileCheck2,
  Layers3,
  Leaf,
  LogOut,
  RefreshCw,
  ShieldCheck,
  Upload,
} from "lucide-react";
import {
  canReview,
  codepointSlice,
  diffText,
  selectedVersion,
  usageLabel,
  type Version,
} from "./domain";
import "./style.css";

type Workspace = { id: string; name: string; role: string };
type Summary = {
  id: string;
  state: string;
  calls: number;
  name?: string;
  brand?: string;
  product_id?: string;
  batch_id?: string | null;
};
type Finding = {
  family: string;
  severity: string;
  explanation: string;
  quote?: string;
  rule?: string;
  field?: "title" | "description";
  start?: number | null;
  end?: number | null;
};
type Evaluation = {
  draft_hash: string;
  version_index: number;
  score: number | null;
  checks: Finding[];
  evaluation: {
    ratings: Record<string, { value: number | null; rationale: string }>;
    findings: Finding[];
  };
};
type Task = Summary & {
  workspace: string;
  maker: string;
  selected_hash: string | null;
  selected_revision: number;
  selected_artifact_hash: string | null;
  versions: Version[];
  facts: Record<string, string>;
  evaluations: Evaluation[];
  plans: unknown[];
  warnings: { code: string }[];
  metrics: unknown[];
  attempts: {
    stage: string;
    status: string;
    receipt: {
      input_tokens: number | null;
      output_tokens: number | null;
    } | null;
  }[];
};
const paths = [
  "product_id",
  "brand",
  "name",
  "net_quantity",
  "net_unit",
  "ingredients",
  "source_ref",
];

function App() {
  const [actor, setActor] = useState(""),
    [csrf, setCsrf] = useState(""),
    [ready, setReady] = useState(false);
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]),
    [workspace, setWorkspace] = useState("");
  const [tab, setTab] = useState("queue"),
    [tasks, setTasks] = useState<Summary[]>([]),
    [task, setTask] = useState<Task | null>(null);
  const [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState<{
      columns: string[];
      row_count: number;
      sample: unknown;
    } | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({}),
    [importId, setImportId] = useState(""),
    [grant, setGrant] = useState("");
  const [count, setCount] = useState(1),
    [original, setOriginal] = useState(""),
    [reason, setReason] = useState(""),
    [audit, setAudit] = useState<unknown>(null);
  const [health, setHealth] = useState(false);
  const [savedImports, setSavedImports] = useState<
    { id: string; rows: number; fact_hash: string }[]
  >([]);
  const [savedBatches, setSavedBatches] = useState<
    {
      id: string;
      source_id: string;
      state: string;
      total_rows: number;
      calls: number;
      unknown_attempts: number;
      counts: Record<string, number>;
      tasks: Summary[];
    }[]
  >([]);
  const [erasure, setErasure] = useState<{
    source: string;
    binding: string;
    tasks: string[];
    limits: string;
  } | null>(null);
  const [search, setSearch] = useState(""),
    [stateFilter, setStateFilter] = useState("all");
  const [brief, setBrief] = useState("Neutral factual copy.");
  const [rights, setRights] = useState<
    {
      id: string;
      expires: number;
      calls: number;
      max_calls: number;
      egress: number;
    }[]
  >([]);
  const [inspectedRevision, setInspectedRevision] = useState<number | null>(
    null,
  );
  const [highlight, setHighlight] = useState<{
    hash: string;
    field: string;
    start: number;
    end: number;
    quote: string;
  } | null>(null);
  const workspaceRef = useRef(workspace);
  workspaceRef.current = workspace;
  const [egress, setEgress] = useState<{
    id: string;
    binding: string;
    maximum_calls: number;
    grant_remaining: number;
    facts: unknown;
  } | null>(null);
  const [unknownAcknowledged, setUnknownAcknowledged] = useState(false);
  const [editTitle, setEditTitle] = useState(""),
    [editDescription, setEditDescription] = useState(""),
    [editGrant, setEditGrant] = useState("");
  async function api(path: string, options: RequestInit = {}) {
    const headers = new Headers(options.headers);
    if (options.body && !(options.body instanceof FormData))
      headers.set("Content-Type", "application/json");
    headers.set("X-CSRF-Token", csrf);
    if (
      options.method &&
      options.method !== "GET" &&
      !headers.has("Idempotency-Key")
    )
      headers.set("Idempotency-Key", crypto.randomUUID());
    const response = await fetch(path, {
      ...options,
      headers,
      credentials: "same-origin",
    });
    const value = await response.json();
    if (!response.ok) {
      if (response.status === 401) setActor("");
      const detail =
        typeof value.detail === "string"
          ? value.detail
          : JSON.stringify(
              value.detail ?? `Request failed (${response.status})`,
            );
      const issues = Array.isArray(value.issues)
        ? value.issues
            .map(
              (issue: { row: number; field: string; code: string }) =>
                `Row ${issue.row}, ${issue.field}: ${issue.code}`,
            )
            .join("; ")
        : "";
      throw new Error(`${detail}${issues ? ": " + issues : ""}`);
    }
    return value;
  }
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  async function loadWorkspaces() {
    const result = await api("/api/workspaces");
    setWorkspaces(result);
    if (!workspace && result.length) setWorkspace(result[0].id);
  }
  async function refresh() {
    if (!workspace) return;
    const requestedWorkspace = workspace;
    const [results, imports, batches] = await Promise.all([
      api(`/api/workspaces/${workspace}/tasks`),
      api(`/api/workspaces/${workspace}/imports`),
      api(`/api/workspaces/${workspace}/batches`),
    ]);
    if (requestedWorkspace !== workspaceRef.current) return;
    setTasks(results);
    setSavedImports(imports);
    setSavedBatches(batches);
    if (task && task.workspace === workspace) {
      const result = await api(`/api/tasks/${task.id}`);
      if (requestedWorkspace === workspaceRef.current) setTask(result);
    }
  }
  useEffect(() => {
    fetch("/api/me")
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => {
        if (me) {
          setActor(me.actor);
          setCsrf(me.csrf);
        }
      })
      .finally(() => setReady(true));
  }, []);
  useEffect(() => {
    if (actor) action(loadWorkspaces);
  }, [actor]);
  useEffect(() => {
    setTask(null);
    setAudit(null);
    setImportId("");
    setGrant("");
    setFile(null);
    setPreview(null);
    setMapping({});
    setEgress(null);
    setOriginal("");
    setInspectedRevision(null);
    setHighlight(null);
    if (workspace)
      action(async () => {
        const [rows, imports, batches, policy, grantRows] = await Promise.all([
          api(`/api/workspaces/${workspace}/tasks`),
          api(`/api/workspaces/${workspace}/imports`),
          api(`/api/workspaces/${workspace}/batches`),
          api(`/api/workspaces/${workspace}/policy`),
          api(`/api/workspaces/${workspace}/rights`),
        ]);
        if (workspace !== workspaceRef.current) return;
        setTasks(rows);
        setSavedImports(imports);
        setSavedBatches(batches);
        setErasure(null);
        setBrief(policy.body.brief);
        setRights(grantRows);
      });
  }, [workspace]);
  useEffect(() => {
    if (!actor) return;
    const tick = setInterval(() => {
      refresh().catch(() => {});
      fetch("/health/ready")
        .then((r) => setHealth(r.ok))
        .catch(() => setHealth(false));
    }, 3000);
    return () => clearInterval(tick);
  }, [actor, workspace, task?.id]);
  function download(value: unknown) {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "shelfproof-partial-patch.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  if (!ready)
    return (
      <main>
        <p>Opening review desk…</p>
      </main>
    );
  if (!actor)
    return (
      <div className="login">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            action(async () => {
              const me = await api("/api/session", {
                method: "POST",
                body: JSON.stringify({
                  username: data.get("username"),
                  password: data.get("password"),
                }),
              });
              setActor(me.actor);
              setCsrf(me.csrf);
            });
          }}
        >
          <div className="brand">
            <Leaf /> ShelfProof<span>REVIEW DESK</span>
          </div>
          <h1>
            Better listings.
            <br />
            Evidence first.
          </h1>
          <p>
            Generate, critique and repair product copy against an approved
            source snapshot.
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
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button disabled={busy}>
            Open workspace <ArrowRight size={16} />
          </button>
          <small>
            Private installed-Codex service · No automatic publishing
          </small>
        </form>
      </div>
    );
  const selected = task ? selectedVersion(task) : undefined;
  const selectedEval = task?.evaluations.find(
    (e) => e.version_index === (inspectedRevision ?? task.selected_revision),
  );
  function highlighted(text: string, field: string, hash: string) {
    if (
      !highlight ||
      highlight.hash !== hash ||
      highlight.field !== field ||
      codepointSlice(text, highlight.start, highlight.end) !== highlight.quote
    )
      return text;
    return (
      <>
        {codepointSlice(text, 0, highlight.start)}
        <mark>{highlight.quote}</mark>
        {codepointSlice(text, highlight.end, Array.from(text).length)}
      </>
    );
  }
  function difference(before: string, after: string) {
    const diff = diffText(before, after);
    return (
      <span>
        {diff.prefix}
        {diff.removed && <del aria-label="Removed text">{diff.removed}</del>}
        {diff.added && <ins aria-label="Added text">{diff.added}</ins>}
        {diff.suffix}
      </span>
    );
  }
  const currentWorkspace = workspaces.find((w) => w.id === workspace);
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <Leaf /> ShelfProof
        </div>
        <p className="eyebrow">CONTENT OPERATIONS</p>
        <label className="workspace">
          Workspace
          <select
            value={workspace}
            onChange={(e) => setWorkspace(e.target.value)}
          >
            <option value="">Choose workspace</option>
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        <nav>
          {[
            ["queue", "Review queue", FileCheck2],
            ["source", "Source intake", Upload],
            ["settings", "Authority & team", ShieldCheck],
          ].map(([id, label, Icon]) => (
            <button
              key={id as string}
              className={tab === id ? "active" : "ghost"}
              onClick={() => setTab(id as string)}
            >
              {React.createElement(Icon as typeof Leaf, { size: 18 })}
              {label as string}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className={`dot ${health ? "on" : ""}`} />
          {health ? "Worker ready" : "Worker unavailable / held"}
          <small>
            {actor} · {currentWorkspace?.role ?? "No workspace"}
          </small>
          <button
            className="ghost"
            onClick={() =>
              action(async () => {
                await api("/api/session", { method: "DELETE" });
                setActor("");
                setTask(null);
                setWorkspaces([]);
                setWorkspace("");
              })
            }
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">
              SHELFPROOF /{" "}
              {tab === "queue"
                ? "WORKBENCH"
                : tab === "source"
                  ? "SOURCE INTAKE"
                  : "WORKSPACE CONTROLS"}
            </p>
            <h1>
              {tab === "queue"
                ? "Every revision, accountable."
                : tab === "source"
                  ? "Start with approved facts."
                  : "Authority before automation."}
            </h1>
            <p className="muted">
              Packaged food & beverage · English / US · Partial text patches
              only
            </p>
          </div>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => action(refresh)}
          >
            <RefreshCw size={15} />
            Refresh
          </button>
        </header>
        {error && (
          <div role="alert" className="banner error">
            {error}
          </div>
        )}
        {notice && (
          <div role="status" className="banner">
            {notice}
          </div>
        )}
        <div className="safety">
          <ShieldCheck size={17} />
          <span>
            Source fidelity is not package verification. A judge score is not
            factual accuracy or regulatory certification.
          </span>
        </div>
        {tab === "settings" && (
          <div className="settings-grid">
            <section>
              <p className="eyebrow">01 / WORKSPACE</p>
              <h2>Create a client workspace</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const data = new FormData(e.currentTarget);
                  action(async () => {
                    const result = await api("/api/workspaces", {
                      method: "POST",
                      body: JSON.stringify({ name: data.get("name") }),
                    });
                    await loadWorkspaces();
                    setWorkspace(result.id);
                    setNotice("Workspace created.");
                  });
                }}
              >
                <label>
                  Name
                  <input name="name" required maxLength={150} />
                </label>
                <button disabled={busy}>Create workspace</button>
              </form>
            </section>
            <section>
              <p className="eyebrow">02 / FINITE AUTHORIZATION</p>
              {!!rights.length && (
                <details>
                  <summary>
                    Existing grants · spent allowances are retained
                  </summary>
                  {rights.map((right) => (
                    <article className="version" key={right.id}>
                      <small className="hash">{right.id}</small>
                      <p>
                        {right.calls} / {right.max_calls} calls · Expires{" "}
                        {new Date(right.expires * 1000).toLocaleString()}
                      </p>
                      <button
                        className="secondary"
                        disabled={
                          !right.egress || right.expires <= Date.now() / 1000
                        }
                        onClick={() => {
                          setGrant(right.id);
                          setEgress(null);
                          setTab("source");
                        }}
                      >
                        Use existing grant ID
                      </button>
                    </article>
                  ))}
                </details>
              )}
              <h2>Approve source use & model egress</h2>
              <p>
                Calls run through installed Codex and may transmit data to its
                configured service. This is not offline inference. Allowances
                include failures and retries.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const data = new FormData(e.currentTarget);
                  action(async () => {
                    const result = await api(
                      `/api/workspaces/${workspace}/rights`,
                      {
                        method: "POST",
                        body: JSON.stringify({
                          basis: data.get("basis"),
                          expires:
                            Date.now() / 1000 +
                            Number(data.get("minutes")) * 60,
                          max_calls: Number(data.get("calls")),
                          egress: true,
                        }),
                      },
                    );
                    setGrant(result.id);
                    setNotice(
                      `Authorization created: ${result.id}. Copy this ID for a later session.`,
                    );
                  });
                }}
              >
                <label>
                  Authority / source reference
                  <textarea name="basis" required maxLength={2000} />
                </label>
                <div className="two">
                  <label>
                    Cumulative calls
                    <input
                      type="number"
                      name="calls"
                      min="1"
                      max="100000"
                      defaultValue="16"
                      required
                    />
                  </label>
                  <label>
                    Expires in minutes
                    <input
                      type="number"
                      name="minutes"
                      min="1"
                      max="525600"
                      defaultValue="60"
                      required
                    />
                  </label>
                </div>
                <label className="check">
                  <input type="checkbox" required />I authorize these facts to
                  be processed and transmitted through the installed Codex
                  service.
                </label>
                <button
                  disabled={
                    busy || !workspace || currentWorkspace?.role !== "owner"
                  }
                >
                  Create authorization
                </button>
              </form>
            </section>
            <section>
              <p className="eyebrow">03 / INDEPENDENT REVIEW</p>
              <h2>Add an existing user</h2>
              <p>
                The service administrator must create the account first. The
                maker cannot approve their own task, including workspace owners.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const data = new FormData(e.currentTarget);
                  action(async () => {
                    await api(`/api/workspaces/${workspace}/members`, {
                      method: "POST",
                      body: JSON.stringify({
                        username: data.get("username"),
                        role: data.get("role"),
                      }),
                    });
                    setNotice("Membership updated.");
                  });
                }}
              >
                <label>
                  Username
                  <input name="username" required />
                </label>
                <label>
                  Role
                  <select name="role">
                    <option>reviewer</option>
                    <option>editor</option>
                    <option>viewer</option>
                    <option>owner</option>
                  </select>
                </label>
                <button
                  disabled={
                    busy || !workspace || currentWorkspace?.role !== "owner"
                  }
                >
                  Add member
                </button>
              </form>
            </section>
            <section>
              <p className="eyebrow">04 / SERVICE ADMINISTRATOR</p>
              <h2>Create a user</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const data = new FormData(e.currentTarget);
                  action(async () => {
                    await api("/api/users", {
                      method: "POST",
                      body: JSON.stringify({
                        username: data.get("username"),
                        password: data.get("password"),
                      }),
                    });
                    e.currentTarget?.reset();
                    setNotice("User created. Add them to a workspace.");
                  });
                }}
              >
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
                    required
                    autoComplete="new-password"
                  />
                </label>
                <button disabled={busy}>Create user</button>
              </form>
            </section>
            <section>
              <p className="eyebrow">05 / FROZEN BRAND BRIEF</p>
              <h2>Activate a new policy revision</h2>
              <p>
                The channel, hard gates and five-dimension rubric cannot be
                weakened. Activating a brief stales existing tasks and
                approvals.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  action(async () => {
                    await api(`/api/workspaces/${workspace}/policy`, {
                      method: "POST",
                      body: JSON.stringify({ brief }),
                    });
                    await refresh();
                    setNotice(
                      "Brief revision activated. Existing tasks and approvals are stale.",
                    );
                  });
                }}
              >
                <label>
                  Brand-tone instructions
                  <textarea
                    value={brief}
                    onChange={(e) => setBrief(e.target.value)}
                    maxLength={2000}
                    required
                  />
                </label>
                <label className="check">
                  <input type="checkbox" required />I acknowledge that existing
                  results and approvals will be invalidated.
                </label>
                <button
                  disabled={
                    busy || !workspace || currentWorkspace?.role !== "owner"
                  }
                >
                  Activate brief & invalidate old context
                </button>
              </form>
            </section>
          </div>
        )}
        {tab === "source" && (
          <div className="intake">
            {!!savedImports.length && (
              <section>
                <p className="eyebrow">SAVED SOURCE SNAPSHOTS · LATEST 50</p>
                <h2>Continue an existing import</h2>
                {savedImports.map((source) => (
                  <article className="version" key={source.id}>
                    <strong>
                      {source.id.slice(0, 10)} · {source.rows} rows
                    </strong>
                    <small className="hash">{source.fact_hash}</small>
                    <div className="actions">
                      <button
                        className="secondary"
                        onClick={() => {
                          setImportId(source.id);
                          setFile(null);
                          setPreview({
                            columns: [],
                            row_count: source.rows,
                            sample: null,
                          });
                          setEgress(null);
                        }}
                      >
                        Use frozen source
                      </button>
                      <button
                        className="secondary"
                        disabled={busy || currentWorkspace?.role !== "owner"}
                        onClick={() =>
                          action(async () =>
                            setErasure(
                              await api(
                                `/api/imports/${source.id}/erasure-preview`,
                              ),
                            ),
                          )
                        }
                      >
                        Preview erasure
                      </button>
                    </div>
                  </article>
                ))}
                {erasure && (
                  <div className="banner error">
                    <p>
                      Erase source {erasure.source.slice(0, 10)} and{" "}
                      {erasure.tasks.length} dependent tasks? Active results
                      will be fenced.
                    </p>
                    <p>{erasure.limits}</p>
                    <button
                      disabled={busy}
                      onClick={() =>
                        action(async () => {
                          await api(`/api/imports/${erasure.source}/erase`, {
                            method: "POST",
                            body: JSON.stringify({ binding: erasure.binding }),
                          });
                          if (importId === erasure.source) setImportId("");
                          setErasure(null);
                          await refresh();
                          setNotice(
                            "Source and derived content logically erased. Independently expire backups and external downloads.",
                          );
                        })
                      }
                    >
                      Confirm source-content erasure
                    </button>
                  </div>
                )}
              </section>
            )}
            <section>
              <p className="eyebrow">01 / PREVIEW</p>
              <h2>Upload a fact snapshot</h2>
              <p>
                UTF-8 CSV or flat JSON array · 25 MiB / 1,000 rows. Quantities
                and product IDs must be literal strings. No automatic mapping.
              </p>
              <label className="upload">
                <Upload />
                <span>{file?.name ?? "Choose CSV or JSON"}</span>
                <input
                  type="file"
                  accept=".csv,.json"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] ?? null);
                    setPreview(null);
                    setImportId("");
                    setMapping({});
                    setEgress(null);
                  }}
                />
              </label>
              <button
                disabled={!file || !workspace || busy}
                onClick={() =>
                  action(async () => {
                    const data = new FormData();
                    data.append("file", file!);
                    setPreview(
                      await api(
                        `/api/workspaces/${workspace}/imports/preview`,
                        { method: "POST", body: data },
                      ),
                    );
                  })
                }
              >
                Preview source
              </button>
              {preview && (
                <>
                  <p>{preview.row_count} rows · Mapping not yet approved</p>
                  <details>
                    <summary>Source sample (unapproved)</summary>
                    <pre>{JSON.stringify(preview.sample, null, 2)}</pre>
                  </details>
                </>
              )}
            </section>
            {preview && file && (
              <section>
                <p className="eyebrow">02 / MAP & FREEZE</p>
                <h2>Confirm every required field</h2>
                <p>
                  Brand is not brand owner. Quantity is the net package size,
                  not serving size. Ingredients must retain their original
                  order.
                </p>
                {paths.map((path) => (
                  <label key={path}>
                    {path.replaceAll("_", " ")}
                    <select
                      value={mapping[path] ?? ""}
                      onChange={(e) => {
                        setMapping({ ...mapping, [path]: e.target.value });
                        setImportId("");
                        setEgress(null);
                      }}
                    >
                      <option value="">Choose source column…</option>
                      {preview.columns.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                ))}
                <button
                  disabled={busy || paths.some((p) => !mapping[p])}
                  onClick={() =>
                    action(async () => {
                      const data = new FormData();
                      data.append("file", file!);
                      data.append("mapping", JSON.stringify(mapping));
                      const result = await api(
                        `/api/workspaces/${workspace}/imports`,
                        { method: "POST", body: data },
                      );
                      setImportId(result.id);
                      setNotice(
                        `Frozen ${result.row_count} source rows. Hash: ${result.fact_hash}`,
                      );
                    })
                  }
                >
                  Approve mapping & freeze
                </button>
              </section>
            )}
            {importId && (
              <section>
                <p className="eyebrow">03 / EXPLICIT EXECUTION</p>
                <h2>Start a bounded run</h2>
                <label>
                  Source/egress authorization ID
                  <input
                    value={grant}
                    onChange={(e) => {
                      setGrant(e.target.value);
                      setEgress(null);
                    }}
                    required
                  />
                </label>
                <label>
                  Rows from start (maximum 100)
                  <input
                    type="number"
                    min="1"
                    max={Math.min(preview?.row_count ?? 1, 100)}
                    value={count}
                    onChange={(e) => {
                      setCount(Number(e.target.value));
                      setEgress(null);
                    }}
                  />
                </label>
                <label>
                  Existing draft to repair (optional, single row only)
                  <textarea
                    value={original}
                    onChange={(e) => {
                      setOriginal(e.target.value);
                      setEgress(null);
                    }}
                    placeholder={'{"title":"…","description":"…","claims":[]}'}
                  />
                </label>
                <p>
                  Up to 16 cumulative attempts per row. The grant is the tighter
                  campaign limit. Imported repair copy must refer to the same
                  product.
                </p>
                <button
                  disabled={
                    busy ||
                    !grant ||
                    count < 1 ||
                    count > 100 ||
                    (!!original && count !== 1)
                  }
                  onClick={() =>
                    action(async () => {
                      const run = crypto.randomUUID();
                      if (original) {
                        await api(`/api/workspaces/${workspace}/tasks`, {
                          method: "POST",
                          headers: { "Idempotency-Key": run },
                          body: JSON.stringify({
                            import_id: importId,
                            row: 0,
                            grant,
                            original: original ? JSON.parse(original) : null,
                          }),
                        });
                        setTab("queue");
                        await refresh();
                        setNotice(
                          "Repair task queued with immutable original.",
                        );
                      } else {
                        const batch = await api(
                          `/api/workspaces/${workspace}/batches`,
                          {
                            method: "POST",
                            headers: { "Idempotency-Key": run },
                            body: JSON.stringify({
                              import_id: importId,
                              rows: Array.from({ length: count }, (_, i) => i),
                              grant,
                            }),
                          },
                        );
                        const preview = await api(
                          `/api/batches/${batch.id}/egress-preview`,
                        );
                        setEgress({ id: batch.id, ...preview });
                      }
                    })
                  }
                >
                  {original
                    ? "Authorize repair"
                    : "Prepare exact egress preview"}{" "}
                  <ArrowRight size={15} />
                </button>
                {egress && (
                  <div className="banner">
                    <h3>Explicit batch authorization</h3>
                    <p>
                      Maximum {egress.maximum_calls} calls; grant has{" "}
                      {egress.grant_remaining} calls remaining. Tighter limits
                      win; completion is not promised.
                    </p>
                    <details>
                      <summary>
                        Exact approved facts sent to installed Codex
                      </summary>
                      <pre>{JSON.stringify(egress.facts, null, 2)}</pre>
                    </details>
                    <small>Binding: {egress.binding}</small>
                    <p>
                      <button
                        disabled={busy}
                        onClick={() =>
                          action(async () => {
                            await api(`/api/batches/${egress.id}/start`, {
                              method: "POST",
                              body: JSON.stringify({ binding: egress.binding }),
                            });
                            setNotice("Exact frozen batch started.");
                            setTab("queue");
                            setEgress(null);
                            await refresh();
                          })
                        }
                      >
                        Authorize this frozen batch & start
                      </button>
                    </p>
                  </div>
                )}
              </section>
            )}
          </div>
        )}
        {tab === "queue" && (
          <>
            {!!savedBatches.length && (
              <section>
                <details>
                  <summary>
                    Saved batches · latest 50 · original row denominators
                    retained
                  </summary>
                  {savedBatches.map((batch) => (
                    <article className="version" key={batch.id}>
                      <h3>
                        {batch.id.slice(0, 10)} · {batch.state}
                      </h3>
                      <p>
                        {batch.total_rows} selected rows · {batch.calls} calls ·{" "}
                        {batch.unknown_attempts} unknown attempts
                      </p>
                      <p>
                        {Object.entries(batch.counts)
                          .map(
                            ([state, count]) =>
                              `${state.replaceAll("_", " ")}: ${count}`,
                          )
                          .join(" · ") || "Prepared, no rows dispatched"}
                      </p>
                      {batch.tasks.some((t) =>
                        ["queued", "running"].includes(t.state),
                      ) && (
                        <button
                          className="secondary"
                          disabled={busy}
                          onClick={() =>
                            action(async () => {
                              await api(`/api/batches/${batch.id}/cancel`, {
                                method: "POST",
                              });
                              await refresh();
                              setNotice(
                                "Entire batch cancelled; retained drafts are not export-eligible.",
                              );
                            })
                          }
                        >
                          Cancel whole batch
                        </button>
                      )}
                      {batch.state === "prepared" && (
                        <button
                          className="secondary"
                          disabled={busy}
                          onClick={() =>
                            action(async () => {
                              const result = await api(
                                `/api/batches/${batch.id}/egress-preview`,
                              );
                              setEgress({ id: batch.id, ...result });
                              setImportId(batch.source_id);
                              setPreview({
                                columns: [],
                                row_count: batch.total_rows,
                                sample: null,
                              });
                              setFile(null);
                              setTab("source");
                            })
                          }
                        >
                          Inspect frozen egress before starting
                        </button>
                      )}
                    </article>
                  ))}
                </details>
              </section>
            )}
            <div className="stats">
              <section>
                <span>IN THIS PAGE</span>
                <strong>{tasks.length}</strong>
                <small>Latest 100 tasks, not entire corpus</small>
              </section>
              <section>
                <span>REVIEW READY</span>
                <strong>
                  {tasks.filter((t) => t.state === "review_ready").length}
                </strong>
                <small>Requires independent approval</small>
              </section>
              <section>
                <span>NEEDS ATTENTION</span>
                <strong>
                  {
                    tasks.filter((t) =>
                      [
                        "manual_required",
                        "needs_data",
                        "stale",
                        "failed",
                      ].includes(t.state),
                    ).length
                  }
                </strong>
                <small>Never silently exported</small>
              </section>
            </div>
            <div className="desk">
              <section className="queue">
                <h2>
                  <Layers3 size={18} />
                  Review queue
                </h2>
                {!tasks.length && (
                  <div className="empty">
                    <Leaf />
                    <h3>No source rows yet</h3>
                    <p>Freeze an approved source snapshot to begin.</p>
                    <button onClick={() => setTab("source")}>
                      Open source intake
                    </button>
                  </div>
                )}
                <div className="queue-controls">
                  <label>
                    Search this page
                    <input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Product, GTIN or task"
                    />
                  </label>
                  <label>
                    State
                    <select
                      value={stateFilter}
                      onChange={(e) => setStateFilter(e.target.value)}
                    >
                      <option value="all">All states</option>
                      {Array.from(new Set(tasks.map((t) => t.state))).map(
                        (state) => (
                          <option key={state} value={state}>
                            {state.replaceAll("_", " ")}
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                </div>
                {tasks
                  .filter(
                    (t) =>
                      (stateFilter === "all" || t.state === stateFilter) &&
                      `${t.name ?? ""} ${t.brand ?? ""} ${t.product_id ?? ""} ${t.id}`
                        .toLowerCase()
                        .includes(search.toLowerCase()),
                  )
                  .map((item) => (
                    <button
                      className={`queue-item ${task?.id === item.id ? "chosen" : ""}`}
                      key={item.id}
                      onClick={() =>
                        action(async () => {
                          setTask(await api(`/api/tasks/${item.id}`));
                          setAudit(null);
                          setReason("");
                          setInspectedRevision(null);
                          setHighlight(null);
                          setUnknownAcknowledged(false);
                          setEditTitle("");
                          setEditDescription("");
                          setEditGrant("");
                        })
                      }
                    >
                      <span>
                        {item.name ?? `Row ${item.id.slice(0, 8)}`}
                        <small>
                          {item.brand} · {item.product_id}
                        </small>
                        <small>{item.calls} calls</small>
                      </span>
                      <span className={`badge ${item.state}`}>
                        {item.state.replaceAll("_", " ")}
                      </span>
                    </button>
                  ))}
              </section>
              <div className="detail">
                {!task ? (
                  <section className="empty">
                    <FileCheck2 />
                    <h2>Select a row to inspect its evidence</h2>
                    <p>
                      Original, selected and rejected drafts remain visible.
                      Higher scores never override hard gates.
                    </p>
                  </section>
                ) : (
                  <>
                    <section>
                      <div className="section-heading">
                        <div>
                          <p className="eyebrow">
                            {task.facts.product_id} / SOURCE-BOUND REVIEW
                          </p>
                          <h2>
                            {task.facts.brand} {task.facts.name}
                          </h2>
                        </div>
                        <span className={`badge ${task.state}`}>
                          {task.state.replaceAll("_", " ")}
                        </span>
                      </div>
                      <dl>
                        {Object.entries(task.facts).map(([key, value]) => (
                          <React.Fragment key={key}>
                            <dt>{key.replaceAll("_", " ")}</dt>
                            <dd>{value}</dd>
                          </React.Fragment>
                        ))}
                      </dl>
                    </section>
                    <section>
                      <div className="section-heading">
                        <h2>Version history</h2>
                        <small>Selected ≠ last attempted</small>
                      </div>
                      {!task.versions.length && <p>No draft retained yet.</p>}
                      {task.versions.map((version, i) => (
                        <article
                          key={`${version.draft_hash}:${i}`}
                          className={
                            version.draft_hash === task.selected_hash
                              ? "version selected"
                              : "version"
                          }
                        >
                          <div className="section-heading">
                            <p className="eyebrow">
                              VERSION {i} · {version.source ?? "imported"}
                            </p>
                            <span className="badge">
                              {version.draft_hash === task.selected_hash
                                ? "Selected incumbent"
                                : i === 0
                                  ? "Original"
                                  : "Not selected"}
                            </span>
                          </div>
                          <h3>
                            {highlighted(
                              version.draft?.title ?? "",
                              "title",
                              `${version.draft_hash}:${version.version_index ?? i}`,
                            )}
                          </h3>
                          <p className="copy">
                            {highlighted(
                              version.draft?.description ?? "",
                              "description",
                              `${version.draft_hash}:${version.version_index ?? i}`,
                            )}
                          </p>
                          <button
                            className="secondary"
                            onClick={() => {
                              setInspectedRevision(version.version_index ?? i);
                              setHighlight(null);
                            }}
                          >
                            Inspect this version's evaluation
                          </button>
                          {i > 0 && (
                            <details>
                              <summary>
                                Compare with original · removed / added
                              </summary>
                              <p className="copy">
                                {difference(
                                  task.versions[0].draft?.title ?? "",
                                  version.draft?.title ?? "",
                                )}
                              </p>
                              <p className="copy">
                                {difference(
                                  task.versions[0].draft?.description ?? "",
                                  version.draft?.description ?? "",
                                )}
                              </p>
                            </details>
                          )}
                          <small className="hash">{version.draft_hash}</small>
                        </article>
                      ))}
                    </section>
                    <section>
                      <h2>Evaluation, not certification</h2>
                      <p className="muted">
                        Viewing{" "}
                        {inspectedRevision === null
                          ? "selected incumbent"
                          : "a historical version"}
                        . Human approval always applies to the selected
                        incumbent.
                      </p>
                      {selectedEval ? (
                        <>
                          <div className="ratings">
                            {Object.entries(
                              selectedEval.evaluation.ratings,
                            ).map(([dimension, rating]) => (
                              <div key={dimension}>
                                <span>{dimension}</span>
                                <strong>
                                  {rating.value ?? "—"}
                                  <small> / 4</small>
                                </strong>
                                <p>{rating.rationale}</p>
                              </div>
                            ))}
                          </div>
                          <p>
                            Weighted rubric score:{" "}
                            <strong>
                              {selectedEval.score ?? "Unassessable"}
                            </strong>{" "}
                            / 100 · Not a probability
                          </p>
                          {[
                            ...selectedEval.checks,
                            ...selectedEval.evaluation.findings,
                          ].map((finding, i) => (
                            <div className="finding" key={i}>
                              <span className="badge">
                                {finding.severity} · {finding.family}
                              </span>
                              <p>{finding.explanation}</p>
                              {finding.quote && (
                                <blockquote>{finding.quote}</blockquote>
                              )}
                              {finding.field &&
                                finding.quote &&
                                finding.start != null &&
                                finding.end != null && (
                                  <button
                                    className="secondary"
                                    onClick={() =>
                                      setHighlight({
                                        hash: `${selectedEval.draft_hash}:${selectedEval.version_index}`,
                                        field: finding.field!,
                                        start: finding.start!,
                                        end: finding.end!,
                                        quote: finding.quote!,
                                      })
                                    }
                                  >
                                    Highlight exact Unicode evidence above
                                  </button>
                                )}
                            </div>
                          ))}
                        </>
                      ) : (
                        <p>
                          No assessable evaluation available. This row cannot
                          pass.
                        </p>
                      )}
                      <details>
                        <summary>
                          Correction plans & improvement metrics
                        </summary>
                        <pre>
                          {JSON.stringify(
                            { plans: task.plans, metrics: task.metrics },
                            null,
                            2,
                          )}
                        </pre>
                      </details>
                    </section>
                    <section>
                      <h2>Execution receipts</h2>
                      <table>
                        <thead>
                          <tr>
                            <th>Stage</th>
                            <th>Accounting</th>
                            <th>Input / output</th>
                          </tr>
                        </thead>
                        <tbody>
                          {task.attempts.map((attempt, i) => (
                            <tr key={i}>
                              <td>{attempt.stage}</td>
                              <td>{attempt.status}</td>
                              <td>
                                {usageLabel(attempt.receipt?.input_tokens)} /{" "}
                                {usageLabel(attempt.receipt?.output_tokens)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() =>
                          action(async () =>
                            setAudit(await api(`/api/tasks/${task.id}/audit`)),
                          )
                        }
                      >
                        Inspect audit trail
                      </button>
                      {audit !== null && (
                        <pre>{JSON.stringify(audit, null, 2)}</pre>
                      )}
                    </section>
                    <section>
                      <h2>Independent human decision</h2>
                      <p>
                        Approval binds to the exact selected version. Maker:{" "}
                        {task.maker}. Server rechecks authority, usage and hard
                        gates.
                      </p>
                      <label>
                        Review rationale
                        <textarea
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          maxLength={2000}
                        />
                      </label>
                      {!!task.warnings.length && (
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={unknownAcknowledged}
                            onChange={(e) =>
                              setUnknownAcknowledged(e.target.checked)
                            }
                          />
                          I acknowledge owner-accepted unknown historical
                          usage/tool safety. This is not fully audited
                          acceptance.
                        </label>
                      )}
                      <div className="actions">
                        <button
                          disabled={
                            busy || !canReview(task, actor) || !reason.trim()
                          }
                          onClick={() =>
                            action(async () => {
                              await api(`/api/tasks/${task.id}/reviews`, {
                                method: "POST",
                                body: JSON.stringify({
                                  version_hash: selected?.draft_hash,
                                  artifact_hash: task.selected_artifact_hash,
                                  decision: "accept",
                                  reason,
                                  acknowledge_unknown: unknownAcknowledged,
                                }),
                              });
                              setNotice(
                                "Exact version approved. Export remains subject to current source authority.",
                              );
                            })
                          }
                        >
                          <Check size={16} />
                          Approve selected version
                        </button>
                        <button
                          className="secondary"
                          disabled={
                            busy || !canReview(task, actor) || !reason.trim()
                          }
                          onClick={() =>
                            action(async () => {
                              await api(`/api/tasks/${task.id}/reviews`, {
                                method: "POST",
                                body: JSON.stringify({
                                  version_hash: selected?.draft_hash,
                                  artifact_hash: task.selected_artifact_hash,
                                  decision: "reject",
                                  reason,
                                  acknowledge_unknown: unknownAcknowledged,
                                }),
                              });
                              setNotice("Review rejection recorded.");
                            })
                          }
                        >
                          Reject
                        </button>
                        {["queued", "running"].includes(task.state) && (
                          <button
                            className="secondary"
                            disabled={busy}
                            onClick={() =>
                              action(async () => {
                                await api(`/api/tasks/${task.id}/cancel`, {
                                  method: "POST",
                                });
                                await refresh();
                              })
                            }
                          >
                            Cancel task
                          </button>
                        )}
                      </div>
                    </section>
                    <section>
                      <h2>Human edit · separately authorized reevaluation</h2>
                      <p>
                        Editing creates an attributed successor and invalidates
                        this task's approval. It does not make an unevaluated
                        edit exportable.
                      </p>
                      <button
                        className="secondary"
                        onClick={() => {
                          setEditTitle(selected?.draft?.title ?? "");
                          setEditDescription(
                            selected?.draft?.description ?? "",
                          );
                        }}
                      >
                        Copy selected draft into editor
                      </button>
                      <label>
                        Edited title
                        <input
                          maxLength={150}
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                        />
                      </label>
                      <label>
                        Edited description
                        <textarea
                          maxLength={5000}
                          value={editDescription}
                          onChange={(e) => setEditDescription(e.target.value)}
                        />
                      </label>
                      <label>
                        Current egress grant ID
                        <input
                          value={editGrant}
                          onChange={(e) => setEditGrant(e.target.value)}
                        />
                      </label>
                      <button
                        disabled={
                          busy ||
                          !selected ||
                          !editTitle ||
                          !editDescription ||
                          !editGrant ||
                          task.state === "running"
                        }
                        onClick={() =>
                          action(async () => {
                            const result = await api(
                              `/api/tasks/${task.id}/edits`,
                              {
                                method: "POST",
                                body: JSON.stringify({
                                  version_hash: task.selected_hash,
                                  draft: {
                                    title: editTitle,
                                    description: editDescription,
                                    claims: [],
                                  },
                                  grant: editGrant,
                                }),
                              },
                            );
                            await refresh();
                            setTask(await api(`/api/tasks/${result.id}`));
                            setNotice(
                              "Attributed edit queued for separate evaluation. Prior task is stale.",
                            );
                          })
                        }
                      >
                        Create edit & authorize reevaluation
                      </button>
                    </section>
                  </>
                )}
                <section className="export">
                  <h2>Export approved partial patches</h2>
                  <p>
                    Only current, independently accepted rows. Every excluded
                    row is listed in the unresolved manifest. No price,
                    inventory or publish action.
                  </p>
                  <button
                    disabled={busy || !workspace}
                    onClick={() =>
                      action(async () => {
                        const result = await api(
                          `/api/workspaces/${workspace}/exports`,
                          { method: "POST" },
                        );
                        download(result);
                        setNotice(
                          `${result.approved_count} of ${result.total} task rows approved. Check unresolved entries in download.`,
                        );
                      })
                    }
                  >
                    Download JSON patch <ArrowRight size={16} />
                  </button>
                </section>
              </div>
            </div>
          </>
        )}
        <footer>
          Frozen facts. Bounded reflection. Human accountability.{" "}
          <span>Internal implementation preview · Acceptance pending</span>
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
