"""SQLite persistence and private document storage for a single-host deployment."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pymupdf
from contracts.tenderlens import DraftBrief, PageLookupRequest, PageLookupResult


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.files = self.root / "documents"
        self.files.mkdir(exist_ok=True)
        self.db_path = self.root / "tenderlens.sqlite3"
        self._initialize()

    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def _initialize(self):
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
                    filename TEXT NOT NULL, sha256 TEXT NOT NULL, page_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pages (
                    document_id TEXT NOT NULL REFERENCES documents(id), page INTEGER NOT NULL,
                    text TEXT NOT NULL, quality TEXT NOT NULL,
                    PRIMARY KEY(document_id, page)
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
                    status TEXT NOT NULL, document_hashes TEXT NOT NULL, brief_json TEXT,
                    error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), position INTEGER NOT NULL,
                    claim_json TEXT NOT NULL, review_status TEXT, review_value TEXT,
                    review_reason TEXT, reviewed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    event_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS exports (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_chunks (
                    run_id TEXT NOT NULL REFERENCES runs(id), chunk_key TEXT NOT NULL,
                    pages_json TEXT NOT NULL, status TEXT NOT NULL, brief_json TEXT,
                    PRIMARY KEY(run_id, chunk_key)
                );
                """
            )

    def create_opportunity(self, title: str):
        item = {"id": str(uuid.uuid4()), "title": title, "created_at": now()}
        with self.connect() as db:
            db.execute(
                "INSERT INTO opportunities(id,title,created_at) VALUES(:id,:title,:created_at)",
                item,
            )
        return item

    def list_opportunities(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM opportunities ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    def opportunity(self, opportunity_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
            return dict(row) if row else None

    def documents_for(self, opportunity_id: str):
        with self.connect() as db:
            rows = db.execute(
                """SELECT d.*, SUM(CASE WHEN p.quality='needs_ocr' THEN 1 ELSE 0 END)
                AS needs_ocr_pages, SUM(CASE WHEN p.quality='ocr' THEN 1 ELSE 0 END) AS ocr_pages
                FROM documents d JOIN pages p ON p.document_id=d.id
                WHERE d.opportunity_id=? GROUP BY d.id ORDER BY d.created_at, d.id""",
                (opportunity_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_document(self, opportunity_id: str, filename: str, data: bytes):
        if len(data) > 30_000_000 or not data.startswith(b"%PDF-"):
            raise ValueError("Upload must be a PDF no larger than 30 MB")
        try:
            document = pymupdf.open(stream=data, filetype="pdf")
            if document.page_count < 1 or document.page_count > 250:
                raise ValueError("PDF must contain 1 to 250 pages")
            pages = []
            for index in range(document.page_count):
                page = document[index]
                text = page.get_text("text")
                quality = "text" if len(text.strip()) >= 80 else "needs_ocr"
                if quality == "needs_ocr" and page.get_images():
                    try:
                        ocr = page.get_text(textpage=page.get_textpage_ocr(language="eng", dpi=200))
                        if len(ocr.strip()) >= 80:
                            text, quality = ocr, "ocr"
                    except RuntimeError:
                        pass
                pages.append((index + 1, text, quality))
            document.close()
        except (pymupdf.FileDataError, pymupdf.EmptyFileError) as error:
            raise ValueError("Unreadable PDF") from error
        doc_id = str(uuid.uuid4())
        path = self.files / f"{doc_id}.pdf"
        path.write_bytes(data)
        item = {
            "id": doc_id,
            "opportunity_id": opportunity_id,
            "filename": Path(filename).name[:255],
            "sha256": hashlib.sha256(data).hexdigest(),
            "page_count": len(pages),
            "created_at": now(),
        }
        with self.connect() as db:
            db.execute(
                """INSERT INTO documents(id,opportunity_id,filename,sha256,page_count,created_at)
                VALUES(:id,:opportunity_id,:filename,:sha256,:page_count,:created_at)""",
                item,
            )
            db.executemany(
                "INSERT INTO pages(document_id,page,text,quality) VALUES(?,?,?,?)",
                [(doc_id, page, text, quality) for page, text, quality in pages],
            )
        return item

    def document(self, document_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            return dict(row) if row else None

    def page(self, document_id: str, page: int):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM pages WHERE document_id=? AND page=?", (document_id, page)
            ).fetchone()
            return dict(row) if row else None

    def lookup(self, request: PageLookupRequest) -> PageLookupResult:
        row = self.page(request.document_id, request.page)
        if not row:
            raise ValueError("Page does not exist")
        return PageLookupResult(
            document_id=request.document_id, page=request.page, text=row["text"]
        )

    def create_run(self, opportunity_id: str):
        documents = self.documents_for(opportunity_id)
        if not documents:
            raise ValueError("Upload at least one PDF before starting extraction")
        item = {
            "id": str(uuid.uuid4()),
            "opportunity_id": opportunity_id,
            "status": "queued",
            "document_hashes": json.dumps({d["id"]: d["sha256"] for d in documents}),
            "created_at": now(),
            "updated_at": now(),
        }
        with self.connect() as db:
            db.execute(
                """INSERT INTO runs(id,opportunity_id,status,document_hashes,created_at,updated_at)
                VALUES(:id,:opportunity_id,:status,:document_hashes,:created_at,:updated_at)""",
                item,
            )
        return item

    def claim_next_run(self):
        stale_before = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT * FROM runs WHERE status='queued' OR
                (status='running' AND updated_at < ?) ORDER BY created_at LIMIT 1""",
                (stale_before,),
            ).fetchone()
            if row:
                db.execute(
                    "UPDATE runs SET status='running',updated_at=? WHERE id=?", (now(), row["id"])
                )
            return dict(row) if row else None

    def touch_run(self, run_id: str):
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET updated_at=? WHERE id=? AND status='running'", (now(), run_id)
            )

    def ensure_chunks(self, run_id: str, groups: list[list[tuple[str, int]]]):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT 1 FROM run_chunks WHERE run_id=? LIMIT 1", (run_id,)
            ).fetchone()
            if not existing:
                db.executemany(
                    "INSERT INTO run_chunks(run_id,chunk_key,pages_json,status) VALUES(?,?,?,'pending')",
                    [
                        (run_id, f"{index:05d}", json.dumps(pages))
                        for index, pages in enumerate(groups, start=1)
                    ],
                )

    def pending_chunks(self, run_id: str):
        with self.connect() as db:
            rows = db.execute(
                """SELECT chunk_key,pages_json FROM run_chunks WHERE run_id=? AND status='pending'
                ORDER BY chunk_key""",
                (run_id,),
            ).fetchall()
            return [
                (row["chunk_key"], [tuple(page) for page in json.loads(row["pages_json"])])
                for row in rows
            ]

    def save_chunk(self, run_id: str, chunk_key: str, brief: DraftBrief):
        with self.connect() as db:
            cursor = db.execute(
                """UPDATE run_chunks SET status='done',brief_json=?
                WHERE run_id=? AND chunk_key=? AND status='pending'""",
                (brief.model_dump_json(), run_id, chunk_key),
            )
            if cursor.rowcount != 1:
                raise ValueError("Chunk is not pending")
            db.execute("UPDATE runs SET updated_at=? WHERE id=?", (now(), run_id))

    def split_chunk(self, run_id: str, chunk_key: str):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT pages_json FROM run_chunks
                WHERE run_id=? AND chunk_key=? AND status='pending'""",
                (run_id, chunk_key),
            ).fetchone()
            if not row:
                raise ValueError("Chunk is not pending")
            pages = json.loads(row["pages_json"])
            if len(pages) < 2:
                raise ValueError("A single-page chunk cannot be split")
            midpoint = len(pages) // 2
            db.execute(
                "UPDATE run_chunks SET status='split' WHERE run_id=? AND chunk_key=?",
                (run_id, chunk_key),
            )
            db.executemany(
                "INSERT INTO run_chunks(run_id,chunk_key,pages_json,status) VALUES(?,?,?,'pending')",
                [
                    (run_id, f"{chunk_key}.0", json.dumps(pages[:midpoint])),
                    (run_id, f"{chunk_key}.1", json.dumps(pages[midpoint:])),
                ],
            )
            db.execute("UPDATE runs SET updated_at=? WHERE id=?", (now(), run_id))

    def completed_briefs(self, run_id: str):
        with self.connect() as db:
            rows = db.execute(
                """SELECT brief_json FROM run_chunks WHERE run_id=? AND status='done'
                ORDER BY chunk_key""",
                (run_id,),
            ).fetchall()
            return [DraftBrief.model_validate_json(row["brief_json"]) for row in rows]

    def chunk_progress(self, run_id: str):
        with self.connect() as db:
            row = db.execute(
                """SELECT COUNT(*) AS total,
                SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
                FROM run_chunks WHERE run_id=? AND status!='split'""",
                (run_id,),
            ).fetchone()
            return {"done": row["done"] or 0, "total": row["total"]}

    def requeue_run(self, run_id: str):
        with self.connect() as db:
            cursor = db.execute(
                """UPDATE runs SET status='queued',error=NULL,updated_at=?
                WHERE id=? AND status IN ('failed','partial')""",
                (now(), run_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Only failed or partial runs can be retried")

    def finish_run(self, run_id: str, brief, *, status: str = "draft", error: str | None = None):
        if status not in ("draft", "partial"):
            raise ValueError("Invalid brief status")
        with self.connect() as db:
            current = db.execute(
                "SELECT opportunity_id,document_hashes FROM runs WHERE id=?", (run_id,)
            ).fetchone()
            previous_reviews = {}
            if current:
                existing = db.execute(
                    """SELECT claim_json,review_status,review_value,review_reason,reviewed_at
                    FROM claims WHERE run_id=? AND review_status IN ('accepted','edited')""",
                    (run_id,),
                ).fetchall()
                for row in existing:
                    previous_reviews.setdefault(row["claim_json"], row)
                prior = db.execute(
                    """SELECT c.claim_json,c.review_status,c.review_value,c.review_reason,c.reviewed_at
                    FROM claims c JOIN runs r ON r.id=c.run_id
                    WHERE r.opportunity_id=? AND r.document_hashes=? AND r.id<>?
                    AND c.review_status IN ('accepted','edited')
                    ORDER BY r.created_at DESC""",
                    (current["opportunity_id"], current["document_hashes"], run_id),
                ).fetchall()
                for row in prior:
                    previous_reviews.setdefault(row["claim_json"], row)
            db.execute("DELETE FROM claims WHERE run_id=?", (run_id,))
            db.execute(
                "UPDATE runs SET status=?,brief_json=?,error=?,updated_at=? WHERE id=?",
                (status, brief.model_dump_json(), error[:500] if error else None, now(), run_id),
            )
            for position, claim in enumerate(brief.claims):
                claim_json = claim.model_dump_json()
                previous = previous_reviews.get(claim_json)
                db.execute(
                    """INSERT INTO claims(id,run_id,position,claim_json,review_status,review_value,
                    review_reason,reviewed_at) VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        run_id,
                        position,
                        claim_json,
                        previous["review_status"] if previous else None,
                        previous["review_value"] if previous else None,
                        previous["review_reason"] if previous else None,
                        previous["reviewed_at"] if previous else None,
                    ),
                )

    def fail_run(self, run_id: str, error: str):
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET status='failed',error=?,updated_at=? WHERE id=?",
                (error[:500], now(), run_id),
            )

    def add_event(self, event):
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id,event_json,created_at) VALUES(?,?,?)",
                (event.run_id.split(":")[0], event.model_dump_json(), now()),
            )

    def run(self, run_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                return None
            result = dict(row)
            claims = db.execute(
                "SELECT * FROM claims WHERE run_id=? ORDER BY position", (run_id,)
            ).fetchall()
            brief_json = result.pop("brief_json")
            result["brief"] = json.loads(brief_json) if brief_json else None
            if result["brief"] is not None:
                result["brief"]["claims"] = [
                    {
                        "id": claim["id"],
                        **json.loads(claim["claim_json"]),
                        "review_status": claim["review_status"],
                        "review_value": claim["review_value"],
                        "review_reason": claim["review_reason"],
                    }
                    for claim in claims
                ]
            result["events"] = [
                json.loads(event["event_json"])
                for event in db.execute(
                    "SELECT event_json FROM events WHERE run_id=? ORDER BY id", (run_id,)
                )
            ]
            result["progress"] = self.chunk_progress(run_id)
            return result

    def latest_run(self, opportunity_id: str):
        with self.connect() as db:
            row = db.execute(
                "SELECT id FROM runs WHERE opportunity_id=? ORDER BY created_at DESC LIMIT 1",
                (opportunity_id,),
            ).fetchone()
            return self.run(row["id"]) if row else None

    def review_claim(self, claim_id: str, status: str, value: str | None, reason: str):
        with self.connect() as db:
            row = db.execute(
                """SELECT c.claim_json,r.status AS run_status FROM claims c
                JOIN runs r ON r.id=c.run_id WHERE c.id=?""",
                (claim_id,),
            ).fetchone()
            if not row:
                return False
            if row["run_status"] != "draft":
                raise ValueError("Only complete drafts can be reviewed")
            if status in ("accepted", "edited") and not json.loads(row["claim_json"])["citations"]:
                raise ValueError("Claim needs a source citation before approval")
            cursor = db.execute(
                """UPDATE claims SET review_status=?,review_value=?,review_reason=?,reviewed_at=?
                WHERE id=?""",
                (status, value, reason, now(), claim_id),
            )
            return cursor.rowcount > 0

    def export_run(self, run_id: str):
        run = self.run(run_id)
        if not run or run["status"] != "draft" or not run["brief"]:
            raise ValueError("Draft brief is not available")
        claims = run["brief"]["claims"]
        if not claims or any(c["review_status"] not in ("accepted", "edited") for c in claims):
            raise ValueError("All claims require review before export")
        if any(not c["citations"] for c in claims):
            raise ValueError("Uncited claims cannot be exported as approved")
        snapshot = {
            "run_id": run_id,
            "opportunity_id": run["opportunity_id"],
            "approved_at": now(),
            "document_hashes": json.loads(run["document_hashes"]),
            "schema_version": run["brief"]["schema_version"],
            "title": run["brief"]["title"],
            "claims": claims,
            "open_questions": run["brief"]["open_questions"],
        }
        with self.connect() as db:
            db.execute(
                "INSERT INTO exports(id,run_id,snapshot_json,created_at) VALUES(?,?,?,?)",
                (str(uuid.uuid4()), run_id, json.dumps(snapshot), now()),
            )
        return snapshot
