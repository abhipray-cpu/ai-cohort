import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Boxes,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Code2,
  FileJson,
  Fingerprint,
  GitBranch,
  Globe2,
  Layers3,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  MessageSquare,
  Network,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  ShieldQuestion,
  SlidersHorizontal,
  Square,
  Terminal,
  Upload,
  Users,
  X,
  Zap,
} from "lucide-react";
import {
  distinctClients,
  outcomeLabel,
  publicationAction,
  statusTone,
} from "./presentation";
import "./styles.css";

type Data = Record<string, any>;
type Tab = "plan" | "conversation" | "activity" | "inventory" | "tools";
const key = () => crypto.randomUUID();
const date = (value?: string) =>
  value ? new Date(value).toLocaleString() : "Not recorded";
const short = (value?: string) => (value ? value.slice(0, 10) : "—");
function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${statusTone(value)}`}>
      <span />
      {outcomeLabel(value)}
    </span>
  );
}
function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const el = ref.current;
    const list = () =>
      Array.from(
        el?.querySelectorAll<HTMLElement>(
          "button,input,textarea,select,a[href]",
        ) || [],
      ).filter((e) => !e.hasAttribute("disabled"));
    list()[0]?.focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const items = list(),
          first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <div>
            <span className="eyebrow">PATCHDESK WORKSPACE</span>
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
      </div>
    </div>
  );
}

function App() {
  const [me, setMe] = useState<Data | null>(null),
    [boot, setBoot] = useState(true),
    [projects, setProjects] = useState<Data[]>([]),
    [selected, setSelected] = useState(""),
    [project, setProject] = useState<Data | null>(null),
    [input, setInput] = useState<Data | null>(null),
    [run, setRun] = useState<Data | null>(null),
    [report, setReport] = useState<Data | null>(null),
    [caps, setCaps] = useState<Data | null>(null);
  const [tab, setTab] = useState<Tab>("plan"),
    [search, setSearch] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [modal, setModal] = useState(""),
    [snapshot, setSnapshot] = useState<Data | null>(null),
    [publication, setPublication] = useState<Data | null>(null);
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [client, setClient] = useState(""),
    [question, setQuestion] = useState(
      "Prepare this project's next security-maintenance batch. Explain evidence, conflicts and verification requirements.",
    ),
    [manifest, setManifest] = useState<Data | null>(null),
    [lockfile, setLockfile] = useState<Data | null>(null),
    [fileNames, setFileNames] = useState<string[]>([]),
    [packageList, setPackageList] = useState(""),
    [modelEgress, setModelEgress] = useState(false),
    [repo, setRepo] = useState(""),
    [repoId, setRepoId] = useState(""),
    [nodeVersion, setNodeVersion] = useState(""),
    [notes, setNotes] = useState(""),
    [summary, setSummary] = useState(""),
    [editSummary, setEditSummary] = useState(false),
    [ack, setAck] = useState(false),
    [member, setMember] = useState(""),
    [memberRoles, setMemberRoles] = useState(["analyst"]),
    [newPassword, setNewPassword] = useState("");
  const current = useRef(selected);
  current.current = selected;
  async function api(
    path: string,
    method = "GET",
    body?: any,
    extra: Data = {},
  ) {
    const response = await fetch(path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(me ? { "X-CSRF-Token": me.csrf } : {}),
        ...extra,
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) {
      let detail = "Request failed";
      try {
        const data = await response.json();
        detail =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      } catch {}
      if (response.status === 401) setMe(null);
      throw new Error(detail);
    }
    return response.headers.get("content-type")?.includes("json")
      ? response.json()
      : response.text();
  }
  async function action(work: () => Promise<void>) {
    setError("");
    setBusy(true);
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  async function refreshList() {
    setProjects(await api("/v1/projects"));
  }
  async function loadProject(id: string) {
    const p = await api(`/v1/projects/${id}`);
    if (current.current !== id) return;
    setProject(p);
    setReport(p.report);
    setCaps(await api(`/v1/projects/${id}/capabilities`));
    if (p.latest_input) {
      const data = await api(`/v1/snapshots/${p.latest_input}`);
      if (current.current === id) setInput(data);
    } else setInput(null);
    if (p.runs.length) {
      const value = await api(`/v1/runs/${p.runs[0].id}`);
      if (current.current === id) setRun(value);
    } else setRun(null);
  }
  useEffect(() => {
    fetch("/v1/me")
      .then(async (r) => {
        if (r.ok) {
          setMe(await r.json());
        }
      })
      .finally(() => setBoot(false));
  }, []);
  useEffect(() => {
    if (me) action(refreshList);
    else {
      setProjects([]);
      setSelected("");
      setProject(null);
    }
  }, [me?.username]);
  useEffect(() => {
    setError("");
    setProject(null);
    setInput(null);
    setRun(null);
    setReport(null);
    setPublication(null);
    if (selected) action(() => loadProject(selected));
  }, [selected]);
  useEffect(() => {
    if (!run || !["running", "queued"].includes(run.status)) return;
    const id = selected;
    const timer = setInterval(async () => {
      try {
        const next = await api(`/v1/runs/${run.id}`);
        if (current.current !== id) return;
        setRun(next);
        if (next.report) setReport(next.report);
        if (!["running", "queued"].includes(next.status)) await loadProject(id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Progress unavailable");
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [run?.id, run?.status, selected]);
  useEffect(() => {
    if (project) {
      setPackageList(project.policy.public_packages.join("\n"));
      setModelEgress(project.policy.model_egress);
      setRepo(project.policy.repository);
      setRepoId(
        project.policy.repository_id
          ? String(project.policy.repository_id)
          : "",
      );
      setNodeVersion(project.policy.node_version);
    }
  }, [project?.id, project?.revision]);
  const active = run && ["queued", "running"].includes(run.status),
    inventory = input?.payload.inventory,
    payload = report?.payload,
    findings: Data[] = payload?.findings || [],
    conflicts: Data[] = payload?.conflicts || [],
    candidates: Data[] = payload?.candidates || [],
    results: Data[] = Object.values(run?.results || {}),
    canInvestigate = project?.roles.includes("analyst"),
    canReview = project?.roles.includes("reviewer"),
    canPublish = project?.roles.includes("publisher");
  function openReview() {
    setSummary(payload.narrative.summary);
    setNotes(report?.notes || "");
    setEditSummary(false);
    setAck(false);
    setModal("review");
  }
  async function start(refresh = false) {
    await action(async () => {
      const value = await api(
        `/v1/projects/${selected}/${refresh ? "refresh" : "messages"}`,
        "POST",
        { content: question },
        { "Idempotency-Key": key() },
      );
      setRun(value);
      setReport(null);
      setTab("conversation");
      setNotice(
        "Investigation queued. Completed evidence will appear as tools finish.",
      );
    });
  }
  async function download(format = "markdown") {
    await action(async () => {
      const response = await fetch(
        `/v1/reports/${report!.id}/exports?format=${format}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": me!.csrf,
          },
          body: "{}",
        },
      );
      if (!response.ok) {
        const e = await response.json();
        throw new Error(e.detail);
      }
      const blob = await response.blob(),
        url = URL.createObjectURL(blob),
        a = document.createElement("a");
      a.href = url;
      a.download = `patchdesk-${short(report!.id)}.${format === "json" ? "json" : "md"}`;
      a.click();
      URL.revokeObjectURL(url);
      setNotice("Reviewed pack exported with source coverage and limitations.");
    });
  }
  if (boot)
    return (
      <div className="loading-page">
        <LoaderCircle className="spin" /> Connecting to your workspace…
      </div>
    );
  if (!me)
    return (
      <main className="login-page">
        <section className="login-story">
          <div className="brand">
            <div className="brand-mark">
              <Layers3 size={23} />
            </div>
            PatchDesk<span>MAINTENANCE INTELLIGENCE</span>
          </div>
          <div className="login-copy">
            <span className="eyebrow">
              LESS ALERT NOISE. MORE ACCOUNTABILITY.
            </span>
            <h1>
              From scattered alerts
              <br />
              to a considered
              <br />
              <em>maintenance plan.</em>
            </h1>
            <p>
              One workspace for dependency evidence, conflicting advice and the
              client decisions that matter.
            </p>
            <div className="login-points">
              <span>
                <Network size={18} /> Tools working together
              </span>
              <span>
                <Fingerprint size={18} /> Evidence behind every decision
              </span>
              <span>
                <LockKeyhole size={18} /> Your scope. Your approval.
              </span>
            </div>
          </div>
          <footer>
            BUILT FOR THE WORK AFTER THE BUILD <span>01 — 04</span>
          </footer>
        </section>
        <section className="login-form">
          <div className="login-card">
            <span className="eyebrow">YOUR PRIVATE WORKSPACE</span>
            <h2>Good to have you back.</h2>
            <p>
              Sign in to review maintenance work across your authorized client
              projects.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                action(async () => {
                  const user = await api("/v1/session", "POST", {
                    username,
                    password,
                  });
                  setMe(user);
                  setPassword("");
                });
              }}
            >
              <label>
                Username
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </label>
              {error && (
                <div role="alert" className="error">
                  {error}
                </div>
              )}
              <button className="primary large" disabled={busy}>
                {busy ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <>
                    Enter workspace <ArrowRight size={17} />
                  </>
                )}
              </button>
            </form>
            <div className="privacy-note">
              <ShieldCheck size={18} />
              <span>
                Project-scoped access. No changes or publications without
                explicit permission.
              </span>
            </div>
          </div>
        </section>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="PatchDesk home">
          <div className="brand-mark">
            <Layers3 size={22} />
          </div>
          PatchDesk
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">
            {me.username[0].toUpperCase()}
          </span>
          <div>
            Agency workspace<small>PRIVATE INSTANCE</small>
          </div>
          <ShieldCheck size={16} />
        </div>
        <div className="sidebar-section-label">
          CLIENT PROJECTS{" "}
          <button
            className="icon-button"
            aria-label="New project"
            onClick={() => {
              setName("");
              setClient("");
              setModal("project");
            }}
          >
            <Plus size={16} />
          </button>
        </div>
        <label className="search">
          <Search size={15} />
          <input
            aria-label="Search projects"
            placeholder="Find a project…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <nav className="project-list">
          {distinctClients(projects as { client: string }[]).map((group) => (
            <div key={group}>
              <div className="client-label">{group}</div>
              {projects
                .filter(
                  (p) =>
                    p.client === group &&
                    p.name.toLowerCase().includes(search.toLowerCase()),
                )
                .map((p) => (
                  <button
                    key={p.id}
                    className={`project-link ${selected === p.id ? "selected" : ""}`}
                    onClick={() => setSelected(p.id)}
                  >
                    <span className="project-icon">
                      <Code2 size={16} />
                    </span>
                    <span>
                      {p.name}
                      <small>
                        {p.latest_input
                          ? "Snapshot available"
                          : "Awaiting first import"}
                      </small>
                    </span>
                    <ChevronRight size={14} />
                  </button>
                ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="scope-note">
            <LockKeyhole size={17} />
            <div>
              Permission, not assumption.
              <small>Only your authorized projects appear here.</small>
            </div>
          </div>
          {me.admin && (
            <button
              className="sidebar-control"
              onClick={() => setModal("user")}
            >
              <Users size={17} /> Add workspace user
            </button>
          )}
          <button
            className="sidebar-control"
            onClick={() =>
              action(async () => {
                await api("/v1/session", "DELETE");
                setMe(null);
              })
            }
          >
            <LogOut size={17} /> {me.username}
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={13} />
            <span>{project?.client || "Overview"}</span>
            {project && (
              <>
                <ChevronRight size={13} />
                <strong>{project.name}</strong>
              </>
            )}
          </div>
          <div className="topbar-right">
            <span className="private-indicator">
              <span /> Private service
            </span>
            <button
              className="icon-button"
              aria-label="About evidence limits"
              onClick={() => setModal("about")}
            >
              <CircleHelp size={18} />
            </button>
          </div>
        </header>
        <main>
          {error && (
            <div className="toast error" role="alert">
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={15} />
              </button>
            </div>
          )}
          {notice && (
            <div className="toast notice" role="status">
              {notice}
              <button
                onClick={() => setNotice("")}
                aria-label="Dismiss notification"
              >
                <X size={15} />
              </button>
            </div>
          )}
          {!project ? (
            <section className="welcome">
              <div className="welcome-icon">
                <Network size={36} />
              </div>
              <span className="eyebrow">A CLEARER MAINTENANCE PICTURE</span>
              <h1>
                Every client.
                <br />
                Every decision, accounted for.
              </h1>
              <p>
                Create a project, bring its recorded dependency graph, and turn
                public-source evidence into work your team can review.
              </p>
              <button
                className="primary large"
                onClick={() => setModal("project")}
              >
                <Plus size={18} /> Create your first project
              </button>
              <div className="welcome-grid">
                <article>
                  <FileJson />
                  <h3>Start with the actual graph</h3>
                  <p>
                    Import paired npm manifests and lockfiles. No installs. No
                    project scripts.
                  </p>
                </article>
                <article>
                  <Boxes />
                  <h3>Orchestrate the right tools</h3>
                  <p>
                    Capability routing, bounded parallel checks and visible
                    source gaps.
                  </p>
                </article>
                <article>
                  <CheckCheck />
                  <h3>Keep a human in control</h3>
                  <p>
                    Review the evidence, approve the scope, export a considered
                    plan.
                  </p>
                </article>
              </div>
            </section>
          ) : (
            <>
              <div className="project-heading">
                <div>
                  <span className="eyebrow">
                    {project.client} / SECURITY MAINTENANCE
                  </span>
                  <h1>{project.name}</h1>
                  <div className="project-meta">
                    <GitBranch size={14} />
                    <span>
                      {project.policy.repository || "Uploaded project snapshot"}
                    </span>
                    <span className="separator">/</span>
                    <Fingerprint size={14} />
                    <span>{short(input?.sha256)}</span>
                    <span className="separator">/</span>
                    <span>
                      {inventory
                        ? `${inventory.packages.length.toLocaleString()} recorded instances`
                        : "No input imported"}
                    </span>
                  </div>
                </div>
                <div className="heading-actions">
                  <button
                    className="secondary"
                    onClick={() => setModal("policy")}
                  >
                    <SlidersHorizontal size={15} /> Scope & permissions
                  </button>
                  <button
                    className="primary"
                    onClick={() => {
                      setManifest(null);
                      setLockfile(null);
                      setFileNames([]);
                      setModal("import");
                    }}
                    disabled={!canInvestigate || !!active}
                  >
                    <Upload size={16} /> Import snapshot
                  </button>
                </div>
              </div>
              <div className="stat-strip">
                <div>
                  <span className="stat-icon">
                    <Boxes size={19} />
                  </span>
                  <div>
                    <small>RECORDED INSTANCES</small>
                    <strong>
                      {inventory?.packages.length.toLocaleString() || "—"}
                    </strong>
                  </div>
                </div>
                <div>
                  <span className="stat-icon amber">
                    <ShieldQuestion size={19} />
                  </span>
                  <div>
                    <small>ADVISORY CONCERNS</small>
                    <strong>
                      {payload ? findings.length.toLocaleString() : "—"}
                      <span>recorded, not exposure</span>
                    </strong>
                  </div>
                </div>
                <div>
                  <span className="stat-icon">
                    <Network size={19} />
                  </span>
                  <div>
                    <small>CONFLICTS TO REVIEW</small>
                    <strong>{payload ? conflicts.length : "—"}</strong>
                  </div>
                </div>
                <div>
                  <span className="stat-icon sage">
                    <CheckCheck size={19} />
                  </span>
                  <div>
                    <small>REVIEW STATE</small>
                    <strong className="text-stat">
                      {report?.reviewed_by
                        ? "Reviewed"
                        : report
                          ? "Needs review"
                          : "Not started"}
                    </strong>
                  </div>
                </div>
              </div>
              <div className="tabs-and-status">
                <nav className="tabs">
                  {(
                    [
                      ["plan", "Maintenance plan", Layers3],
                      ["conversation", "Investigation", MessageSquare],
                      ["inventory", "Inventory", FileJson],
                      ["activity", "Activity", Network],
                      ["tools", "Tool registry", Settings2],
                    ] as const
                  ).map(([value, label, Icon]) => (
                    <button
                      key={value}
                      className={tab === value ? "active" : ""}
                      onClick={() => setTab(value)}
                    >
                      <Icon size={16} />
                      {label}
                    </button>
                  ))}
                </nav>
                {run && <Badge value={run.status} />}
              </div>
              <div className="content-grid">
                <section className="main-panel">
                  {tab === "plan" &&
                    (!report ? (
                      <div className="empty-panel">
                        <div className="empty-art">
                          <Layers3 size={38} />
                          <span>
                            <Search size={18} />
                          </span>
                        </div>
                        <span className="eyebrow">
                          EVIDENCE FIRST, ACTION SECOND
                        </span>
                        <h2>A plan worth reviewing starts here.</h2>
                        <p>
                          {inventory
                            ? "Your inventory is ready. Confirm your package and model egress permissions, then start an investigation."
                            : "Import package.json and package-lock.json to see the recorded graph, supported coverage and source checks."}
                        </p>
                        {inventory ? (
                          <button
                            className="primary"
                            onClick={() => start()}
                            disabled={busy || !!active || !canInvestigate}
                          >
                            <Zap size={16} /> Prepare maintenance plan
                          </button>
                        ) : (
                          <button
                            className="secondary"
                            onClick={() => setModal("import")}
                            disabled={!canInvestigate}
                          >
                            <Upload size={16} /> Import project files
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="report-content">
                        <div className="section-heading">
                          <div>
                            <span className="eyebrow">
                              MAINTENANCE BRIEF / {short(report.id)}
                            </span>
                            <h2>What needs your attention</h2>
                          </div>
                          <button
                            className="secondary"
                            disabled={!canReview}
                            onClick={openReview}
                          >
                            <CheckCheck size={15} />
                            {report.reviewed_by
                              ? "Review notes"
                              : "Review pack"}
                          </button>
                        </div>
                        <p className="report-summary">
                          {payload.narrative.summary}
                        </p>
                        {payload.gaps.length > 0 && (
                          <div className="qualification">
                            <ShieldQuestion size={20} />
                            <div>
                              <strong>This pack has qualified coverage</strong>
                              <p>
                                {payload.gaps.length} source, input or
                                investigation limitations remain. Review the
                                evidence before using this plan.
                              </p>
                              <details>
                                <summary>Show all coverage gaps</summary>
                                <ul>
                                  {payload.gaps.map((g: string, i: number) => (
                                    <li key={i}>{g}</li>
                                  ))}
                                </ul>
                              </details>
                            </div>
                          </div>
                        )}
                        <div className="subheading">
                          <h3>Recorded advisory concerns</h3>
                          <span>{findings.length} total</span>
                        </div>
                        {!findings.length && (
                          <p className="muted">
                            No supported matches are presented. Check source
                            coverage before interpreting an empty result.
                          </p>
                        )}
                        {findings.slice(0, 60).map((f) => (
                          <article className="finding-card" key={f.id}>
                            <div className="finding-symbol">
                              <ShieldQuestion size={18} />
                            </div>
                            <div className="finding-main">
                              <div className="finding-title">
                                <h4>
                                  {f.package}
                                  <code>{f.version}</code>
                                </h4>
                                <Badge value={f.status} />
                              </div>
                              <a
                                href={`https://github.com/advisories/${f.advisory_id}`}
                                target="_blank"
                                rel="noreferrer"
                                className="advisory-link"
                              >
                                {f.advisory_id}
                                <ArrowUpRight size={12} />
                              </a>
                              {f.summary && <p>{f.summary}</p>}
                              <p>{f.claim}</p>
                              <div className="finding-path">
                                <GitBranch size={12} />
                                <code>{f.location}</code>
                                {f.dev && (
                                  <span className="tiny-tag">Development</span>
                                )}
                              </div>
                              <div className="evidence-buttons">
                                {f.evidence.map((ref: Data, i: number) => (
                                  <button
                                    key={i}
                                    onClick={() =>
                                      action(async () =>
                                        setSnapshot(
                                          await api(
                                            `/v1/snapshots/${ref.snapshot_id}`,
                                          ),
                                        ),
                                      )
                                    }
                                  >
                                    <Fingerprint size={12} />
                                    {ref.adapter}
                                    <ArrowUpRight size={11} />
                                  </button>
                                ))}
                              </div>
                            </div>
                          </article>
                        ))}
                        {findings.length > 60 && (
                          <p className="muted">
                            Showing 60 findings. The full reviewed export
                            retains all {findings.length}.
                          </p>
                        )}
                        {conflicts.length > 0 && (
                          <>
                            <div className="subheading">
                              <h3>Conflicting source assertions</h3>
                              <span>{conflicts.length} unresolved</span>
                            </div>
                            {conflicts.slice(0, 15).map((c) => (
                              <article className="conflict-card" key={c.id}>
                                <h4>
                                  <Network size={16} />
                                  {outcomeLabel(c.category)}
                                </h4>
                                <p>{c.reason}</p>
                                <div className="assertion-grid">
                                  {c.assertions.map((a: Data, i: number) => (
                                    <button
                                      key={i}
                                      onClick={() =>
                                        action(async () =>
                                          setSnapshot(
                                            await api(
                                              `/v1/snapshots/${a.evidence.snapshot_id}`,
                                            ),
                                          ),
                                        )
                                      }
                                    >
                                      <small>{a.adapter}</small>
                                      <strong>
                                        {a.match === null
                                          ? "Unknown membership"
                                          : a.match
                                            ? "Range matches"
                                            : "Range does not match"}
                                      </strong>
                                      <span>
                                        Inspect exact source fields{" "}
                                        <ArrowUpRight size={12} />
                                      </span>
                                    </button>
                                  ))}
                                </div>
                              </article>
                            ))}
                          </>
                        )}
                        <div className="subheading">
                          <h3>Proposed maintenance work</h3>
                          <span>Human verification required</span>
                        </div>
                        {payload.narrative.tasks.map(
                          (task: Data, i: number) => (
                            <article className="task-card" key={i}>
                              <span className="task-number">
                                {String(i + 1).padStart(2, "0")}
                              </span>
                              <div>
                                <h4>
                                  {task.title}
                                  <span className={`priority ${task.priority}`}>
                                    {task.priority}
                                  </span>
                                </h4>
                                <p>{task.reason}</p>
                                <div className="verify">
                                  <CheckCheck size={14} />
                                  <span>{task.verification}</span>
                                </div>
                              </div>
                            </article>
                          ),
                        )}
                        {candidates.length > 0 && (
                          <>
                            <div className="subheading">
                              <h3>Release candidates</h3>
                              <span>Not verified upgrades</span>
                            </div>
                            <div className="table-wrap">
                              <table>
                                <thead>
                                  <tr>
                                    <th>Package / target</th>
                                    <th>Captured advisory</th>
                                    <th>Engine</th>
                                    <th>Verification</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {candidates.slice(0, 40).map((c) => (
                                    <tr key={c.id}>
                                      <td>
                                        <strong>{c.package}</strong>
                                        <code>{c.target}</code>
                                      </td>
                                      <td>{outcomeLabel(c.advisory_check)}</td>
                                      <td>
                                        {c.engine_check === null
                                          ? "Unknown"
                                          : c.engine_check
                                            ? "Metadata check passes"
                                            : "Constraint blocked"}
                                      </td>
                                      <td>
                                        <span className="tiny-tag">
                                          Pending
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </>
                        )}
                        <div className="report-footer">
                          <Fingerprint size={16} />
                          <span>
                            {payload.source_manifest.length} captured source
                            snapshots · report {short(report.id)} ·{" "}
                            {date(report.created_at)}
                          </span>
                        </div>
                        <div className="export-actions">
                          <button
                            className="primary"
                            disabled={!report.reviewed_by || busy || !canReview}
                            onClick={() => download()}
                          >
                            <ArrowDownToLine size={16} /> Export reviewed pack
                          </button>
                          <button
                            className="secondary"
                            disabled={!report.reviewed_by || busy || !canReview}
                            onClick={() => download("json")}
                          >
                            <FileJson size={16} /> JSON
                          </button>
                          <button
                            className="secondary"
                            onClick={() => window.print()}
                          >
                            Print
                          </button>
                          <button
                            className="text-button"
                            disabled={
                              !report.reviewed_by || !canPublish || busy
                            }
                            onClick={() =>
                              action(async () => {
                                const value = await api(
                                  `/v1/reports/${report.id}/publication-drafts`,
                                  "POST",
                                  {
                                    title: `Security maintenance — ${project.name}`,
                                  },
                                );
                                setPublication(value);
                                setModal("publication");
                              })
                            }
                          >
                            Draft work item <ArrowRight size={14} />
                          </button>
                        </div>
                        {report.reviewed_by && (
                          <p className="review-attribution">
                            Reviewed by {report.reviewed_by}. {report.notes}
                          </p>
                        )}
                      </div>
                    ))}
                  {tab === "conversation" && (
                    <div className="conversation">
                      <div className="section-heading">
                        <div>
                          <span className="eyebrow">PROJECT INVESTIGATION</span>
                          <h2>Ask a maintenance question</h2>
                        </div>
                        <MessageSquare size={22} />
                      </div>
                      <p className="muted">
                        Follow-ups reuse pinned evidence. Refresh starts a new
                        acquisition; neither option authorizes a code change.
                      </p>
                      <div className="conversation-log">
                        {[...(project.runs || [])].reverse().map((r: Data) => (
                          <React.Fragment key={r.id}>
                            <div className="user-message">
                              <span className="avatar">
                                {me.username[0].toUpperCase()}
                              </span>
                              <div>
                                <small>
                                  PROJECT QUESTION · {date(r.created_at)}
                                </small>
                                <p>{r.question}</p>
                              </div>
                            </div>
                            <button
                              className="assistant-message"
                              onClick={() =>
                                action(async () => {
                                  const value = await api(`/v1/runs/${r.id}`);
                                  setRun(value);
                                  setReport(value.report);
                                })
                              }
                            >
                              <div className="brand-mark small">
                                <Layers3 size={16} />
                              </div>
                              <div>
                                <strong>{outcomeLabel(r.status)}</strong>
                                <p>
                                  {r.stop_reason ||
                                    "Evidence is being collected within your project's scope."}
                                </p>
                                <span>
                                  Inspect this investigation{" "}
                                  <ArrowRight size={12} />
                                </span>
                              </div>
                            </button>
                          </React.Fragment>
                        ))}
                      </div>
                      {active && (
                        <div className="live-callout" role="status">
                          <LoaderCircle size={18} className="spin" />
                          <div>
                            <strong>Tools are working within your scope</strong>
                            <p>
                              {results.length} checkpointed tasks ·{" "}
                              {run.actions} tool attempts · {run.model_calls}{" "}
                              model calls
                            </p>
                          </div>
                          <button
                            className="secondary"
                            onClick={() =>
                              action(async () => {
                                await api(
                                  `/v1/runs/${run.id}/cancel`,
                                  "POST",
                                  {},
                                );
                                setNotice(
                                  "Cancellation requested; the current bounded operation may finish first.",
                                );
                              })
                            }
                          >
                            <Square size={12} /> Stop
                          </button>
                        </div>
                      )}
                      <form
                        className="composer"
                        onSubmit={(e) => {
                          e.preventDefault();
                          start();
                        }}
                      >
                        <label htmlFor="question">Maintenance question</label>
                        <textarea
                          id="question"
                          value={question}
                          onChange={(e) => setQuestion(e.target.value)}
                          rows={4}
                          maxLength={4000}
                        />
                        <footer>
                          <span>
                            <LockKeyhole size={12} /> Selected project only
                          </span>
                          <button
                            className="primary"
                            disabled={
                              busy || !!active || !inventory || !canInvestigate
                            }
                          >
                            <Send size={15} /> Investigate
                          </button>
                        </footer>
                      </form>
                    </div>
                  )}
                  {tab === "inventory" && (
                    <div className="inventory-panel">
                      <div className="section-heading">
                        <div>
                          <span className="eyebrow">THE RECORDED GRAPH</span>
                          <h2>Dependency inventory</h2>
                        </div>
                        <FileJson size={24} />
                      </div>
                      {inventory ? (
                        <>
                          <div className="input-provenance">
                            <span>
                              <Fingerprint size={14} /> {input?.sha256}
                            </span>
                            <span>Origin: {input?.payload.origin}</span>
                            <span>
                              Commit: {input?.payload.commit || "Not supplied"}
                            </span>
                          </div>
                          {inventory.gaps.length > 0 && (
                            <details className="qualification">
                              <summary>
                                {inventory.gaps.length} parser/graph
                                qualifications — inspect before relying on paths
                              </summary>
                              <ul>
                                {inventory.gaps.map((g: string, i: number) => (
                                  <li key={i}>{g}</li>
                                ))}
                              </ul>
                            </details>
                          )}
                          <div className="table-wrap">
                            <table>
                              <thead>
                                <tr>
                                  <th>Package / version</th>
                                  <th>Installation location</th>
                                  <th>Source</th>
                                  <th>Role</th>
                                </tr>
                              </thead>
                              <tbody>
                                {inventory.packages
                                  .slice(0, 150)
                                  .map((p: Data) => (
                                    <tr key={p.id}>
                                      <td>
                                        <strong>{p.name}</strong>
                                        <code>{p.version}</code>
                                      </td>
                                      <td>
                                        <code>{p.location}</code>
                                      </td>
                                      <td>{outcomeLabel(p.source_type)}</td>
                                      <td>
                                        {p.dev
                                          ? "Development"
                                          : "Not marked dev"}
                                        {p.optional ? " · optional" : ""}
                                      </td>
                                    </tr>
                                  ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="muted">
                            Showing up to 150 of {inventory.packages.length}{" "}
                            instances. {inventory.edges.length} recorded edges.
                            The saved snapshot contains the full parsed
                            inventory.
                          </p>
                          <details>
                            <summary>Inspect recorded graph edges</summary>
                            <pre>
                              {JSON.stringify(inventory.edges, null, 2)}
                            </pre>
                          </details>
                        </>
                      ) : (
                        <div className="empty-panel">
                          <Upload size={30} />
                          <h3>No recorded inventory yet</h3>
                          <p>Import paired manifest and npm lockfile v2/v3.</p>
                        </div>
                      )}
                    </div>
                  )}
                  {tab === "activity" && (
                    <div className="activity-panel">
                      <div className="section-heading">
                        <div>
                          <span className="eyebrow">
                            OBSERVABLE ORCHESTRATION
                          </span>
                          <h2>Routing & execution</h2>
                        </div>
                        <Network size={24} />
                      </div>
                      <label className="history-select">
                        Investigation
                        <select
                          value={run?.id || ""}
                          onChange={(e) =>
                            action(async () => {
                              const value = await api(
                                `/v1/runs/${e.target.value}`,
                              );
                              setRun(value);
                              setReport(value.report);
                            })
                          }
                        >
                          {project.runs.map((r: Data) => (
                            <option key={r.id} value={r.id}>
                              {date(r.created_at)} — {outcomeLabel(r.status)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="activity-stats">
                        <span>{run?.actions || 0} tool attempts</span>
                        <span>{run?.http_attempts || 0} HTTP attempts</span>
                        <span>{run?.model_calls || 0} model calls</span>
                        <span>Grant {run?.grant || 1} / 2</span>
                      </div>
                      <div className="timeline">
                        {run?.events.map((e: Data) => (
                          <article key={e.id}>
                            <div
                              className={`timeline-dot ${statusTone(e.outcome)}`}
                            />
                            <div>
                              <header>
                                <strong>{outcomeLabel(e.stage)}</strong>
                                <span>{date(e.created_at)}</span>
                              </header>
                              <Badge value={e.outcome} />
                              <details>
                                <summary>Inspect safe event details</summary>
                                <pre>{e.detail}</pre>
                              </details>
                            </div>
                          </article>
                        ))}
                      </div>
                      {!run && (
                        <p className="muted">
                          Start an investigation to see selected providers,
                          overlapping tool tasks and validation history.
                        </p>
                      )}
                    </div>
                  )}
                  {tab === "tools" && (
                    <div className="tools-panel">
                      <div className="section-heading">
                        <div>
                          <span className="eyebrow">
                            TRUSTED, CAPABILITY-BASED
                          </span>
                          <h2>Your tool registry</h2>
                        </div>
                        <Boxes size={24} />
                      </div>
                      <p className="muted">
                        Only installed, trusted adapters can register. Runs pin
                        a registry revision; live disablement and permissions
                        still take precedence. Enabled does not mean upstream
                        health is verified.
                      </p>
                      <code className="registry-hash">
                        Revision {short(caps?.registry.revision)}
                      </code>
                      {caps?.registry.adapters.map((adapter: Data) => (
                        <article className="tool-card" key={adapter.id}>
                          <div className="tool-icon">
                            <Terminal size={18} />
                          </div>
                          <div>
                            <h4>
                              {adapter.id}
                              <span>v{adapter.version}</span>
                            </h4>
                            <p>{adapter.capabilities.join(" · ")}</p>
                            <small>
                              {adapter.provider} / {adapter.permission} scope /
                              priority {adapter.priority}
                            </small>
                          </div>
                          {me.admin ? (
                            <label className="switch-label">
                              <input
                                type="checkbox"
                                checked={adapter.enabled}
                                onChange={(e) =>
                                  action(async () => {
                                    await api("/v1/admin/registry", "PUT", {
                                      adapter: adapter.id,
                                      enabled: e.target.checked,
                                    });
                                    setCaps(
                                      await api(
                                        `/v1/projects/${selected}/capabilities`,
                                      ),
                                    );
                                  })
                                }
                              />
                              Enabled
                            </label>
                          ) : (
                            <Badge
                              value={adapter.enabled ? "available" : "disabled"}
                            />
                          )}
                        </article>
                      ))}
                      <div className="privacy-note">
                        <LockKeyhole size={20} />
                        <span>
                          Registry availability never grants access by itself.
                          Package egress, project membership and publication
                          approval are enforced separately.
                        </span>
                      </div>
                    </div>
                  )}
                </section>
                <aside className="context-panel">
                  <section className="context-card">
                    <div className="context-card-title">
                      <Network size={17} />
                      <h3>Investigation coverage</h3>
                    </div>
                    {run ? (
                      <>
                        <div className="coverage-count">
                          <strong>
                            {
                              results.filter((r) =>
                                ["success", "no_matches"].includes(r.outcome),
                              ).length
                            }
                          </strong>
                          <span>
                            of {results.length} checkpointed tasks processed
                          </span>
                        </div>
                        <progress
                          aria-label="Processed task proportion"
                          max={Math.max(results.length, 1)}
                          value={
                            results.filter((r) =>
                              ["success", "no_matches"].includes(r.outcome),
                            ).length
                          }
                        />
                        <p className="tiny-muted">
                          This is task progress, not a security or completeness
                          score.
                        </p>
                        <div className="source-checks">
                          {results.slice(0, 12).map((r, i) => (
                            <button
                              key={i}
                              disabled={!r.snapshot_id}
                              onClick={() =>
                                action(async () =>
                                  setSnapshot(
                                    await api(`/v1/snapshots/${r.snapshot_id}`),
                                  ),
                                )
                              }
                            >
                              <span
                                className={`source-dot ${statusTone(r.outcome)}`}
                              />
                              <span>
                                <strong>
                                  {r.adapter ||
                                    r.request?.capability ||
                                    "Source task"}
                                </strong>
                                <small>{outcomeLabel(r.outcome)}</small>
                              </span>
                              <ArrowUpRight size={13} />
                            </button>
                          ))}
                        </div>
                        {results.length > 12 && (
                          <button
                            className="text-button"
                            onClick={() => setTab("activity")}
                          >
                            See all {results.length} tasks{" "}
                            <ArrowRight size={13} />
                          </button>
                        )}
                      </>
                    ) : (
                      <p className="muted">
                        Source checks will appear here as an investigation
                        proceeds.
                      </p>
                    )}
                  </section>
                  <section className="context-card">
                    <div className="context-card-title">
                      <Fingerprint size={17} />
                      <h3>Evidence scope</h3>
                    </div>
                    <dl>
                      <dt>Input acquired</dt>
                      <dd>{date(input?.created_at)}</dd>
                      <dt>Public-query grants</dt>
                      <dd>
                        {project.policy.public_packages.length} package names
                      </dd>
                      <dt>Model egress</dt>
                      <dd>
                        {project.policy.model_egress
                          ? "Explicitly permitted"
                          : "Not permitted"}
                      </dd>
                      <dt>Code execution</dt>
                      <dd>Never performed</dd>
                      <dt>Upgrade verification</dt>
                      <dd>Pending human/CI evidence</dd>
                    </dl>
                    {inventory && (
                      <button
                        className="text-button"
                        disabled={busy || !!active || !canInvestigate}
                        onClick={() => start(true)}
                      >
                        <RefreshCw size={13} /> Refresh source evidence
                      </button>
                    )}
                    {run?.status === "partial" && run.grant < 2 && (
                      <button
                        className="secondary full"
                        disabled={busy || !canInvestigate}
                        onClick={() =>
                          action(async () => {
                            const value = await api(
                              `/v1/runs/${run.id}/resume`,
                              "POST",
                              {},
                              { "Idempotency-Key": key() },
                            );
                            setRun(value);
                            setNotice(
                              "Explicit second grant queued. Existing evidence and cumulative counters retained.",
                            );
                          })
                        }
                      >
                        Resume with bounded grant <ArrowRight size={13} />
                      </button>
                    )}
                  </section>
                  <section className="context-note">
                    <ShieldQuestion size={20} />
                    <h3>A match is not exposure.</h3>
                    <p>
                      Public advisories describe known package concerns. They do
                      not establish application reachability, successful
                      remediation or compatibility.
                    </p>
                    <button onClick={() => setModal("about")}>
                      Understand the boundaries <ArrowUpRight size={12} />
                    </button>
                  </section>
                </aside>
              </div>
            </>
          )}
        </main>
        <footer className="workspace-footer">
          <span>
            PATCHDESK <span className="footer-separator">/</span> MAINTENANCE,
            MADE ACCOUNTABLE.
          </span>
          <span>Source evidence. Explicit scope. Human review.</span>
        </footer>
      </div>
      {modal === "project" && (
        <Modal title="A new client project" onClose={() => setModal("")}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action(async () => {
                const p = await api("/v1/projects", "POST", { name, client });
                await refreshList();
                setSelected(p.id);
                setModal("");
              });
            }}
          >
            <label>
              Client name
              <input
                value={client}
                onChange={(e) => setClient(e.target.value)}
                required
                minLength={2}
                placeholder="Acme Studio"
              />
            </label>
            <label>
              Project name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                minLength={2}
                placeholder="Customer API"
              />
            </label>
            <p className="muted">
              Public queries and model egress start denied. You choose exactly
              what this project can share.
            </p>
            <button className="primary full" disabled={busy}>
              Create project <ArrowRight size={16} />
            </button>
          </form>
        </Modal>
      )}
      {modal === "import" && project && (
        <Modal
          title="Bring the actual dependency graph"
          onClose={() => setModal("")}
        >
          <p className="muted">
            Select package.json and package-lock.json v2/v3 from the same
            project snapshot. Files stay in this project's local store. No
            packages are installed or executed.
          </p>
          <label className="file-drop">
            <Upload size={28} />
            <strong>Select the two JSON files</strong>
            <span>Up to 10 MiB each · npm lockfile v2 / v3</span>
            <input
              type="file"
              accept=".json,application/json"
              multiple
              onChange={(e) =>
                action(async () => {
                  let m: Data | null = null,
                    l: Data | null = null;
                  const names: string[] = [];
                  for (const file of Array.from(e.target.files || [])) {
                    if (file.size > 10 * 1024 * 1024)
                      throw new Error("File exceeds 10 MiB");
                    const parsed = JSON.parse(await file.text());
                    if (file.name === "package.json") m = parsed;
                    else if (file.name === "package-lock.json") l = parsed;
                    else
                      throw new Error(
                        "Select files named package.json and package-lock.json",
                      );
                    names.push(file.name);
                  }
                  setManifest(m);
                  setLockfile(l);
                  setFileNames(names);
                })
              }
            />
          </label>
          {fileNames.map((f) => (
            <p className="selected-file" key={f}>
              <FileJson size={15} />
              {f}
              <Check size={15} />
            </p>
          ))}
          <button
            className="primary full"
            disabled={busy || !manifest || !lockfile}
            onClick={() =>
              action(async () => {
                await api(`/v1/projects/${selected}/inputs`, "POST", {
                  manifest,
                  lockfile,
                  origin: "uploaded",
                });
                await loadProject(selected);
                await refreshList();
                setModal("");
                setTab("inventory");
                setNotice(
                  "Snapshot imported. Review the graph and explicitly configure egress before investigating.",
                );
              })
            }
          >
            Import scoped snapshot <ArrowRight size={15} />
          </button>
          {project.policy.repository && (
            <div className="repository-import">
              <p>
                Or read the configured repository at its current HEAD, pinned to
                a commit.
              </p>
              <button
                className="secondary full"
                disabled={busy}
                onClick={() =>
                  action(async () => {
                    await api(
                      `/v1/projects/${selected}/repository-snapshots`,
                      "POST",
                      { ref: "HEAD" },
                    );
                    await loadProject(selected);
                    setModal("");
                  })
                }
              >
                <GitBranch size={15} /> Read {project.policy.repository}
              </button>
            </div>
          )}
        </Modal>
      )}
      {modal === "policy" && project && (
        <Modal
          title="Explicit scope & permissions"
          onClose={() => setModal("")}
          wide
        >
          <p className="muted">
            Only the project owner can change this policy. Public package
            identities and model context use separate egress grants. Changes
            invalidate older publication approvals.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action(async () => {
                const value = await api(
                  `/v1/projects/${selected}/policy`,
                  "PUT",
                  {
                    expected_revision: project.revision,
                    public_packages: packageList.split(/\s+/).filter(Boolean),
                    model_egress: modelEgress,
                    repository: repo,
                    repository_id: repoId ? Number(repoId) : null,
                    node_version: nodeVersion,
                    connector_epoch: project.policy.connector_epoch,
                  },
                );
                setProject(value);
                setCaps(await api(`/v1/projects/${selected}/capabilities`));
                setModal("");
                setNotice("Project policy saved with a new revision.");
              });
            }}
          >
            <label>
              Approved public package names — one per line
              <textarea
                rows={5}
                value={packageList}
                onChange={(e) => setPackageList(e.target.value)}
                placeholder="Each listed identity may be queried against enabled public APIs."
              />
            </label>
            {inventory && (
              <button
                type="button"
                className="text-button"
                onClick={() =>
                  setPackageList(
                    [
                      ...new Set(
                        inventory.packages
                          .filter(
                            (p: Data) => p.source_type === "public_registry",
                          )
                          .map((p: Data) => p.name),
                      ),
                    ]
                      .sort()
                      .join("\n"),
                  )
                }
              >
                List registry-backed names for explicit review{" "}
                <ArrowRight size={12} />
              </button>
            )}
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={modelEgress}
                onChange={(e) => setModelEgress(e.target.checked)}
              />
              <span>
                I authorize minimized evidence and this project's question to be
                sent through Codex for model inference. This is not offline
                inference.
              </span>
            </label>
            <div className="field-grid">
              <label>
                Configured GitHub repository
                <input
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  placeholder="owner/repository"
                />
              </label>
              <label>
                Immutable repository numeric ID
                <input
                  value={repoId}
                  onChange={(e) => setRepoId(e.target.value)}
                  placeholder="Required for repository access"
                />
              </label>
            </div>
            <label>
              Deployment Node version, if verified
              <input
                value={nodeVersion}
                onChange={(e) => setNodeVersion(e.target.value)}
                placeholder="e.g. 20.19.0; leave empty if unknown"
              />
            </label>
            <button
              className="primary full"
              disabled={busy || project.owner !== me.username}
            >
              Save explicit policy <Check size={16} />
            </button>
          </form>
          <div className="members-section">
            <h3>Project membership</h3>
            {project.members.map((m: Data) => (
              <p key={m.username}>
                <Users size={14} />
                {m.username}
                <span>{m.roles.join(", ") || "No roles"}</span>
              </p>
            ))}
            <label>
              Existing workspace username
              <input
                value={member}
                onChange={(e) => setMember(e.target.value)}
              />
            </label>
            <div className="role-options">
              {["analyst", "reviewer", "publisher"].map((r) => (
                <label className="checkbox-label" key={r}>
                  <input
                    type="checkbox"
                    checked={memberRoles.includes(r)}
                    onChange={(e) =>
                      setMemberRoles(
                        e.target.checked
                          ? [...memberRoles, r]
                          : memberRoles.filter((v) => v !== r),
                      )
                    }
                  />
                  {r}
                </label>
              ))}
            </div>
            <button
              className="secondary full"
              disabled={busy || !member || project.owner !== me.username}
              onClick={() =>
                action(async () => {
                  await api(`/v1/projects/${selected}/members`, "PUT", {
                    username: member,
                    roles: memberRoles,
                  });
                  await loadProject(selected);
                  setNotice(
                    "Membership updated; affected grants are rechecked at dispatch.",
                  );
                })
              }
            >
              Set project roles
            </button>
          </div>
        </Modal>
      )}
      {modal === "review" && report && (
        <Modal
          title="Review this exact maintenance pack"
          onClose={() => setModal("")}
          wide
        >
          <div className="review-identity">
            <Fingerprint size={15} />
            Report {short(report.id)} · revision {report.revision}
            <Badge value={payload.status} />
          </div>
          <label>
            Reviewer notes
            <textarea
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={4000}
            />
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={editSummary}
              onChange={(e) => setEditSummary(e.target.checked)}
            />
            Edit the qualified summary (creates a new partial report revision)
          </label>
          {editSummary && (
            <label>
              Summary
              <textarea
                rows={5}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                maxLength={2000}
              />
            </label>
          )}
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
            />
            <span>
              I acknowledge unresolved coverage/conflicts and unperformed
              compatibility/security verification. These limitations remain in
              exports.
            </span>
          </label>
          <button
            className="primary full"
            disabled={
              busy || (!ack && (payload.status !== "completed" || editSummary))
            }
            onClick={() =>
              action(async () => {
                const value = await api(
                  `/v1/reports/${report.id}/reviews`,
                  "POST",
                  {
                    expected_revision: report.revision,
                    notes,
                    acknowledge_limits: ack,
                    ...(editSummary
                      ? { narrative: { ...payload.narrative, summary } }
                      : {}),
                  },
                );
                setReport(value);
                setModal("");
                setNotice(
                  "Exact report revision reviewed. Source limitations are unchanged.",
                );
              })
            }
          >
            <CheckCheck size={16} /> Save review
          </button>
        </Modal>
      )}
      {modal === "publication" && publication && (
        <Modal
          title="A deliberate external action"
          onClose={() => setModal("")}
          wide
        >
          <div className="qualification">
            <LockKeyhole size={20} />
            <div>
              <strong>Publishing is separate from investigating</strong>
              <p>
                Inspect this exact title, body and target. Approval expires
                after 15 minutes and does not authorize code changes.
              </p>
            </div>
          </div>
          <dl>
            <dt>Repository</dt>
            <dd>
              {publication.payload.repository} / ID{" "}
              {publication.payload.repository_id}
            </dd>
            <dt>Payload SHA-256</dt>
            <dd>
              <code>{publication.payload_hash}</code>
            </dd>
          </dl>
          <Badge value={publication.status} />
          <h3>{publication.payload.title}</h3>
          <pre className="publication-preview">{publication.payload.body}</pre>
          {publicationAction(publication.status) === "approve" && (
            <button
              className="primary full"
              disabled={busy}
              onClick={() =>
                action(async () =>
                  setPublication(
                    await api(
                      `/v1/publications/${publication.id}/approve`,
                      "POST",
                      {
                        expected_revision: publication.revision,
                        payload_hash: publication.payload_hash,
                      },
                    ),
                  ),
                )
              }
            >
              <CheckCheck size={16} /> Approve only this draft and destination
            </button>
          )}
          {publicationAction(publication.status) === "dispatch" && (
            <button
              className="primary full"
              disabled={busy || !caps?.publisher_enabled}
              onClick={() =>
                action(async () =>
                  setPublication(
                    await api(
                      `/v1/publications/${publication.id}/dispatch`,
                      "POST",
                      {},
                    ),
                  ),
                )
              }
            >
              <Send size={16} /> Publish the approved GitHub issue
            </button>
          )}
          {publicationAction(publication.status) === "reconcile" && (
            <button
              className="secondary full"
              disabled={busy}
              onClick={() =>
                action(async () =>
                  setPublication(
                    await api(
                      `/v1/publications/${publication.id}/reconcile`,
                      "POST",
                      {},
                    ),
                  ),
                )
              }
            >
              Reconcile unknown outcome — do not resend
            </button>
          )}
          {!caps?.publisher_enabled && (
            <p className="muted">
              External publisher is disabled or quarantined. A draft/approval
              does not create an issue.
            </p>
          )}
          {publication.receipt && (
            <a
              className="advisory-link"
              href={publication.receipt.url}
              target="_blank"
              rel="noreferrer"
            >
              Open verified receipt <ArrowUpRight size={14} />
            </a>
          )}
        </Modal>
      )}
      {modal === "user" && (
        <Modal
          title="Add a scoped workspace actor"
          onClose={() => setModal("")}
        >
          <label>
            New username
            <input value={member} onChange={(e) => setMember(e.target.value)} />
          </label>
          <label>
            Initial password — at least 12 characters
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
          </label>
          <p className="muted">
            The new actor starts with no access to any existing project. Grant
            specific project roles separately.
          </p>
          <button
            className="primary full"
            disabled={busy || !member || newPassword.length < 12}
            onClick={() =>
              action(async () => {
                await api("/v1/users", "POST", {
                  username: member,
                  password: newPassword,
                  admin: false,
                });
                setNewPassword("");
                setModal("");
                setNotice("User created without project access.");
              })
            }
          >
            <Users size={16} /> Create actor
          </button>
        </Modal>
      )}
      {modal === "about" && (
        <Modal title="Evidence, with boundaries" onClose={() => setModal("")}>
          <p>
            PatchDesk orchestrates scoped reads and prepares reviewable
            maintenance work. Recorded package/advisory matches do not establish
            application exploitability.
          </p>
          <p>
            Release candidates have not been installed, built, tested or
            deployed. EPSS is a general threat signal, not this client's
            compromise probability. Missing data is not a clean result.
          </p>
          <p>
            Only your authorized projects are accessible. Public lookup, model
            egress and external publication each have explicit permission
            boundaries.
          </p>
          <div className="privacy-note">
            <ShieldCheck size={22} />
            <span>
              Review the source snapshots, conflicts, coverage and stop reason
              before acting on any report.
            </span>
          </div>
        </Modal>
      )}
      {snapshot && (
        <Modal
          title="Captured source evidence"
          onClose={() => setSnapshot(null)}
          wide
        >
          <div className="review-identity">
            <Fingerprint size={16} />
            {snapshot.id}
          </div>
          <dl>
            <dt>Acquired</dt>
            <dd>{date(snapshot.created_at)}</dd>
            <dt>Payload SHA-256</dt>
            <dd>
              <code>{snapshot.sha256}</code>
            </dd>
          </dl>
          <p className="muted">
            Original captured fields and normalized records. Prompt sampling
            does not remove records from this stored snapshot.
          </p>
          <pre className="evidence-json">
            {JSON.stringify(snapshot.payload, null, 2)}
          </pre>
        </Modal>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
