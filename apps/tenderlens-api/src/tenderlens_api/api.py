"""TenderLens HTTP API and same-origin web host."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from contracts.tenderlens import ReviewAction
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tenderlens_api.store import Store


class OpportunityCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)


def create_app(
    *,
    data_dir: Path | str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> FastAPI:
    data_dir = Path(data_dir or os.getenv("APP_DATA_DIR", "var/tenderlens"))
    username = username or os.getenv("TENDERLENS_USERNAME")
    password = password or os.getenv("TENDERLENS_PASSWORD")
    if not username or not password:
        raise RuntimeError("TENDERLENS_USERNAME and TENDERLENS_PASSWORD must be configured")

    app = FastAPI(title="TenderLens", version="0.1.0")
    app.state.store = Store(data_dir)
    basic = HTTPBasic()

    def authorize(credentials: HTTPBasicCredentials = Depends(basic)):
        if not (
            secrets.compare_digest(credentials.username, username)
            and secrets.compare_digest(credentials.password, password)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        app.state.store.connect().close()
        return {"status": "ok"}

    @app.get("/v1/opportunities", dependencies=[Depends(authorize)])
    def list_opportunities():
        return app.state.store.list_opportunities()

    @app.post("/v1/opportunities", status_code=201, dependencies=[Depends(authorize)])
    def create_opportunity(body: OpportunityCreate):
        return app.state.store.create_opportunity(body.title)

    @app.get("/v1/opportunities/{opportunity_id}", dependencies=[Depends(authorize)])
    def get_opportunity(opportunity_id: str):
        item = app.state.store.opportunity(opportunity_id)
        if not item:
            raise HTTPException(404, "Opportunity not found")
        return {
            **item,
            "documents": app.state.store.documents_for(opportunity_id),
            "latest_run": app.state.store.latest_run(opportunity_id),
        }

    @app.post(
        "/v1/opportunities/{opportunity_id}/documents",
        status_code=201,
        dependencies=[Depends(authorize)],
    )
    async def add_document(opportunity_id: str, file: UploadFile = File(...)):
        if not app.state.store.opportunity(opportunity_id):
            raise HTTPException(404, "Opportunity not found")
        data = await file.read(30_000_001)
        try:
            return app.state.store.add_document(opportunity_id, file.filename or "upload.pdf", data)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/v1/documents/{document_id}/file", dependencies=[Depends(authorize)])
    def document_file(document_id: str):
        item = app.state.store.document(document_id)
        if not item:
            raise HTTPException(404, "Document not found")
        return FileResponse(
            app.state.store.files / f"{document_id}.pdf",
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    @app.post(
        "/v1/opportunities/{opportunity_id}/runs",
        status_code=202,
        dependencies=[Depends(authorize)],
    )
    def create_run(opportunity_id: str):
        if not app.state.store.opportunity(opportunity_id):
            raise HTTPException(404, "Opportunity not found")
        try:
            return app.state.store.create_run(opportunity_id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/v1/runs/{run_id}", dependencies=[Depends(authorize)])
    def get_run(run_id: str):
        item = app.state.store.run(run_id)
        if not item:
            raise HTTPException(404, "Run not found")
        return item

    @app.post("/v1/runs/{run_id}/retry", status_code=202, dependencies=[Depends(authorize)])
    def retry_run(run_id: str):
        if not app.state.store.run(run_id):
            raise HTTPException(404, "Run not found")
        try:
            app.state.store.requeue_run(run_id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return app.state.store.run(run_id)

    @app.patch("/v1/claims/{claim_id}/review", dependencies=[Depends(authorize)])
    def review_claim(claim_id: str, action: ReviewAction):
        try:
            updated = app.state.store.review_claim(
                claim_id, action.status, action.value, action.reason
            )
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        if not updated:
            raise HTTPException(404, "Claim not found")
        return {"id": claim_id, "status": action.status}

    @app.post("/v1/runs/{run_id}/exports", dependencies=[Depends(authorize)])
    def export_run(run_id: str):
        if not app.state.store.run(run_id):
            raise HTTPException(404, "Run not found")
        try:
            return app.state.store.export_run(run_id)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    web_dist = Path(__file__).resolve().parents[3] / "tenderlens-web" / "dist"
    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/", dependencies=[Depends(authorize)])
        def web_index():
            return FileResponse(web_dist / "index.html", media_type="text/html")

    return app


def app_from_env():
    return create_app()
