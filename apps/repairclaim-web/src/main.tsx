import React, { useEffect, useState, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  ArrowLeft,
  ShieldCheck,
  CarFront,
  FolderOpen,
  FileCheck2,
  Clock3,
  Bell,
  Plus,
  LogOut,
  LockKeyhole,
  FileText,
  Search,
  ChevronRight,
} from "lucide-react";
import { api, ApiError, download, image, setCsrf, upload } from "./api";
import {
  aware,
  documentReviewNotice,
  factInput,
  label,
  nextAction,
  packetAccess,
  currencies,
  outcomeKinds,
  type Item,
} from "./domain";
import "./style.css";

type Fields = Record<string, string>;
type Input = {
  name: string;
  label: string;
  type?: string;
  options?: string[];
  optionLabels?: Record<string, string>;
  required?: boolean;
  value?: string;
  hint?: string;
};
function Form({
  fields,
  submit,
  onSubmit,
  children,
}: {
  fields: Input[];
  submit: string;
  onSubmit: (values: Fields) => Promise<void>;
  children?: React.ReactNode;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(
          new FormData(e.currentTarget),
        ) as Fields;
        setBusy(true);
        setError("");
        try {
          await onSubmit(data);
        } catch (err) {
          setError((err as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      {fields.map((f) => (
        <label key={f.name}>
          {f.label}
          {f.options ? (
            <select name={f.name} defaultValue={f.value || f.options[0]}>
              {f.options.map((o) => (
                <option key={o} value={o}>
                  {f.optionLabels?.[o] || label(o)}
                </option>
              ))}
            </select>
          ) : f.type === "textarea" ? (
            <textarea
              name={f.name}
              maxLength={2000}
              required={f.required !== false}
              defaultValue={f.value}
            />
          ) : (
            <input
              name={f.name}
              type={f.type || "text"}
              required={f.required !== false}
              defaultValue={f.value}
              maxLength={f.type === "password" ? 256 : 200}
              step={f.type === "number" ? "0.01" : undefined}
            />
          )}{" "}
          {f.hint && <small>{f.hint}</small>}
        </label>
      ))}
      {children}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button disabled={busy}>
        {busy ? "Saving…" : submit}
        <ArrowUpRight size={16} />
      </button>
    </form>
  );
}
function Badge({
  children,
  tone = "",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function Empty({ children }: { children: React.ReactNode }) {
  return <p className="empty">{children}</p>;
}
function Detail({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <details>
      <summary>{title}</summary>
      <div className="details-body">{children}</div>
    </details>
  );
}
function App() {
  const [user, setUser] = useState<Item | null>(null),
    [loading, setLoading] = useState(true),
    [cases, setCases] = useState<Item[]>([]),
    [vehicles, setVehicles] = useState<Item[]>([]),
    [caps, setCaps] = useState<Item>({
      registry: { status: "unavailable", epoch: 0, sources: [] },
    }),
    [alerts, setAlerts] = useState<Item[]>([]),
    [selected, setSelected] = useState(""),
    [workspace, setWorkspace] = useState<Item | null>(null),
    [tab, setTab] = useState("Overview"),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  async function refresh(id = selected) {
    const [c, v, k, n] = await Promise.all([
      api("/cases"),
      api("/vehicles"),
      api("/capabilities"),
      api("/notifications"),
    ]);
    setCases(c);
    setVehicles(v);
    setCaps(k);
    setAlerts(n);
    if (id) {
      const value = await api(`/cases/${id}/workspace`);
      if (selectedRef.current === id) setWorkspace(value);
    }
  }
  async function action(work: () => Promise<unknown>, message = "Saved.") {
    setError("");
    try {
      await work();
      await refresh();
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
      if (e instanceof ApiError && e.status === 401) {
        setUser(null);
        setCsrf("");
      }
    }
  }
  useEffect(() => {
    api("/me")
      .then(async (me) => {
        setCsrf(me.csrf_token);
        setUser(me);
        await refresh("");
      })
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) setError(e.message);
      })
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!user || !selected) return;
    let active = true;
    setWorkspace(null);
    api(`/cases/${selected}/workspace`)
      .then((value) => {
        if (active) setWorkspace(value);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected]);
  useEffect(() => {
    if (!user) return;
    const timer = setInterval(() => {
      refresh().catch((e) => {
        setError(e.message);
        if (e instanceof ApiError && e.status === 401) setUser(null);
      });
    }, 5000);
    return () => clearInterval(timer);
  }, [selected, user]);
  const brand = (
    <div className="brand">
      <span className="brand-icon">
        <ShieldCheck size={23} />
      </span>
      <span>
        repairclaim<span className="brand-dot">.</span>
      </span>
    </div>
  );
  if (loading)
    return <div className="center">Opening your private workspace…</div>;
  if (!user)
    return (
      <main className="login">
        <section className="login-story">
          {brand}
          <Badge>YOUR REPAIR. ON RECORD.</Badge>
          <h1>
            A repair bill shouldn’t
            <br />
            be the end of
            <br />
            <em>the story.</em>
          </h1>
          <p>
            Bring the paperwork. Find the documented conditions. Make your next
            conversation count.
          </p>
          <div className="trust">
            <ShieldCheck /> Private by default · Nothing sent without you
          </div>
        </section>
        <section className="login-form">
          <small>YOUR PRIVATE CASEWORK DESK</small>
          <h2>Welcome back.</h2>
          <p>Sign in to pick up where you left off.</p>
          <Form
            fields={[
              { name: "username", label: "Username" },
              { name: "password", label: "Password", type: "password" },
            ]}
            submit="Open my workspace"
            onSubmit={async (v) => {
              const session = await api("/sessions", v);
              setCsrf(session.csrf_token);
              setUser(await api("/me"));
              await refresh("");
            }}
          />
          <p className="muted">
            Accounts are provisioned by the operator. No manufacturer or portal
            passwords are collected.
          </p>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
        </section>
      </main>
    );
  const w = workspace,
    own = w?.role === "owner",
    editable = own || w?.role === "editor";
  const casePath = `/cases/${selected}`;
  return (
    <div className="shell">
      <aside>
        {brand}
        <div className="side-label">YOUR WORKSPACE</div>
        <button
          className={!selected ? "nav active" : "nav"}
          onClick={() => {
            setSelected("");
            setWorkspace(null);
          }}
        >
          <CarFront size={19} />
          My garage<span>{cases.length}</span>
        </button>
        <div className="side-note">
          <LockKeyhole size={21} />
          <strong>You stay in control.</strong>
          <p>
            Evidence stays private. Every packet needs your approval. You submit
            it yourself.
          </p>
        </div>
        <button
          className="nav logout"
          onClick={() =>
            action(async () => {
              await api("/sessions/current", undefined, "DELETE");
              setCsrf("");
              setUser(null);
              setSelected("");
              setWorkspace(null);
            }, "Signed out.")
          }
        >
          <LogOut size={18} />
          Sign out
        </button>
      </aside>
      <div className="main">
        <header>
          <span>PERSONAL REPAIR CASEWORK</span>
          <div>
            <Bell size={17} />
            {alerts.length > 0 && <Badge>{alerts.length} updates</Badge>}
            <span className="avatar">
              {user.username.slice(0, 1).toUpperCase()}
            </span>
            <span>{user.username}</span>
          </div>
        </header>
        <div className="content">
          {error && (
            <div className="error" role="alert">
              {error}
              <button className="text-button" onClick={() => setError("")}>
                Dismiss
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
              <button className="text-button" onClick={() => setNotice("")}>
                Dismiss
              </button>
            </div>
          )}
          {!selected ? (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    A LITTLE CLARITY GOES A LONG WAY
                  </div>
                  <h1>Your garage.</h1>
                  <p>
                    A clear record. A considered next step. All in one place.
                  </p>
                </div>
                <Badge tone="green">
                  <ShieldCheck size={14} />
                  Private workspace
                </Badge>
              </div>
              <div className="hero-card">
                <div>
                  <Badge>FROM PAPERWORK TO A PLAN</Badge>
                  <h2>
                    Know what to ask.
                    <br />
                    <em>Keep the evidence.</em>
                  </h2>
                  <p>
                    Turn a repair into an organised case, with sources you can
                    inspect and correspondence you control.
                  </p>
                  <a href="#new-case">
                    Start a repair case <ArrowUpRight size={16} />
                  </a>
                </div>
                <div className="hero-art" aria-hidden="true">
                  <div className="paper">
                    <FileCheck2 size={32} />
                    <div />
                    <div />
                    <div />
                    <span>Evidence, not guesswork.</span>
                  </div>
                  <span className="art-stamp">
                    <ShieldCheck />
                    YOUR CALL. ALWAYS.
                  </span>
                </div>
              </div>
              <div className="section-heading">
                <h2>
                  Repair cases <span>{cases.length}</span>
                </h2>
                <small>US · Honda · reviewed inventory only</small>
              </div>
              <div className="case-grid">
                {cases.map((c) => (
                  <button
                    className="case-card"
                    key={c.id}
                    onClick={() => {
                      setTab("Overview");
                      setSelected(c.id);
                    }}
                  >
                    <div>
                      <span className="case-icon">
                        <CarFront />
                      </span>
                      <Badge>{label(c.lifecycle)}</Badge>
                    </div>
                    <h3>{c.title}</h3>
                    <p>
                      {vehicles.find((v) => v.id === c.vehicle_id)?.model ||
                        "Shared vehicle"}{" "}
                      · Revision {c.revision}
                    </p>
                    <footer>
                      <span>Open case file</span>
                      <ChevronRight size={19} />
                    </footer>
                  </button>
                ))}
                {!cases.length && (
                  <Empty>
                    Your first case starts here. Add your vehicle, then open a
                    repair case below.
                  </Empty>
                )}
              </div>
              {alerts.length > 0 && (
                <section className="card">
                  <h2>Evidence updates</h2>
                  {alerts.map((n) => (
                    <article className="record" key={n.id}>
                      <Badge>{label(n.change.type)}</Badge>
                      <h3>
                        {n.change.family}: {n.change.old_revision || "new"} →{" "}
                        {n.change.new_revision}
                      </h3>
                      <p>{n.change.label}</p>
                      <Detail title="Inspect the change">
                        <pre>{JSON.stringify(n.change, null, 2)}</pre>
                      </Detail>
                      <button
                        className="secondary"
                        onClick={() =>
                          action(
                            () => api(`/notifications/${n.id}/acknowledge`, {}),
                            "Update acknowledged.",
                          )
                        }
                      >
                        Acknowledge
                      </button>
                    </article>
                  ))}
                </section>
              )}
              <div className="two-col" id="new-case">
                <section className="card">
                  <h2>Add a vehicle</h2>
                  <p>
                    The supported first release covers US Honda vehicles.
                    Coverage is never inferred from the badge alone.
                  </p>
                  <Form
                    submit="Add to garage"
                    fields={[
                      { name: "model", label: "Honda model" },
                      {
                        name: "model_year",
                        label: "Model year",
                        type: "number",
                        value: "2018",
                      },
                    ]}
                    onSubmit={async (v) => {
                      await api("/vehicles", {
                        make: "Honda",
                        model: v.model,
                        model_year: Number(v.model_year),
                        jurisdiction: "US",
                      });
                      await refresh();
                    }}
                  />
                </section>
                <section className="card">
                  <h2>Start a repair case</h2>
                  {vehicles.length ? (
                    <Form
                      submit="Create case"
                      fields={[
                        {
                          name: "vehicle_id",
                          label: "Vehicle",
                          options: vehicles.map((v) => v.id),
                          optionLabels: Object.fromEntries(
                            vehicles.map((v) => [
                              v.id,
                              `${v.make} ${v.model} · ${v.model_year}`,
                            ]),
                          ),
                        },
                        {
                          name: "title",
                          label: "Case title",
                          hint: "For example: Air conditioning repair",
                        },
                      ]}
                      onSubmit={async (v) => {
                        const c = await api("/cases", v);
                        await refresh();
                        setSelected(c.id);
                        setTab("Overview");
                      }}
                    >
                      <small>
                        {vehicles
                          .map((v) => `${v.id}: ${v.model} ${v.model_year}`)
                          .join(" · ")}
                      </small>
                    </Form>
                  ) : (
                    <Empty>Add a vehicle first.</Empty>
                  )}
                </section>
              </div>
              <Detail title="Join a family case">
                <Form
                  submit="Accept one-use invitation"
                  fields={[{ name: "invitation", label: "Invitation token" }]}
                  onSubmit={async (v) => {
                    const item = await api("/invitations/accept", v);
                    await refresh();
                    setSelected(item.case_id);
                  }}
                />
              </Detail>
              <Detail title="Account privacy">
                <p>
                  Erase all owned cases, vehicle details, sessions and
                  credentials. External downloads cannot be recalled. Restores
                  require the current erasure ledger.
                </p>
                <Form
                  submit="Permanently erase my account"
                  fields={[
                    { name: "confirmation", label: "Type DELETE MY ACCOUNT" },
                  ]}
                  onSubmit={async (v) => {
                    await api("/account/erase", v);
                    setUser(null);
                    setCsrf("");
                  }}
                />
              </Detail>
            </>
          ) : !w ? (
            <Empty>Loading your case file…</Empty>
          ) : (
            <>
              <button
                className="text-button back"
                onClick={() => {
                  setSelected("");
                  setWorkspace(null);
                }}
              >
                <ArrowLeft size={15} />
                My garage
              </button>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    REPAIR CASE / REVISION {w.revision}
                  </div>
                  <h1>{w.title}</h1>
                  <p>
                    {label(w.role)} access · Nothing submitted automatically
                  </p>
                </div>
                <Badge>{label(w.lifecycle)}</Badge>
              </div>
              <nav className="tabs" aria-label="Case sections">
                {[
                  "Overview",
                  "Documents & facts",
                  "Coverage",
                  "Packet desk",
                  "Timeline",
                  "Privacy",
                ].map((t) => (
                  <button
                    className={tab === t ? "selected" : ""}
                    onClick={() => setTab(t)}
                    key={t}
                  >
                    {t}
                  </button>
                ))}
              </nav>
              {tab === "Overview" && (
                <>
                  <section className="next-step">
                    <span className="step-icon">
                      <ArrowUpRight />
                    </span>
                    <div>
                      <small>YOUR NEXT STEP</small>
                      <h2>{nextAction(w.jobs, caps.registry.status)}</h2>
                      <button
                        className="text-button"
                        onClick={() => setTab("Documents & facts")}
                      >
                        Review the case evidence <ChevronRight size={16} />
                      </button>
                    </div>
                  </section>
                  <div className="metric-grid">
                    {[
                      ["Documents", w.documents.length],
                      [
                        "Confirmed / reported facts",
                        w.snapshot.facts.filter(
                          (f: Item) => f.status !== "extracted",
                        ).length,
                      ],
                      ["Packets", w.packets.length],
                    ].map(([k, v]) => (
                      <div className="metric" key={k}>
                        <small>{k}</small>
                        <strong>{v}</strong>
                      </div>
                    ))}
                  </div>
                  <section className="card">
                    <h2>What this desk can—and cannot—tell you</h2>
                    <p>
                      Check facts against an operator-reviewed official
                      programme inventory. Inspect every condition, keep missing
                      evidence visible, and prepare a factual enquiry.
                    </p>
                    <p className="muted">
                      A service bulletin is not a coverage promise. A potential
                      match is not manufacturer approval. No negative result
                      means an exhaustive search of every programme.
                    </p>
                    <div className="pipeline">
                      <span>
                        <FolderOpen />
                        Gather
                      </span>
                      <ChevronRight />
                      <span>
                        <Search />
                        Check
                      </span>
                      <ChevronRight />
                      <span>
                        <FileCheck2 />
                        Review
                      </span>
                      <ChevronRight />
                      <span>
                        <ArrowUpRight />
                        You submit
                      </span>
                    </div>
                  </section>
                </>
              )}
              {tab === "Documents & facts" && (
                <Evidence
                  w={w}
                  editable={editable}
                  casePath={casePath}
                  action={action}
                />
              )}
              {tab === "Coverage" && (
                <Coverage
                  w={w}
                  caps={caps}
                  editable={editable}
                  own={own}
                  casePath={casePath}
                  action={action}
                />
              )}
              {tab === "Packet desk" && (
                <Packets
                  w={w}
                  own={own}
                  caps={caps}
                  casePath={casePath}
                  action={action}
                />
              )}
              {tab === "Timeline" && (
                <Timeline w={w} own={own} casePath={casePath} action={action} />
              )}
              {tab === "Privacy" && (
                <section className="card">
                  <h2>You control the case.</h2>
                  <p>
                    Encrypted private content · Case-scoped access · 180-day
                    retention, extended by user edits only. Monitoring is a
                    separate, revocable purpose.
                  </p>
                  {own ? (
                    <>
                      <button
                        className="secondary"
                        onClick={() =>
                          action(
                            () =>
                              download(
                                casePath + "/export",
                                "repairclaim-private-export.zip",
                              ),
                            "Private export downloaded. Not approved correspondence.",
                          )
                        }
                      >
                        Export private case data
                      </button>
                      <Detail title="Invite a family member">
                        <Form
                          submit="Create one-use invitation"
                          fields={[
                            {
                              name: "role",
                              label: "Permission",
                              options: ["viewer", "editor"],
                            },
                          ]}
                          onSubmit={async (v) => {
                            const invite = await api(
                              casePath + "/invitations",
                              v,
                            );
                            window.prompt(
                              "Copy this one-use token (valid 24 hours). Only share with your intended recipient.",
                              invite.token,
                            );
                            await action(async () => {}, "Invitation created.");
                          }}
                        />
                        <p>
                          Invitations apply to this case only and grants expire
                          after 90 days.
                        </p>
                        {w.grants.map((g: Item) => (
                          <p key={g.user_id}>
                            {g.username} · {g.role} · until{" "}
                            {new Date(g.expires * 1000).toLocaleDateString()}{" "}
                            <button
                              className="text-button"
                              onClick={() =>
                                action(
                                  () =>
                                    api(
                                      casePath + `/grants/${g.user_id}`,
                                      undefined,
                                      "DELETE",
                                    ),
                                  "Access revoked.",
                                )
                              }
                            >
                              Revoke access
                            </button>
                          </p>
                        ))}
                        {w.invitations
                          .filter((i: Item) => i.status === "available")
                          .map((i: Item) => (
                            <p key={i.id}>
                              Unclaimed {i.role} invitation ·{" "}
                              {new Date(i.expires * 1000).toLocaleString()}{" "}
                              <button
                                className="text-button"
                                onClick={() =>
                                  action(
                                    () =>
                                      api(
                                        `/invitations/${i.id}`,
                                        undefined,
                                        "DELETE",
                                      ),
                                    "Invitation revoked.",
                                  )
                                }
                              >
                                Revoke invitation
                              </button>
                            </p>
                          ))}
                        <Form
                          submit="Revoke access"
                          fields={[
                            { name: "user_id", label: "Recipient user ID" },
                          ]}
                          onSubmit={async (v) => {
                            await api(
                              casePath +
                                `/grants/${encodeURIComponent(v.user_id)}`,
                              undefined,
                              "DELETE",
                            );
                            await action(async () => {});
                          }}
                        />
                      </Detail>
                      <Detail title="Retrospective monitoring consent">
                        <p>
                          Allow checks against newly reviewed programme versions
                          for this repair for 90 days. Notifications remain in
                          this app. No background model calls or automatic
                          claims.
                        </p>
                        {w.monitoring.map((m: Item) => (
                          <p key={m.id}>
                            {label(m.status)} · expires{" "}
                            {new Date(m.expires * 1000).toLocaleDateString()}
                          </p>
                        ))}
                        <button
                          onClick={() =>
                            action(
                              () =>
                                api(`/vehicles/${w.vehicle_id}/monitoring`, {
                                  case_ids: [w.id],
                                  ttl: 90 * 86400,
                                }),
                              "Monitoring consent saved for this case.",
                            )
                          }
                        >
                          Consent for 90 days
                        </button>
                        <button
                          className="secondary"
                          onClick={() =>
                            action(
                              () =>
                                api(
                                  `/vehicles/${w.vehicle_id}/monitoring`,
                                  undefined,
                                  "DELETE",
                                ),
                              "Monitoring revoked for this vehicle.",
                            )
                          }
                        >
                          Revoke vehicle monitoring
                        </button>
                      </Detail>
                      <Detail title="Pause, close or reopen">
                        <Form
                          submit="Update case state"
                          fields={[
                            {
                              name: "state",
                              label: "State",
                              options: ["paused", "closed", "fact_review"],
                            },
                          ]}
                          onSubmit={async (v) => {
                            await api(casePath + "/lifecycle", {
                              ...v,
                              expected_revision: w.revision,
                            });
                            await action(async () => {});
                          }}
                        />
                        <p>
                          Pausing/closing cancels queued work and invalidates
                          old approvals. Reopening does not reset job budgets.
                        </p>
                      </Detail>
                      <Detail title="Permanently erase this case">
                        <p>
                          Deletes encrypted records, attachments and case keys.
                          Keep the erasure ledger with every restore. Copies you
                          downloaded or sent yourself cannot be recalled.
                        </p>
                        <Form
                          submit="Permanently erase case"
                          fields={[
                            {
                              name: "confirmation",
                              label: "Type DELETE THIS CASE",
                            },
                          ]}
                          onSubmit={async (v) => {
                            if (v.confirmation !== "DELETE THIS CASE")
                              throw Error("Confirmation did not match.");
                            const response = await fetch(image(casePath), {
                              method: "DELETE",
                              headers: {
                                "x-csrf-token": (await api("/me")).csrf_token,
                                "if-match": String(w.revision),
                              },
                            });
                            if (!response.ok)
                              throw Error(
                                "Deletion failed; refresh the case revision.",
                              );
                            setSelected("");
                            setWorkspace(null);
                            await refresh("");
                            setNotice("Case permanently erased.");
                          }}
                        >
                          <p>
                            This operation checks case revision {w.revision}{" "}
                            before erasing.
                          </p>
                        </Form>
                      </Detail>
                    </>
                  ) : (
                    <Empty>
                      Only the owner can export, share, approve, monitor or
                      erase. Your access expires or can be revoked at any time.
                    </Empty>
                  )}
                </section>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>RepairClaim · Evidence before action.</span>
            <span>
              <LockKeyhole size={12} />
              Private by default
            </span>
          </footer>
        </div>
      </div>
    </div>
  );
}
type SectionProps = {
  w: Item;
  casePath: string;
  action: (work: () => Promise<unknown>, message?: string) => Promise<void>;
};

function Evidence({
  w,
  editable,
  casePath,
  action,
}: SectionProps & { editable: boolean }) {
  const [doc, setDoc] = useState(""),
    [page, setPage] = useState(1),
    [selected, setSelected] = useState<number[]>([]);
  const current = w.documents.find((d: Item) => d.id === doc);
  return (
    <>
      <div className="two-col">
        <section className="card">
          <h2>Bring the paperwork.</h2>
          <p>
            PDF, JPG or PNG · up to 20 MB · No passwords, active scripts or
            embedded files.
          </p>
          {editable ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const form = e.currentTarget;
                const data = new FormData(form);
                const file = data.get("file") as File;
                if (!file?.size) return;
                action(async () => {
                  const d = await upload(
                    `${casePath}/documents?filename=${encodeURIComponent(file.name)}&kind=${data.get("kind")}&revision=${w.revision}`,
                    file,
                  );
                  setDoc(d.id);
                  setSelected([]);
                }, "Document queued. Extracted values still need your confirmation.");
              }}
            >
              <label>
                Document type
                <select name="kind">
                  {[
                    "invoice",
                    "estimate",
                    "job_sheet",
                    "receipt",
                    "response",
                    "other",
                  ].map((k) => (
                    <option key={k}>{k}</option>
                  ))}
                </select>
              </label>
              <label>
                Choose a file
                <input
                  name="file"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  required
                />
              </label>
              <button>
                Upload securely <Plus size={16} />
              </button>
            </form>
          ) : (
            <Empty>Read-only access. Ask an editor to upload evidence.</Empty>
          )}
          <div className="document-list">
            {w.documents.map((d: Item) => (
              <button
                className={"document-row " + (doc === d.id ? "chosen" : "")}
                key={d.id}
                onClick={() => {
                  setDoc(d.id);
                  setPage(1);
                  setSelected([]);
                }}
              >
                <FileText />
                <span>
                  <strong>{d.filename}</strong>
                  <small>
                    {label(d.document_kind)} · {label(d.status)}
                  </small>
                </span>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>
        </section>
        <section className="card">
          <h2>Review, then confirm.</h2>
          {!current ? (
            <Empty>
              Select a document to inspect its pages and proposed facts.
            </Empty>
          ) : (
            <>
              <h3>{current.filename}</h3>
              <Badge>{label(current.status)}</Badge>
              {current.error && <p className="error">{label(current.error)}</p>}
              {current.status === "ready" ? (
                <>
                  <div className="preview-controls">
                    <label>
                      Page
                      <input
                        type="number"
                        min={1}
                        max={current.parsed.page_count}
                        value={page}
                        onChange={(e) => setPage(Number(e.target.value) || 1)}
                      />
                    </label>
                    <span>of {current.parsed.page_count}</span>
                  </div>
                  <img
                    className="document-preview"
                    src={image(`/documents/${doc}/preview?page=${page}`)}
                    alt={`${current.filename}, page ${page}`}
                  />
                  <p className="warning" role="status">
                    {documentReviewNotice(current.parsed)}
                  </p>
                  {current.parsed.proposals.map((p: Item, i: number) => (
                    <label className="check-row" key={i}>
                      <input
                        type="checkbox"
                        disabled={!editable}
                        checked={selected.includes(i)}
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? [...selected, i]
                              : selected.filter((n) => n !== i),
                          )
                        }
                      />
                      <span>
                        <strong>
                          {label(p.field)}: {p.value} {p.unit}
                        </strong>
                        <small>
                          Page {p.page} · “{p.quote}” · Unconfirmed extraction
                        </small>
                      </span>
                    </label>
                  ))}
                  {editable && (
                    <button
                      disabled={!selected.length}
                      onClick={() =>
                        action(
                          () =>
                            api(`/documents/${doc}/confirm`, {
                              selected,
                              expected_revision: w.revision,
                            }),
                          "Selected facts confirmed. Conflicting values remain visible.",
                        )
                      }
                    >
                      Confirm selected facts
                    </button>
                  )}
                  {current.document_kind === "response" && editable && (
                    <button
                      className="secondary"
                      onClick={() =>
                        action(
                          () =>
                            api(casePath + "/responses", {
                              document_id: doc,
                              key: crypto.randomUUID(),
                            }),
                          "Response reasons recorded for human review.",
                        )
                      }
                    >
                      Review response reasons
                    </button>
                  )}
                </>
              ) : (
                <p>
                  Background parsing runs in a restricted process. Check job
                  status in Coverage; no fact is accepted automatically.
                </p>
              )}
            </>
          )}
        </section>
      </div>
      <section className="card">
        <h2>The facts on record</h2>
        <p>
          Corrections create a new revision. Existing source anchors and earlier
          revisions are retained; old packet approvals are invalidated.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Fact</th>
                <th>Value</th>
                <th>Attribution</th>
                <th>Evidence</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {w.snapshot.facts.map((f: Item, i: number) => (
                <tr key={i}>
                  <td>{label(f.field)}</td>
                  <td>
                    {f.value} {f.unit}
                  </td>
                  <td>
                    <Badge>{label(f.status)}</Badge>
                  </td>
                  <td>
                    {f.anchor ? (
                      <button
                        className="text-button"
                        onClick={() => {
                          setDoc(f.anchor.document_id);
                          setPage(f.anchor.page);
                        }}
                      >
                        Page {f.anchor.page} ↗
                      </button>
                    ) : (
                      "User entered"
                    )}
                  </td>
                  <td>
                    {editable && (
                      <button
                        className="text-button"
                        onClick={() =>
                          action(
                            () =>
                              api(casePath + "/corrections", {
                                expected_revision: w.revision,
                                index: i,
                                replacement: null,
                              }),
                            "Fact removed in a new revision.",
                          )
                        }
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {editable && (
          <Detail title="Add or correct a fact">
            <Form
              submit="Save attributed fact"
              fields={[
                {
                  name: "field",
                  label: "Field",
                  options: [
                    "repair_mileage",
                    "repair_date",
                    "in_service_date",
                    "paid_amount",
                    "invoice_total",
                    "component",
                    "diagnostic_code",
                    "diagnosis",
                    "repair_description",
                    "vin",
                    "model",
                    "model_year",
                    "current_mileage",
                  ],
                },
                {
                  name: "value",
                  label: "Value",
                  hint: "Dates: YYYY-MM-DD. Correct a conflict by removing the wrong value first.",
                },
                {
                  name: "unit",
                  label: "Unit",
                  options: ["", "mi", "km", ...currencies],
                },
              ]}
              onSubmit={async (v) => {
                await api(casePath + "/corrections", {
                  expected_revision: w.revision,
                  replacement: factInput(v.field, v.value, v.unit),
                });
                await action(async () => {});
              }}
            />
          </Detail>
        )}
      </section>
    </>
  );
}

function Coverage({
  w,
  caps,
  editable,
  own,
  casePath,
  action,
}: SectionProps & { caps: Item; editable: boolean; own: boolean }) {
  const [preview, setPreview] = useState<Item | null>(null);
  const [source, setSource] = useState<Item | null>(null);
  return (
    <>
      <section className="card">
        <div className="section-heading">
          <h2>Documented conditions, not a promise.</h2>
          <Badge>
            {caps.registry.status === "complete"
              ? "Reviewed inventory available"
              : `Sources ${caps.registry.status}`}
          </Badge>
        </div>
        <p>
          Checks are limited to the supported, reviewed inventory below.
          Unknowns stay unknown; manufacturer confirmation is separate.
        </p>
        {caps.registry.sources.map((s: Item) => (
          <p key={s.id}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.id} ↗
            </a>{" "}
            · {label(s.state)} · last successful check{" "}
            {new Date(s.last_success * 1000).toLocaleString()}
          </p>
        ))}
        {editable && (
          <button
            onClick={() =>
              action(
                () =>
                  api(casePath + "/investigations", {
                    expected_revision: w.revision,
                    key: crypto.randomUUID(),
                  }),
                "Condition check queued.",
              )
            }
          >
            Check documented conditions <Search size={16} />
          </button>
        )}
        {own && caps.codex_enabled && (
          <Detail title="Optional Codex advisory review">
            <p>
              This is a separate, bounded egress approval—not permission to
              submit a claim. Billing and actual token usage may be unknown.
              Deterministic conditions remain authoritative.
            </p>
            <button
              className="secondary"
              onClick={() =>
                action(
                  async () =>
                    setPreview(await api(casePath + "/analysis-preview")),
                  "Review the exact data before authorising.",
                )
              }
            >
              Preview exact analysis context
            </button>
            {preview && (
              <>
                <pre>{JSON.stringify(preview.context, null, 2)}</pre>
                <p>
                  Estimate: {preview.estimated_input_tokens} input tokens ·{" "}
                  {preview.actual_billing}
                </p>
                <button
                  onClick={() =>
                    action(
                      () =>
                        api(casePath + "/investigations", {
                          expected_revision: w.revision,
                          key: crypto.randomUUID(),
                          mode: "codex",
                          allowance: 2,
                          egress_fingerprint: preview.fingerprint,
                        }),
                      "Approved advisory review queued; maximum two calls including retries.",
                    )
                  }
                >
                  Approve this context · at most 2 calls
                </button>
              </>
            )}
          </Detail>
        )}
      </section>
      {w.jobs
        .slice()
        .reverse()
        .map((j: Item) => (
          <section className="card" key={j.id}>
            <div className="section-heading">
              <h3>
                {label(j.operation)} <small>{j.id.slice(0, 8)}</small>
              </h3>
              <Badge tone={j.stale ? "amber" : ""}>
                {j.stale ? "Stale inputs" : label(j.status)}
              </Badge>
            </div>
            {j.error && <p className="warning">{label(j.error)}</p>}
            {j.result?.search && (
              <>
                <h2>
                  {j.result.search.state
                    ? label(j.result.search.state)
                    : "No reliable assessment available"}
                </h2>
                <p>
                  Search completeness: {j.result.search.search_status}. This is
                  not an exhaustive entitlement determination.
                </p>
                {j.result.search.candidates.map((c: Item) => (
                  <Detail
                    key={c.family_id}
                    title={`${c.family_id} / ${c.programme_revision} · ${label(c.state)}`}
                  >
                    <table>
                      <thead>
                        <tr>
                          <th>Condition</th>
                          <th>Finding</th>
                          <th>Official evidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {c.conditions.map((condition: Item) => (
                          <tr key={condition.condition_id}>
                            <td>{condition.condition_id}</td>
                            <td>{label(condition.status)}</td>
                            <td>
                              <p>{condition.anchor.quote}</p>
                              <small>
                                {condition.anchor.document_id} · page{" "}
                                {condition.anchor.page} · SHA-256{" "}
                                {condition.anchor.sha256}
                              </small>
                              <button
                                className="text-button"
                                onClick={() => setSource(condition.anchor)}
                              >
                                Inspect frozen source page ↗
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </Detail>
                ))}
                {source && (
                  <Detail
                    title={`Frozen source page ${source.page} — ${source.document_id}`}
                  >
                    <p>
                      The captured version below supports the cited quote. Older
                      versions remain historical, not automatically current.
                    </p>
                    <img
                      className="document-preview"
                      src={image(
                        `/sources/${source.document_id}/revisions/${source.sha256}/preview?page=${source.page}`,
                      )}
                      alt={`Official capture ${source.document_id}, page ${source.page}`}
                    />
                    <button
                      className="text-button"
                      onClick={() => setSource(null)}
                    >
                      Close source
                    </button>
                  </Detail>
                )}
                {j.result.next_question && (
                  <div className="question">
                    <h3>
                      {j.result.next_question.prompt ||
                        `Please provide ${label(j.result.next_question.field)}`}
                    </h3>
                    <p>
                      Record the answer as an attributed fact or confirm it from
                      a document. Choosing “answered” alone does not create
                      evidence.
                    </p>
                    {editable &&
                      ["unknown", "later", "answered"].map((answer) => (
                        <button
                          className="secondary"
                          key={answer}
                          onClick={() =>
                            action(
                              () => api(`/jobs/${j.id}/answer`, { answer }),
                              `Response recorded: ${answer}`,
                            )
                          }
                        >
                          {label(answer)}
                        </button>
                      ))}
                  </div>
                )}
              </>
            )}
            {j.result?.agent_advice && (
              <Detail title="Validated advisory result">
                <pre>{JSON.stringify(j.result.agent_advice, null, 2)}</pre>
              </Detail>
            )}
            {j.attempts.length > 0 && (
              <Detail title="Attempt and validation history">
                <pre>{JSON.stringify(j.attempts, null, 2)}</pre>
                <p>Null usage/cost means unknown, not free.</p>
                {own && (
                  <Form
                    submit="Acknowledge unknown usage"
                    fields={[
                      {
                        name: "reason",
                        label: "Why you accept the unresolved billing risk",
                      },
                    ]}
                    onSubmit={async (v) => {
                      await api(`/jobs/${j.id}/usage-acknowledgement`, v);
                      await action(async () => {});
                    }}
                  />
                )}
              </Detail>
            )}
            {editable && (
              <div className="button-row">
                {["queued", "running"].includes(j.status) && (
                  <button
                    className="secondary"
                    onClick={() =>
                      action(
                        () => api(`/jobs/${j.id}/cancel`, {}),
                        "Work cancelled; stale results cannot commit.",
                      )
                    }
                  >
                    Cancel work
                  </button>
                )}
                {["partial", "awaiting_authority"].includes(j.status) &&
                  !j.stale && (
                    <button
                      className="secondary"
                      onClick={() =>
                        action(
                          () => api(`/jobs/${j.id}/resume`, {}),
                          "Resume queued with the original allowance and deadline.",
                        )
                      }
                    >
                      Resume original job
                    </button>
                  )}
              </div>
            )}
          </section>
        ))}
      {!w.jobs.length && (
        <Empty>
          No assessment yet. Start with a condition check after reviewing the
          facts.
        </Empty>
      )}
    </>
  );
}

function Packets({
  w,
  own,
  caps,
  casePath,
  action,
}: SectionProps & { own: boolean; caps: Item }) {
  const [attachments, setAttachments] = useState<Record<string, Item>>({}),
    [page, setPage] = useState<Record<string, number>>({});
  const eligible = w.jobs.filter(
    (j: Item) =>
      j.operation === "investigate" &&
      !j.stale &&
      ["review_ready", "awaiting_evidence", "manual_review"].includes(j.status),
  );
  return (
    <>
      <section className="card">
        <h2>A careful enquiry. Your final say.</h2>
        <p>
          Creating an edited packet creates a new draft with a new approval.
          Review every page and attachment before approving the exact
          fingerprint. RepairClaim never sends it for you.
        </p>
        {own && eligible.length ? (
          <Form
            submit="Create new packet draft"
            fields={[
              {
                name: "job_id",
                label: "Assessment",
                options: eligible.map((j: Item) => j.id),
              },
              { name: "recipient", label: "Recipient / department" },
              {
                name: "purpose",
                label: "Purpose",
                options: [
                  "enquiry",
                  "records_request",
                  "reimbursement",
                  "followup",
                ],
              },
              {
                name: "notes",
                label: "Your additional statement",
                type: "textarea",
                required: false,
                hint: "Clearly attributed to you. Avoid unsupported accusations or guarantees.",
              },
            ]}
            onSubmit={async (v) => {
              await api(casePath + "/packets", {
                ...v,
                key: crypto.randomUUID(),
                attachments: Object.values(attachments),
              });
              await action(async () => {}, "New unapproved draft created.");
            }}
          >
            <div className="attachment-picker">
              <h3>Explicit attachment selection</h3>
              {w.documents
                .filter((d: Item) => d.status === "ready")
                .map((d: Item) => (
                  <div className="record" key={d.id}>
                    <label className="check-row">
                      <input
                        type="checkbox"
                        checked={!!attachments[d.id]}
                        onChange={(e) =>
                          setAttachments((prev) => {
                            const next = { ...prev };
                            if (e.target.checked)
                              next[d.id] = {
                                document_id: d.id,
                                mode: "sanitized",
                                redactions: [],
                              };
                            else delete next[d.id];
                            return next;
                          })
                        }
                      />
                      <span>{d.filename}</span>
                    </label>
                    {attachments[d.id] && (
                      <>
                        <label>
                          Attachment policy
                          <select
                            value={attachments[d.id].mode}
                            onChange={(e) =>
                              setAttachments({
                                ...attachments,
                                [d.id]: {
                                  ...attachments[d.id],
                                  mode: e.target.value,
                                  redactions: [],
                                },
                              })
                            }
                          >
                            <option value="sanitized">
                              Sanitized image-only PDF
                            </option>
                            <option value="original">
                              Include original too (metadata may remain)
                            </option>
                          </select>
                        </label>
                        {attachments[d.id].mode === "sanitized" && (
                          <label>
                            Exact strings to black out, one per line
                            <textarea
                              onChange={(e) =>
                                setAttachments({
                                  ...attachments,
                                  [d.id]: {
                                    ...attachments[d.id],
                                    redactions: e.target.value
                                      .split("\n")
                                      .filter(Boolean),
                                  },
                                })
                              }
                            />
                          </label>
                        )}
                      </>
                    )}
                  </div>
                ))}
            </div>
          </Form>
        ) : (
          <Empty>
            {own
              ? "Complete a current condition check before drafting."
              : "Only the case owner can draft, approve or download packets."}
          </Empty>
        )}
      </section>
      {w.packets
        .slice()
        .reverse()
        .map((p: Item) => {
          const access = packetAccess(
            p,
            w.revision,
            caps.registry.epoch,
            caps.registry.status,
          );
          return (
            <section className="card" key={p.id}>
              <div className="section-heading">
                <h2>{p.recipient}</h2>
                <Badge tone={p.stale ? "amber" : ""}>
                  {p.stale ? "Stale" : label(p.status)}
                </Badge>
              </div>
              <p>
                {label(p.purpose)} · Case revision {p.case_revision}
              </p>
              <p
                className={
                  p.status === "approved" && !p.stale ? "notice" : "warning"
                }
              >
                {p.status === "approved" && !p.stale
                  ? "Owner approval recorded. Download still rechecks expiry and current sources."
                  : "UNAPPROVED REVIEW COPY — do not submit this preview. Exact owner approval is required."}
              </p>
              <Detail title="Read the exact draft">
                {p.paragraphs.map((text: string, i: number) => (
                  <p key={i}>{text}</p>
                ))}
              </Detail>
              {p.manifest && (
                <Detail title="Inspect attachment manifest and hashes">
                  <pre>{JSON.stringify(p.manifest, null, 2)}</pre>
                </Detail>
              )}
              {p.fingerprint && (
                <>
                  <p className="fingerprint">
                    Exact approval fingerprint: {p.fingerprint}
                  </p>
                  <div className="preview-controls">
                    <label>
                      Preview page
                      <input
                        type="number"
                        min={1}
                        value={page[p.id] || 1}
                        onChange={(e) =>
                          setPage({
                            ...page,
                            [p.id]: Number(e.target.value) || 1,
                          })
                        }
                      />
                    </label>
                  </div>
                  <img
                    className="packet-preview"
                    src={image(
                      `/packets/${p.id}/preview?page=${page[p.id] || 1}`,
                    )}
                    alt={`Packet for ${p.recipient}, page ${page[p.id] || 1}`}
                  />
                </>
              )}
              {own && (
                <div className="button-row">
                  {p.status === "draft" && !p.stale && (
                    <button
                      onClick={() =>
                        action(
                          () => api(`/packets/${p.id}/render`, {}),
                          "Rendering queued. Review the resulting pages before approval.",
                        )
                      }
                    >
                      Render review copy
                    </button>
                  )}
                  {access.approve && (
                    <button
                      onClick={() => {
                        if (
                          window.confirm(
                            "I reviewed the pages, recipient, redactions and attachment manifest. Approve these exact bytes for 24 hours?",
                          )
                        )
                          action(
                            () =>
                              api(`/packets/${p.id}/approve`, {
                                fingerprint: p.fingerprint,
                              }),
                            "Exact packet approved for 24 hours. Nothing was sent.",
                          );
                      }}
                    >
                      Approve these exact bytes
                    </button>
                  )}
                  {access.download && (
                    <button
                      onClick={() =>
                        action(
                          () =>
                            download(
                              `/packets/${p.id}/download`,
                              "repairclaim-approved-packet.zip",
                            ),
                          "Approved packet downloaded. Submit it manually if you choose.",
                        )
                      }
                    >
                      Download approved packet
                    </button>
                  )}
                  {p.approval && (
                    <button
                      className="secondary"
                      onClick={() =>
                        action(
                          () => api(`/packets/${p.id}/revoke`, {}),
                          "Approval revoked.",
                        )
                      }
                    >
                      Revoke approval
                    </button>
                  )}
                </div>
              )}
            </section>
          );
        })}
    </>
  );
}

function Timeline({
  w,
  own,
  casePath,
  action,
}: SectionProps & { own: boolean }) {
  return (
    <>
      <section className="card">
        <h2>Outcomes without inflated savings.</h2>
        <p>
          Requested, covered, approved, received and avoided are separate
          categories. They are never added into a single “savings” number.
          Reversals preserve the history.
        </p>
        {Object.keys(w.totals).length ? (
          <div className="metric-grid">
            {Object.entries(w.totals).flatMap(([currency, kinds]) =>
              Object.entries(kinds as Item).map(([kind, amounts]) => (
                <div className="metric" key={currency + kind}>
                  <small>
                    {label(kind)} · {currency}
                  </small>
                  {Object.entries(amounts as Item).map(
                    ([attribution, amount]) => (
                      <div key={attribution}>
                        <strong>{String(amount)}</strong>
                        <small>{label(attribution)}</small>
                      </div>
                    ),
                  )}
                </div>
              )),
            )}
          </div>
        ) : (
          <Empty>
            No outcome amounts recorded. A potential programme match is not
            money received.
          </Empty>
        )}
        {own && (
          <Detail title="Record a financial event">
            <Form
              submit="Record attributed amount"
              fields={[
                {
                  name: "kind",
                  label: "Category",
                  options: outcomeKinds,
                },
                { name: "amount", label: "Amount", type: "number" },
                {
                  name: "currency",
                  label: "Currency",
                  options: currencies,
                },
                {
                  name: "repair_line_id",
                  label: "Repair line identifier",
                  hint: "Use the same identifier for the same repair expense.",
                },
                {
                  name: "evidence_class",
                  label: "Attribution",
                  options: ["user_reported", "documented"],
                },
                {
                  name: "evidence_ref",
                  label: "Evidence reference",
                  hint: "Document ID for documented events; your own reference for reported events.",
                },
                {
                  name: "evidence_page",
                  label: "Document page",
                  type: "number",
                  required: false,
                },
                {
                  name: "evidence_quote",
                  label: "Exact evidence quote with amount",
                  type: "textarea",
                  required: false,
                },
                {
                  name: "reverses",
                  label: "Reverses event ID (optional)",
                  required: false,
                },
              ]}
              onSubmit={async (v) => {
                await api(casePath + "/outcomes", {
                  key: crypto.randomUUID(),
                  event: {
                    id: crypto.randomUUID(),
                    kind: v.kind,
                    amount: { amount: v.amount, currency: v.currency },
                    evidence_class: v.evidence_class,
                    evidence_ref: v.evidence_ref,
                    repair_line_id: v.repair_line_id,
                    reverses: v.reverses || null,
                  },
                  evidence_page: v.evidence_page
                    ? Number(v.evidence_page)
                    : null,
                  evidence_quote: v.evidence_quote || null,
                });
                await action(async () => {});
              }}
            />
          </Detail>
        )}
      </section>
      <div className="two-col">
        <section className="card">
          <h2>Responses & next steps</h2>
          <p>
            Upload a response under Documents, then select “Review response
            reasons”. No message is interpreted as independently verified
            coverage.
          </p>
          {w.responses.map((r: Item) => (
            <article className="record" key={r.id}>
              {r.comparison && (
                <Detail title="Compare against frozen case and conditions">
                  <p>{r.comparison.interpretation}</p>
                  <pre>{JSON.stringify(r.comparison, null, 2)}</pre>
                </Detail>
              )}
              {r.reasons.map((reason: Item, i: number) => (
                <div key={i}>
                  <Badge>{label(reason.category)}</Badge>
                  <blockquote>{reason.quote}</blockquote>
                  <small>
                    Page {reason.page} · {label(reason.attribution)}
                  </small>
                  <p>{reason.next_action}</p>
                </div>
              ))}
            </article>
          ))}
          {!w.responses.length && <Empty>No response recorded yet.</Empty>}
          <h3>Manual submission log</h3>
          {w.manual_submissions.map((s: Item) => (
            <p key={s.id}>
              User reported sent · {label(s.channel)} ·{" "}
              {new Date(s.sent_at * 1000).toLocaleString()} · delivery not
              verified
            </p>
          ))}
          {own && w.packets.some((p: Item) => p.fingerprint) && (
            <Detail title="I submitted it myself">
              <Form
                submit="Log my manual submission"
                fields={[
                  {
                    name: "packet_id",
                    label: "Packet",
                    options: w.packets
                      .filter((p: Item) => p.fingerprint)
                      .map((p: Item) => p.id),
                  },
                  {
                    name: "channel",
                    label: "Channel",
                    options: [
                      "portal",
                      "email",
                      "postal_mail",
                      "in_person",
                      "other",
                    ],
                  },
                  {
                    name: "sent_at",
                    label: "When you sent it (your local time)",
                    type: "datetime-local",
                  },
                ]}
                onSubmit={async (v) => {
                  await api(casePath + "/submissions", {
                    ...v,
                    sent_at: aware(v.sent_at),
                    key: crypto.randomUUID(),
                  });
                  await action(
                    async () => {},
                    "Recorded as user-reported sent, not verified delivery.",
                  );
                }}
              />
            </Detail>
          )}
        </section>
        <section className="card">
          <h2>Keep the follow-up in view.</h2>
          {w.reminders.map((r: Item) => (
            <article className="record" key={r.id}>
              <Badge>{label(r.status)}</Badge>
              <h3>{r.label}</h3>
              <p>
                {new Date(r.due_at * 1000).toLocaleString()} · {r.timezone}
              </p>
              <small>
                {label(r.provenance)} — not an inferred legal deadline
              </small>
              {r.source_anchor && (
                <Detail title="Documented deadline provenance">
                  <pre>{JSON.stringify(r.source_anchor, null, 2)}</pre>
                </Detail>
              )}
              {own && ["scheduled", "due"].includes(r.status) && (
                <button
                  className="text-button"
                  onClick={() =>
                    action(
                      () => api(`/reminders/${r.id}`, undefined, "DELETE"),
                      "Reminder cancelled.",
                    )
                  }
                >
                  Cancel
                </button>
              )}
            </article>
          ))}
          {own && (
            <Form
              submit="Save reminder"
              fields={[
                { name: "label", label: "Reminder" },
                {
                  name: "due_at",
                  label: "Date and time (your local time)",
                  type: "datetime-local",
                },
                {
                  name: "timezone",
                  label: "Timezone",
                  value: Intl.DateTimeFormat().resolvedOptions().timeZone,
                },
                {
                  name: "provenance",
                  label: "Provenance",
                  options: ["user_entered", "suggested_followup"],
                },
              ]}
              onSubmit={async (v) => {
                await api(casePath + "/reminders", {
                  ...v,
                  due_at: aware(v.due_at),
                });
                await action(async () => {});
              }}
            />
          )}
          {own && (
            <Detail title="Record an explicitly documented programme deadline">
              <p>
                Only a current reviewed source with a literal “Submit by”, “File
                by”, or “Submission deadline” and matching ISO date is accepted.
                Ambiguous wording stays a user-entered reminder.
              </p>
              <Form
                submit="Verify and record source-stated date"
                fields={[
                  { name: "label", label: "Reminder" },
                  {
                    name: "due_at",
                    label: "Date and time (local)",
                    type: "datetime-local",
                  },
                  {
                    name: "timezone",
                    label: "Timezone",
                    value: Intl.DateTimeFormat().resolvedOptions().timeZone,
                  },
                  { name: "document_id", label: "Official source ID" },
                  { name: "sha256", label: "Captured SHA-256" },
                  { name: "page", label: "Source page", type: "number" },
                  {
                    name: "quote",
                    label: "Exact deadline quote",
                    type: "textarea",
                  },
                ]}
                onSubmit={async (v) => {
                  await api(casePath + "/reminders", {
                    label: v.label,
                    due_at: aware(v.due_at),
                    timezone: v.timezone,
                    provenance: "programme_documented",
                    source_anchor: {
                      document_id: v.document_id,
                      sha256: v.sha256,
                      page: Number(v.page),
                      quote: v.quote,
                    },
                  });
                  await action(async () => {});
                }}
              />
            </Detail>
          )}
        </section>
      </div>
      <section className="card">
        <h2>
          <Clock3 size={20} /> The case record
        </h2>
        <div className="timeline">
          {w.timeline
            .slice()
            .reverse()
            .map((event: Item, i: number) => (
              <article key={i}>
                <span className="timeline-dot" />
                <div>
                  <strong>{label(event.action)}</strong>
                  <p>
                    Revision {event.revision} ·{" "}
                    {new Date(event.created * 1000).toLocaleString()}
                  </p>
                  <small>
                    {event.actor_kind === "system_on_behalf_of_owner"
                      ? "Scheduled system action for owner"
                      : `Actor ${event.actor_id}`}
                  </small>
                </div>
              </article>
            ))}
        </div>
      </section>
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
