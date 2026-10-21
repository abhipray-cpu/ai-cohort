"""Same-origin authenticated ShelfProof HTTP boundary. No publishing endpoint."""

import csv
import hmac
import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated

from contracts.shelfproof import Contract, Draft
from fastapi import Depends, FastAPI, File, Form, Header, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from .core import ImportValidationError, freeze_import, preview_import
from .store import Conflict, Forbidden, Store


class Login(Contract):
    username: Annotated[str, Field(min_length=1, max_length=100)]
    password: Annotated[str, Field(min_length=1, max_length=512)]


class Name(Contract):
    name: Annotated[str, Field(min_length=1, max_length=150)]


class Member(Contract):
    username: Annotated[str, Field(min_length=1, max_length=100)]
    role: Annotated[str, Field(max_length=20)]


class Authority(Contract):
    basis: Annotated[str, Field(min_length=1, max_length=2000)]
    expires: float
    max_calls: Annotated[int, Field(strict=True, ge=1, le=100000)]
    egress: bool


class TaskRequest(Contract):
    import_id: Annotated[str, Field(min_length=1, max_length=128)]
    row: Annotated[int, Field(strict=True, ge=0, le=999)]
    grant: Annotated[str, Field(min_length=1, max_length=128)]
    original: Draft | None = None


class Review(Contract):
    version_hash: Annotated[str, Field(min_length=1, max_length=64)]
    decision: Annotated[str, Field(min_length=1, max_length=20)]
    reason: Annotated[str, Field(min_length=1, max_length=2000)]
    acknowledge_unknown: bool = False
    artifact_hash: Annotated[str, Field(min_length=64, max_length=64)]


class BatchRequest(Contract):
    import_id: Annotated[str, Field(min_length=1, max_length=128)]
    rows: Annotated[
        list[Annotated[int, Field(strict=True, ge=0, le=999)]], Field(min_length=1, max_length=100)
    ]
    grant: Annotated[str, Field(min_length=1, max_length=128)]


class Binding(Contract):
    binding: Annotated[str, Field(min_length=64, max_length=64)]


class Brief(Contract):
    brief: Annotated[str, Field(min_length=1, max_length=2000)]


class Edit(Contract):
    version_hash: Annotated[str, Field(min_length=64, max_length=64)]
    draft: Draft
    grant: Annotated[str, Field(min_length=1, max_length=128)]


def create_app(store: Store, *, origin="http://testserver", administrator=None, web_root=None):
    app = FastAPI(title="ShelfProof", docs_url=None, redoc_url=None)
    attempts = defaultdict(deque)
    secure = origin.startswith("https://")

    @app.middleware("http")
    async def bounds_and_headers(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            maximum = 26 * 1024 * 1024 if "/imports" in request.url.path else 131072
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > maximum:
                    return JSONResponse({"detail": "request exceeds limits"}, status_code=413)
                body.extend(chunk)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; frame-ancestors 'none'; object-src 'none'",
            }
        )
        return response

    @app.exception_handler(Forbidden)
    async def denied(request, exc):
        return JSONResponse({"detail": "object unavailable or action forbidden"}, status_code=403)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": "state, authority or allowance conflict"}, status_code=409)

    @app.exception_handler(csv.Error)
    async def csv_invalid(request, exc):
        return JSONResponse({"detail": "CSV parse/field limit exceeded"}, status_code=422)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(
            {"detail": "invalid input; verify required fields and source mapping"}, status_code=422
        )

    @app.exception_handler(ImportValidationError)
    async def import_invalid(request, exc):
        return JSONResponse(
            {"detail": "Source row validation failed", "issues": exc.issues}, status_code=422
        )

    def session(request: Request):
        try:
            result = store.session(request.cookies.get("shelfproof_session", ""))
        except Forbidden:
            from fastapi import HTTPException

            raise HTTPException(401, "session required") from None
        if request.method not in {"GET", "HEAD", "OPTIONS"} and (
            request.headers.get("origin") != origin
            or not hmac.compare_digest(request.headers.get("x-csrf-token", ""), result["csrf"])
        ):
            raise Forbidden("same-origin CSRF context required")
        return result

    @app.get("/health/live")
    def live():
        return {"live": True}

    @app.get("/health/ready")
    def health():
        try:
            result = store.health()
        except (ValueError, OSError):
            result = {"ready": False}
        return JSONResponse(result, status_code=200 if result["ready"] else 503)

    @app.post("/api/session")
    def login(body: Login, request: Request):
        from fastapi import HTTPException

        if request.headers.get("origin") not in {None, origin}:
            raise Forbidden("origin unavailable")
        key = request.client.host if request.client else "unknown"
        recent = attempts[key]
        now = time.monotonic()
        while recent and recent[0] < now - 60:
            recent.popleft()
        if len(recent) >= 8:
            raise HTTPException(429, "try again later")
        recent.append(now)
        token, csrf = store.login(body.username, body.password)
        response = JSONResponse({"actor": body.username, "csrf": csrf})
        response.set_cookie(
            "shelfproof_session",
            token,
            httponly=True,
            secure=secure,
            samesite="strict",
            max_age=28800,
            path="/",
        )
        return response

    @app.get("/api/me")
    def me(auth=Depends(session)):
        return {"actor": auth["actor"], "csrf": auth["csrf"]}

    @app.delete("/api/session")
    def logout(request: Request, auth=Depends(session)):
        store.logout(request.cookies.get("shelfproof_session", ""))
        response = JSONResponse({"logged_out": True})
        response.delete_cookie("shelfproof_session", path="/")
        return response

    @app.post("/api/users")
    def user(body: Login, auth=Depends(session)):
        if auth["actor"] != administrator:
            raise Forbidden("administrator required")
        store.create_user(body.username, body.password)
        return {"created": body.username}

    @app.get("/api/workspaces")
    def workspaces(auth=Depends(session)):
        return store.workspaces(auth["actor"])

    @app.post("/api/workspaces")
    def workspace(body: Name, auth=Depends(session)):
        return {"id": store.create_workspace(auth["actor"], body.name)}

    @app.post("/api/workspaces/{workspace}/members")
    def member(workspace: str, body: Member, auth=Depends(session)):
        store.add_member(auth["actor"], workspace, body.username, body.role)
        return {"updated": True}

    @app.post("/api/workspaces/{workspace}/rights")
    def rights(workspace: str, body: Authority, auth=Depends(session)):
        return {"id": store.authorize(auth["actor"], workspace, **body.model_dump())}

    @app.get("/api/workspaces/{workspace}/rights")
    def rights_list(workspace: str, auth=Depends(session)):
        return store.rights(auth["actor"], workspace)

    async def upload(file):
        format = Path(file.filename or "").suffix.lower().lstrip(".")
        if format not in {"json", "csv"}:
            raise ValueError("csv/json required")
        raw = await file.read(25 * 1024 * 1024 + 1)
        if len(raw) > 25 * 1024 * 1024:
            from fastapi import HTTPException

            raise HTTPException(413, "import exceeds limits")
        return raw, format

    @app.post("/api/workspaces/{workspace}/imports/preview")
    async def preview(workspace: str, file: UploadFile = File(...), auth=Depends(session)):
        with store.db() as db:
            store._role(db, auth["actor"], workspace, {"owner", "editor"})
        raw, format = await upload(file)
        return await run_in_threadpool(preview_import, raw, format)

    @app.post("/api/workspaces/{workspace}/imports")
    async def freeze(
        workspace: str,
        file: UploadFile = File(...),
        mapping: str = Form(...),
        auth=Depends(session),
    ):
        raw, format = await upload(file)
        frozen = await run_in_threadpool(freeze_import, raw, format, json.loads(mapping))
        return {
            "id": store.save_import(auth["actor"], workspace, raw, frozen),
            "fact_hash": frozen.fact_hash,
            "row_count": len(frozen.facts),
        }

    @app.get("/api/workspaces/{workspace}/tasks")
    def tasks(workspace: str, limit: int = 100, offset: int = 0, auth=Depends(session)):
        return store.tasks(auth["actor"], workspace, limit, offset)

    @app.post("/api/workspaces/{workspace}/tasks")
    def start(
        workspace: str, body: TaskRequest, idempotency_key: str = Header(...), auth=Depends(session)
    ):
        fact = store.import_row(auth["actor"], workspace, body.import_id, body.row)
        return {
            "id": store.create_task(
                auth["actor"],
                workspace,
                fact,
                body.grant,
                idempotency_key,
                original=body.original,
                source_id=body.import_id,
            )
        }

    @app.get("/api/tasks/{task}")
    def task(task: str, auth=Depends(session)):
        return store.task(auth["actor"], task)

    @app.post("/api/tasks/{task}/cancel")
    def cancel(task: str, auth=Depends(session)):
        store.cancel(auth["actor"], task)
        return {"cancelled": True}

    @app.get("/api/tasks/{task}/audit")
    def audit(task: str, auth=Depends(session)):
        return store.audit(auth["actor"], task)

    @app.post("/api/tasks/{task}/reviews")
    def review(task: str, body: Review, auth=Depends(session)):
        store.review(
            auth["actor"],
            task,
            body.version_hash,
            body.decision,
            body.reason,
            acknowledge_unknown=body.acknowledge_unknown,
            artifact_hash=body.artifact_hash,
        )
        return {"reviewed": True}

    @app.post("/api/workspaces/{workspace}/exports")
    def export(workspace: str, auth=Depends(session)):
        return store.export(auth["actor"], workspace)

    @app.get("/api/workspaces/{workspace}/policy")
    def policy(workspace: str, auth=Depends(session)):
        return store.policy(auth["actor"], workspace)

    @app.get("/api/workspaces/{workspace}/imports")
    def imports(workspace: str, auth=Depends(session)):
        return store.imports(auth["actor"], workspace)

    @app.get("/api/workspaces/{workspace}/batches")
    def batches(workspace: str, auth=Depends(session)):
        return store.batches(auth["actor"], workspace)

    @app.post("/api/workspaces/{workspace}/policy")
    def activate_policy(
        workspace: str, body: Brief, idempotency_key: str = Header(...), auth=Depends(session)
    ):
        return {
            "revision": store.activate_policy(
                auth["actor"], workspace, body.model_dump(), idempotency_key
            )
        }

    @app.post("/api/workspaces/{workspace}/batches")
    def prepare_batch(
        workspace: str,
        body: BatchRequest,
        idempotency_key: str = Header(...),
        auth=Depends(session),
    ):
        return {
            "id": store.create_batch(
                auth["actor"], workspace, body.import_id, body.rows, body.grant, idempotency_key
            )
        }

    @app.get("/api/batches/{batch}/egress-preview")
    def batch_preview(batch: str, auth=Depends(session)):
        return store.batch_preview(auth["actor"], batch)

    @app.post("/api/batches/{batch}/start")
    def start_batch(batch: str, body: Binding, auth=Depends(session)):
        return {"tasks": store.start_batch(auth["actor"], batch, body.binding)}

    @app.get("/api/batches/{batch}")
    def batch(batch: str, auth=Depends(session)):
        return store.batch(auth["actor"], batch)

    @app.post("/api/batches/{batch}/cancel")
    def cancel_batch(batch: str, auth=Depends(session)):
        store.cancel_batch(auth["actor"], batch)
        return {"cancelled": True}

    @app.post("/api/tasks/{task}/edits")
    def edit(task: str, body: Edit, idempotency_key: str = Header(...), auth=Depends(session)):
        return {
            "id": store.edit(
                auth["actor"], task, body.version_hash, body.draft, body.grant, idempotency_key
            )
        }

    @app.get("/api/workspaces/{workspace}/review.csv")
    def review_csv(workspace: str, auth=Depends(session)):
        return Response(
            store.review_csv(auth["actor"], workspace),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="shelfproof-UNAPPROVED-review.csv"'
            },
        )

    @app.get("/api/imports/{source}/erasure-preview")
    def erasure_preview(source: str, auth=Depends(session)):
        return store.erasure_preview(auth["actor"], source)

    @app.post("/api/imports/{source}/erase")
    def erase(
        source: str, body: Binding, idempotency_key: str = Header(...), auth=Depends(session)
    ):
        store.erase_import(auth["actor"], source, body.binding, idempotency_key)
        return {"erased": True, "external_backups_and_downloads_recallable": False}

    if web_root and Path(web_root, "index.html").is_file():
        root = Path(web_root)
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(root / "index.html")

    return app


def app_from_env():
    actor = os.environ.get("SHELFPROOF_USERNAME", "")
    password = os.environ.get("SHELFPROOF_PASSWORD", "")
    if not actor or len(password) < 12 or password == "replace-me":
        raise RuntimeError("explicit ShelfProof service credentials required")
    store = Store(os.environ.get("SHELFPROOF_DATA_DIR", "var/shelfproof"))
    with store.db() as db:
        exists = db.execute("SELECT 1 FROM users WHERE name=?", (actor,)).fetchone()
    if not exists:
        store.create_user(actor, password)
    return create_app(
        store,
        origin=os.environ.get("SHELFPROOF_ORIGIN", "http://127.0.0.1:8009"),
        administrator=actor,
        web_root=Path(__file__).resolve().parents[3] / "shelfproof-web/dist",
    )
