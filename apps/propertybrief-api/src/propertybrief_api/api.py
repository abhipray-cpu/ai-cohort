"""Authenticated same-origin API and PropertyBrief web host."""

import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from contracts.propertybrief import ExportRequest, IdentitySelection, Message, PropertyInput, Review
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from propertybrief_api.sources import DEFINITIONS, SourceClient
from propertybrief_api.store import Store


def markdown(report):
    payload = report["payload"]
    draft = payload["draft"]
    lines = [
        f"# PropertyBrief — {payload['identity']['address']}",
        "",
        f"Status: {payload['status']}. Evidence is limited to listed sources.",
        "",
        draft["summary"],
        "",
        "## Findings",
        "",
    ]
    for finding in draft["findings"]:
        lines.append(f"- {finding['text']}")
        for ref in finding["evidence"]:
            definition = DEFINITIONS[ref["source"]]
            lines.append(
                f"  - [{definition.title}]({definition.catalog}), row {ref['record_id']}, {ref['field']}: {ref['value']}"
            )
    lines.extend(["", "## Follow-up plan", ""])
    for task in draft["tasks"]:
        lines.append(
            f"- [{task['priority']}] {task['title']} — {task['recipient']}. {task['reason']} Verify: {task['verification']}"
        )
    lines.extend(["", "## Coverage and limitations", ""])
    lines += [f"- {key}: {value}" for key, value in payload["coverage"].items()]
    lines += [f"- {value}" for value in draft["limitations"]]
    lines += [
        "",
        f"Critique: {payload['critique']['outcome']}",
        f"Stop reason: {payload['stop_reason']}",
        "",
        "## Source manifest",
        "",
    ]
    lines += [
        f"- {item['source']}: {item['retrieved_at']}; SHA-256 {item['sha256']}; snapshot {item['snapshot_id']}"
        for item in payload["source_manifest"]
    ]
    lines += ["", f"Reviewed by: {report['reviewed_by']}", f"Reviewer notes: {report['notes']}"]
    return "\n".join(lines)


def create_app(*, data_dir=None, username=None, password=None, source_client=None):
    username = username or os.getenv("PROPERTYBRIEF_USERNAME")
    password = password or os.getenv("PROPERTYBRIEF_PASSWORD")
    if not username or not password or password == "replace-me":
        raise RuntimeError("Configure PROPERTYBRIEF_USERNAME and PROPERTYBRIEF_PASSWORD")
    store = Store(data_dir or os.getenv("PROPERTYBRIEF_DATA_DIR", "var/propertybrief"))
    app = FastAPI(title="PropertyBrief", version="0.1.0")
    app.state.store = store
    security = HTTPBasic()

    def auth(credentials: HTTPBasicCredentials = Depends(security)):
        if not (
            secrets.compare_digest(credentials.username.encode(), username.encode())
            and secrets.compare_digest(credentials.password.encode(), password.encode())
        ):
            raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Basic"})
        return credentials.username

    def checked(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        except OSError as error:
            raise HTTPException(503, "Source or storage unavailable; retry later") from error

    def found(value):
        if value is None:
            raise HTTPException(404, "Not found")
        return value

    @app.middleware("http")
    async def headers(request, call_next):
        origin = request.headers.get("origin")
        try:
            invalid = origin and urlsplit(origin).netloc != request.headers.get("host")
        except ValueError:
            invalid = True
        if request.method not in ("GET", "HEAD", "OPTIONS") and invalid:
            return JSONResponse(
                {"detail": "Cross-origin changes are not permitted"}, status_code=403
            )
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'",
            }
        )
        return response

    @app.get("/health/live")
    def live():
        return {"status": "ok", "product": "propertybrief"}

    @app.get("/health/ready")
    def ready():
        with store.connect() as db:
            db.execute("SELECT 1").fetchone()
        return {"status": "ok", "product": "propertybrief", "worker_heartbeat": store.heartbeat()}

    @app.get("/v1/settings", dependencies=[Depends(auth)])
    def settings():
        return {
            "sources": [
                {
                    "key": key,
                    "title": definition.title,
                    "catalog": definition.catalog,
                    "required": definition.required,
                }
                for key, definition in DEFINITIONS.items()
            ],
            "max_actions": 16,
            "max_model_calls": 24,
        }

    @app.get("/v1/cases", dependencies=[Depends(auth)])
    def cases():
        return store.cases()

    @app.post("/v1/cases", status_code=201)
    def create(value: PropertyInput, actor=Depends(auth)):
        return store.create_case(value, actor)

    @app.get("/v1/cases/{cid}", dependencies=[Depends(auth)])
    def case(cid: str):
        return found(store.case(cid))

    @app.post("/v1/cases/{cid}/resolve", dependencies=[Depends(auth)])
    def resolve(cid: str):
        item = found(store.case(cid))
        candidates = checked(
            (source_client or SourceClient()).resolve, PropertyInput.model_validate(item["input"])
        )
        checked(store.save_candidates, cid, candidates)
        return store.case(cid)

    @app.post("/v1/cases/{cid}/identity")
    def identity(cid: str, value: IdentitySelection, actor=Depends(auth)):
        return checked(
            store.confirm_identity, cid, value.candidate_id, value.expected_revision, actor
        )

    @app.post("/v1/cases/{cid}/messages", status_code=202)
    def message(
        cid: str, value: Message, actor=Depends(auth), key: str = Header(alias="Idempotency-Key")
    ):
        return checked(store.enqueue, cid, value.content, key, actor)

    @app.post("/v1/cases/{cid}/runs", status_code=202)
    def start(cid: str, actor=Depends(auth), key: str = Header(alias="Idempotency-Key")):
        item = found(store.case(cid))
        return checked(store.enqueue, cid, item["input"]["question"], key, actor)

    @app.post("/v1/cases/{cid}/refresh", status_code=202)
    def refresh(cid: str, actor=Depends(auth), key: str = Header(alias="Idempotency-Key")):
        item = found(store.case(cid))
        return checked(store.enqueue, cid, item["input"]["question"], key, actor, refresh=True)

    @app.get("/v1/runs/{rid}", dependencies=[Depends(auth)])
    def run(rid: str):
        value = found(store.run(rid))
        value.pop("lease", None)
        value.pop("observations", None)
        return value

    @app.post("/v1/runs/{rid}/cancel", dependencies=[Depends(auth)])
    def cancel(rid: str):
        checked(store.cancel, rid)
        return {"status": "requested"}

    @app.post("/v1/runs/{rid}/resume", dependencies=[Depends(auth)])
    def resume(rid: str, key: str = Header(alias="Idempotency-Key")):
        return checked(store.resume, rid, key)

    @app.get("/v1/snapshots/{sid}", dependencies=[Depends(auth)])
    def snapshot(sid: str):
        return found(store.snapshot(sid))

    @app.get("/v1/reports/{report_id}", dependencies=[Depends(auth)])
    def report(report_id: str):
        return found(store.report(report_id))

    @app.patch("/v1/reports/{report_id}/review")
    def review(report_id: str, value: Review, actor=Depends(auth)):
        return checked(store.review, report_id, value, actor)

    @app.post("/v1/reports/{report_id}/exports", dependencies=[Depends(auth)])
    def export(report_id: str, value: ExportRequest):
        result = checked(store.export, report_id)
        if value.format == "markdown":
            return PlainTextResponse(
                markdown(result["report"]),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=propertybrief-{result['id']}.md"
                },
            )
        return result

    @app.get("/v1/exports/{eid}", dependencies=[Depends(auth)])
    def exported(eid: str):
        return found(store.exported(eid))

    web = Path(__file__).resolve().parents[3] / "propertybrief-web" / "dist"

    @app.get("/", dependencies=[Depends(auth)])
    def index():
        if not (web / "index.html").exists():
            raise HTTPException(503, "Build the PropertyBrief web UI first")
        return FileResponse(web / "index.html")

    @app.get("/assets/{name}", dependencies=[Depends(auth)])
    def asset(name: str):
        target = (web / "assets" / name).resolve()
        if target.parent != (web / "assets").resolve() or not target.is_file():
            raise HTTPException(404, "Asset not found")
        return FileResponse(target)

    return app


def app_from_env():
    return create_app()
