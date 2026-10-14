import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ArrowUp,
  BookOpen,
  MessageSquare,
  Plus,
  X,
  Loader2,
  ExternalLink,
} from "lucide-react";
import "./chat.css";
import {
  confidenceLabel,
  evidenceTrace,
  ragConcepts,
} from "./chatPresentation";

type Passage = {
  id: string;
  title: string;
  url: string;
  version: string;
  text: string;
  anchor?: string;
  origin: string;
};
type Run = {
  id: string;
  status: string;
  error?: string;
  events: { stage: string; outcome: string }[];
  answer: null | {
    draft: {
      claims: {
        id: string;
        text: string;
        citations: { passage_id: string; quote: string }[];
      }[];
      reply_order: string[];
      questions: string[];
      limitations: string[];
      evidence_state: string;
    };
    evidence: Passage[];
  };
};
type Chat = {
  id: string;
  title: string;
  turns: { id: string; content: string; run: Run }[];
};
type Summary = { id: string; title: string; turn_count: number };
class RequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}
async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
  key?: string,
): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new RequestError(
      typeof error.detail === "string"
        ? error.detail
        : `Request failed (${response.status})`,
      response.status,
    );
  }
  return response.json();
}
export default function ChatApp() {
  const [list, setList] = useState<Summary[]>([]);
  const [chat, setChat] = useState<Chat | null>(null);
  const [selected, setSelected] = useState<string | null>(
    window.location.hash.split("/")[1] || null,
  );
  const [input, setInput] = useState("");
  const [version, setVersion] = useState("");
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [citation, setCitation] = useState<{
    passage: Passage;
    quote: string;
  } | null>(null);
  const pending = useRef<{
    chatId: string;
    content: string;
    count: number;
    key: string;
  } | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const active = chat?.turns.at(-1)?.run;
  const running = active?.status === "queued" || active?.status === "running";
  useEffect(() => {
    const changed = () => {
      setSelected(window.location.hash.split("/")[1] || null);
      setCitation(null);
    };
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const [items, current] = await Promise.all([
          request<Summary[]>("/v1/chats"),
          selected
            ? request<Chat>(`/v1/chats/${selected}`)
            : Promise.resolve(null),
        ]);
        if (!cancelled) {
          setList(items);
          setChat(current);
          setConnectionError("");
        }
      } catch (e) {
        if (!cancelled) setConnectionError((e as Error).message);
      }
    };
    setChat(null);
    void refresh();
    const timer = window.setInterval(refresh, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selected]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat?.turns.length, active?.status]);
  async function send(event: FormEvent) {
    event.preventDefault();
    if (busy || running || (!input.trim() && !pending.current)) return;
    setBusy(true);
    setError("");
    try {
      if (!pending.current) {
        const target =
          chat ||
          (await request<Chat>("/v1/chats", "POST", {
            server_version: version || null,
          }));
        pending.current = {
          chatId: target.id,
          content: input.trim(),
          count: target.turns.length,
          key: crypto.randomUUID(),
        };
      }
      const operation = pending.current;
      const result = await request<Chat>(
        `/v1/chats/${operation.chatId}/messages`,
        "POST",
        { content: operation.content, expected_turn_count: operation.count },
        operation.key,
      );
      pending.current = null;
      setInput("");
      setChat(result);
      setSelected(result.id);
      window.location.hash = `chat/${result.id}`;
      setList(await request<Summary[]>("/v1/chats"));
    } catch (e) {
      if (e instanceof RequestError && (e.status === 409 || e.status === 422)) {
        const target = pending.current?.chatId;
        pending.current = null;
        setError(
          `${e.message}. Review the current conversation, then send again.`,
        );
        if (target) {
          setSelected(target);
          window.location.hash = `chat/${target}`;
          setChat(await request<Chat>(`/v1/chats/${target}`).catch(() => null));
        }
        return;
      }
      setError(
        `${(e as Error).message}. Retry send to safely resume the same message.`,
      );
    } finally {
      setBusy(false);
    }
  }
  function newChat() {
    if (busy || pending.current) return;
    window.location.hash = "chat";
    setSelected(null);
    setChat(null);
    setInput("");
    setCitation(null);
  }
  async function retry(run: Run) {
    try {
      setBusy(true);
      await request(`/v1/runs/${run.id}/retry`, "POST");
      if (chat) setChat(await request<Chat>(`/v1/chats/${chat.id}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="rag-shell">
      <aside className="rag-sidebar">
        <a className="rag-brand" href="#chat">
          <BookOpen size={25} /> ResolveDesk<span>POSTGRES KNOWLEDGE</span>
        </a>
        <button
          aria-label="New conversation"
          className="rag-new"
          onClick={newChat}
          disabled={busy || !!pending.current}
        >
          <Plus size={17} /> New conversation
        </button>
        <div className="rag-nav-label">YOUR CONVERSATIONS</div>
        <nav aria-label="Conversations">
          {list.map((item) => (
            <a
              className={selected === item.id ? "selected" : ""}
              href={`#chat/${item.id}`}
              key={item.id}
            >
              <MessageSquare size={16} />
              <span>{item.title}</span>
            </a>
          ))}
        </nav>
        <footer>
          <a href="#knowledge">Knowledge library ↗</a>
          <a href="#workspace">Review workspace ↗</a>
          <small>
            Local Codex · Grounded in PostgreSQL 16 / 17 documentation
          </small>
        </footer>
      </aside>
      <main className="rag-main">
        <header>
          <div>
            <span className="rag-eyebrow">DAY 02 / CITATION-GROUNDED RAG</span>
            <h1>{chat?.title || "Ask. Verify. Keep going."}</h1>
          </div>
          <span className="rag-live">● Local model</span>
        </header>
        <div className="rag-transcript" aria-live="polite">
          {!chat?.turns.length && (
            <section className="rag-welcome">
              <span className="rag-icon">
                <MessageSquare size={30} />
              </span>
              <h2>
                Your PostgreSQL questions,
                <br />
                with the evidence attached.
              </h2>
              <p>
                Ask a question, inspect its sources, then ask a follow-up. Each
                answer retrieves fresh context from the knowledge library, with
                official-source search when evidence is thin.
              </p>
              <div className="rag-suggestions">
                {[
                  "Can pg_dump 16 back up a PostgreSQL 17 server?",
                  "How do I restore a custom-format backup?",
                  "What does pg_upgrade check before an upgrade?",
                ].map((text) => (
                  <button key={text} onClick={() => setInput(text)}>
                    {text} ↗
                  </button>
                ))}
              </div>
              <details className="rag-concepts">
                <summary>How this RAG chat works · 4 concepts</summary>
                <ol>
                  {ragConcepts.map((concept) => (
                    <li key={concept.title}>
                      <strong>{concept.title}</strong>
                      <p>{concept.detail}</p>
                    </li>
                  ))}
                </ol>
              </details>
            </section>
          )}
          {chat?.turns.map((turn, index) => (
            <section className="rag-turn" key={turn.id}>
              <div className="rag-user">
                <span>YOU</span>
                <p>{turn.content}</p>
              </div>
              <div className="rag-assistant">
                <span className="rag-eyebrow">RESOLVEDESK</span>
                {turn.run.answer && (
                  <>
                    <span
                      className={`rag-state ${turn.run.answer.draft.evidence_state}`}
                    >
                      {confidenceLabel(
                        turn.run.answer.draft.evidence_state,
                        turn.run.status,
                      )}
                    </span>
                    <div
                      className="rag-trace"
                      aria-label="Retrieval and search provenance"
                    >
                      {evidenceTrace(turn.run).map((text) => (
                        <span key={text}>{text}</span>
                      ))}
                    </div>
                    {turn.run.answer.draft.reply_order.map((id) => {
                      const claim = turn.run.answer!.draft.claims.find(
                        (c) => c.id === id,
                      );
                      return (
                        claim && (
                          <div className="rag-claim" key={id}>
                            <p>{claim.text}</p>
                            <div className="rag-citations">
                              {claim.citations.map((ref, n) => {
                                const passage = turn.run.answer!.evidence.find(
                                  (p) => p.id === ref.passage_id,
                                );
                                return (
                                  passage && (
                                    <button
                                      key={`${ref.passage_id}-${n}`}
                                      onClick={() =>
                                        setCitation({
                                          passage,
                                          quote: ref.quote,
                                        })
                                      }
                                    >
                                      <BookOpen size={12} />
                                      {passage.title} · {passage.version}
                                    </button>
                                  )
                                );
                              })}
                            </div>
                          </div>
                        )
                      );
                    })}
                    {turn.run.answer.draft.questions.map((q, n) => (
                      <p className="rag-question" key={n}>
                        {q}
                      </p>
                    ))}
                    {turn.run.answer.draft.limitations.map((limit, n) => (
                      <p className="rag-warning" key={n}>
                        {limit}
                      </p>
                    ))}
                  </>
                )}
                {(turn.run.status === "queued" ||
                  turn.run.status === "running") && (
                  <p className="rag-working">
                    <Loader2 className="rag-spin" size={17} />
                    {turn.run.events.at(-1)?.stage.replaceAll("_", " ") ||
                      "Queued"}{" "}
                    — retrieving and checking evidence…
                  </p>
                )}
                {turn.run.error && (
                  <div className="rag-warning" role="alert">
                    {turn.run.error}
                    {index === chat.turns.length - 1 && (
                      <button onClick={() => retry(turn.run)} disabled={busy}>
                        Retry this answer
                      </button>
                    )}
                  </div>
                )}
              </div>
            </section>
          ))}
          <div ref={bottom} />
        </div>
        <div className="rag-compose-area">
          {connectionError && (
            <p className="rag-warning" role="alert">
              Connection: {connectionError}
            </p>
          )}
          {error && (
            <p className="rag-warning" role="alert">
              {error}
            </p>
          )}
          <form onSubmit={send}>
            <label className="rag-sr" htmlFor="chat-message">
              Your PostgreSQL question
            </label>
            <textarea
              id="chat-message"
              rows={2}
              maxLength={8000}
              value={input}
              disabled={busy || !!pending.current}
              onChange={(e) => setInput(e.target.value)}
              placeholder={chat ? "Ask a follow-up…" : "Ask about PostgreSQL…"}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className="rag-compose-controls">
              {!chat && (
                <label>
                  Server context{" "}
                  <select
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                  >
                    <option value="">Not specified</option>
                    <option value="16">PostgreSQL 16</option>
                    <option value="17">PostgreSQL 17</option>
                  </select>
                </label>
              )}
              <button
                aria-label="Send message"
                type="submit"
                disabled={
                  busy || running || (!input.trim() && !pending.current)
                }
              >
                {busy ? <Loader2 size={18} /> : <ArrowUp size={19} />}
              </button>
            </div>
          </form>
          <small>
            Sources are verified against retrieved passages. Support assessment
            is advisory, not a guarantee. Shift + Enter for a new line.
          </small>
        </div>
      </main>
      {citation && (
        <aside className="rag-evidence" aria-label="Citation evidence">
          <button
            className="rag-close"
            aria-label="Close evidence"
            onClick={() => setCitation(null)}
          >
            <X />
          </button>
          <span className="rag-eyebrow">SOURCE EVIDENCE</span>
          <h2>{citation.passage.title}</h2>
          <span className="rag-state">
            PostgreSQL {citation.passage.version} · {citation.passage.origin}
          </span>
          <h3>Cited quote</h3>
          <blockquote>{citation.quote}</blockquote>
          <h3>Retrieved passage</h3>
          <pre>{citation.passage.text}</pre>
          <a
            href={
              citation.passage.url +
              (citation.passage.anchor ? `#${citation.passage.anchor}` : "")
            }
            target="_blank"
            rel="noreferrer"
          >
            Open original source <ExternalLink size={14} />
          </a>
        </aside>
      )}
    </div>
  );
}
