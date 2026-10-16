"""Session/CSRF-protected same-origin PatchDesk API and static workbench."""

import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from contracts.patchdesk import (
    Approval,
    CapabilityRequest,
    InputUpload,
    Login,
    Membership,
    Message,
    ProjectCreate,
    ProjectPolicy,
    PublicationDraft,
    RegistryChange,
    RepositoryInput,
    Review,
    UserCreate,
)
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from patchdesk_api.adapters import Sources
from patchdesk_api.publisher import Publisher
from patchdesk_api.registry import default_registry
from patchdesk_api.reports import markdown
from patchdesk_api.store import Store

COOKIE = "patchdesk_session"


def create_app(*, store=None, data_dir=None, sources=None, publisher=None):
    store = store or Store(data_dir or os.getenv("PATCHDESK_DATA_DIR", "var/patchdesk"))
    with store.connect() as db:
        if not db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            username, password = os.getenv("PATCHDESK_USERNAME"), os.getenv("PATCHDESK_PASSWORD")
            if not username or not password:
                raise RuntimeError(
                    "Configure PatchDesk bootstrap username/password before first start"
                )
            store.add_user(username, password, admin=True)
    app = FastAPI(title="PatchDesk", version="0.1.0")
    app.state.store = store
    publisher = publisher or Publisher(store)
    secure = os.getenv("PATCHDESK_SECURE_COOKIES", "0") == "1"

    def checked(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except PermissionError as error:
            raise HTTPException(403, str(error)) from error
        except (ValueError, TypeError, KeyError) as error:
            raise HTTPException(409, str(error)[:300]) from error
        except OSError as error:
            raise HTTPException(503, "Source or storage unavailable") from error

    def actor(request: Request):
        try:
            identity = store.authenticate(request.cookies.get(COOKIE, ""))
        except PermissionError as error:
            raise HTTPException(401, "Sign in required") from error
        if request.method not in ("GET", "HEAD", "OPTIONS") and not secrets.compare_digest(
            request.headers.get("X-CSRF-Token", ""), identity["csrf"]
        ):
            raise HTTPException(403, "CSRF token required")
        return identity

    def admin(identity=Depends(actor)):
        if not identity["admin"]:
            raise HTTPException(403, "Administrator required")
        return identity

    @app.middleware("http")
    async def safety(request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Cross-origin changes denied"}, status_code=403)
            if (
                request.headers.get("content-type", "").split(";")[0] != "application/json"
                and request.method != "DELETE"
            ):
                return JSONResponse({"detail": "JSON changes required"}, status_code=415)
            # Streaming byte guard also handles absent/spoofed Content-Length.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 22 * 1024**2:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
            request._body = bytes(body)
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

    @app.post("/v1/session")
    def login(value: Login, response: Response):
        try:
            result = store.login(value.username, value.password)
        except PermissionError as error:
            raise HTTPException(401, "Invalid credentials or login temporarily limited") from error
        response.set_cookie(
            COOKIE,
            result.pop("token"),
            httponly=True,
            secure=secure,
            samesite="strict",
            max_age=8 * 3600,
            path="/",
        )
        return result

    @app.delete("/v1/session")
    def logout(request: Request, response: Response, identity=Depends(actor)):
        store.logout(request.cookies.get(COOKIE, ""))
        response.delete_cookie(COOKIE, path="/")
        return {"status": "signed_out"}

    @app.get("/v1/me")
    def me(identity=Depends(actor)):
        return identity

    @app.post("/v1/users")
    def add_user(value: UserCreate, identity=Depends(admin)):
        checked(store.add_user, value.username, value.password, value.admin)
        return {"username": value.username}

    @app.get("/v1/projects")
    def projects(identity=Depends(actor)):
        return store.projects(identity["username"])

    @app.get("/v1/clients")
    def clients(identity=Depends(actor)):
        return sorted({p["client"] for p in store.projects(identity["username"])})

    @app.post("/v1/projects")
    def create(value: ProjectCreate, identity=Depends(actor)):
        return checked(store.create_project, identity["username"], value)

    @app.get("/v1/projects/{pid}")
    def project(pid: str, identity=Depends(actor)):
        result = checked(store.project, identity["username"], pid)
        result["report"] = store.latest_report(identity["username"], pid)
        return result

    @app.put("/v1/projects/{pid}/policy")
    def policy(pid: str, value: ProjectPolicy, identity=Depends(actor)):
        return checked(store.update_policy, identity["username"], pid, value)

    @app.put("/v1/projects/{pid}/members")
    def member(pid: str, value: Membership, identity=Depends(actor)):
        checked(store.set_membership, identity["username"], pid, value.username, value.roles)
        return checked(store.project, identity["username"], pid)

    @app.post("/v1/projects/{pid}/inputs")
    def imported(pid: str, value: InputUpload, identity=Depends(actor)):
        result = checked(store.import_input, identity["username"], pid, value)
        return {
            **result,
            "payload": {
                "inventory": result["payload"]["inventory"],
                "origin": result["payload"]["origin"],
                "commit": result["payload"]["commit"],
            },
        }

    @app.post("/v1/projects/{pid}/repository-snapshots")
    def repository(pid: str, value: RepositoryInput, identity=Depends(actor)):
        scope = checked(store.scope, identity["username"], pid, "analyst")
        registry = default_registry(store.setting("disabled_adapters", []))
        checked(
            registry.route,
            CapabilityRequest(capability="repository.snapshot.read", arguments={"ref": value.ref}),
            scope,
        )
        payload = checked((sources or Sources()).repository, scope["policy"], value.ref)
        return checked(
            store.import_input, identity["username"], pid, InputUpload.model_validate(payload)
        )

    @app.get("/v1/projects/{pid}/capabilities")
    def capabilities(pid: str, identity=Depends(actor)):
        scope = checked(store.scope, identity["username"], pid)
        return {
            "registry": default_registry(store.setting("disabled_adapters", [])).snapshot(),
            "roles": scope["roles"],
            "public_package_count": len(scope["policy"]["public_packages"]),
            "model_egress": scope["policy"]["model_egress"],
            "publisher_enabled": publisher.enabled
            and not store.setting("publisher_quarantine", False),
        }

    @app.put("/v1/admin/registry")
    def registry(value: RegistryChange, identity=Depends(admin)):
        current = default_registry(store.setting("disabled_adapters", []))
        checked(current.set_enabled, value.adapter, value.enabled)
        store.set_setting(
            "disabled_adapters", [name for name, d in current.adapters.items() if not d.enabled]
        )
        return current.snapshot()

    def enqueue(pid, value, key, identity, refresh=False):
        return checked(
            store.enqueue,
            identity["username"],
            pid,
            value.content,
            key,
            default_registry(store.setting("disabled_adapters", [])).snapshot(),
            refresh,
        )

    @app.post("/v1/projects/{pid}/runs")
    @app.post("/v1/projects/{pid}/messages")
    def start(
        pid: str,
        value: Message,
        identity=Depends(actor),
        key: str = Header(alias="Idempotency-Key"),
    ):
        result = enqueue(pid, value, key, identity)
        result.pop("lease", None)
        return result

    @app.post("/v1/projects/{pid}/refresh")
    def refresh(
        pid: str,
        value: Message,
        identity=Depends(actor),
        key: str = Header(alias="Idempotency-Key"),
    ):
        result = enqueue(pid, value, key, identity, True)
        result.pop("lease", None)
        return result

    @app.get("/v1/runs/{rid}")
    def run(rid: str, identity=Depends(actor)):
        result = checked(store.run, identity["username"], rid)
        result.pop("lease", None)
        result["results"] = {
            key: {field: val for field, val in value.items() if field not in ("raw", "records")}
            | {"record_count": len(value.get("records", []))}
            for key, value in result["results"].items()
        }
        return result

    @app.post("/v1/runs/{rid}/cancel")
    def cancel(rid: str, identity=Depends(actor)):
        checked(store.cancel, identity["username"], rid)
        return {"status": "requested"}

    @app.post("/v1/runs/{rid}/resume")
    def resume(rid: str, identity=Depends(actor), key: str = Header(alias="Idempotency-Key")):
        result = checked(store.resume, identity["username"], rid, key)
        result.pop("lease", None)
        return result

    @app.get("/v1/snapshots/{oid}")
    @app.get("/v1/reports/{oid}")
    @app.get("/v1/exports/{oid}")
    def artifact(oid: str, identity=Depends(actor)):
        return checked(store.object, identity["username"], oid)

    @app.post("/v1/reports/{oid}/reviews")
    def review(oid: str, value: Review, identity=Depends(actor)):
        return checked(store.review, identity["username"], oid, value)

    @app.post("/v1/reports/{oid}/exports")
    def export(oid: str, format: str = "markdown", identity=Depends(actor)):
        if format not in ("markdown", "json"):
            raise HTTPException(422, "Choose markdown or json")
        result = checked(store.export, identity["username"], oid)
        if format == "json":
            return JSONResponse(
                result,
                headers={
                    "Content-Disposition": f"attachment; filename=patchdesk-{result['id']}.json"
                },
            )
        return PlainTextResponse(
            markdown(result["report"]),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=patchdesk-{result['id']}.md",
                "X-Export-Id": result["id"],
            },
        )

    @app.post("/v1/reports/{oid}/publication-drafts")
    def draft(oid: str, value: PublicationDraft, identity=Depends(actor)):
        return checked(publisher.draft, identity["username"], oid, value.title)

    @app.get("/v1/publications/{iid}")
    def publication(iid: str, identity=Depends(actor)):
        return checked(publisher.get, identity["username"], iid)

    @app.post("/v1/publications/{iid}/approve")
    def approve(iid: str, value: Approval, identity=Depends(actor)):
        return checked(publisher.approve, identity["username"], iid, value)

    @app.post("/v1/publications/{iid}/dispatch")
    def dispatch(iid: str, identity=Depends(actor)):
        return checked(publisher.dispatch, identity["username"], iid)

    @app.post("/v1/publications/{iid}/reconcile")
    def reconciled(iid: str, identity=Depends(actor)):
        return checked(publisher.reconcile, identity["username"], iid)

    @app.get("/health/live")
    def live():
        return {"product": "patchdesk", "status": "ok"}

    @app.get("/health/ready")
    def ready():
        with store.connect() as db:
            db.execute("SELECT 1").fetchone()
        return {
            "product": "patchdesk",
            "status": "ok",
            "worker_heartbeat": store.setting("worker_heartbeat"),
        }

    web = Path(__file__).resolve().parents[3] / "patchdesk-web/dist"

    @app.get("/")
    def index():
        if not (web / "index.html").exists():
            raise HTTPException(503, "Build the PatchDesk frontend first")
        return FileResponse(web / "index.html")

    @app.get("/assets/{name}")
    def asset(name: str):
        path = (web / "assets" / name).resolve()
        if path.parent != (web / "assets").resolve() or not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    return app


def app_from_env():
    return create_app()
