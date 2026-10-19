"""Read-only, bounded fresh GitHub Actions capture. Never posts issues or reruns jobs."""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from buildrelay_api.github import GitHub, parse_webhook
from buildrelay_api.workflow import Failure

REPOSITORIES = [
    "pytest-dev/pytest",
    "pallets/flask",
    "astral-sh/ruff",
    "cli/cli",
    "nodejs/node",
    "microsoft/TypeScript",
    "dotnet/runtime",
    "rails/rails",
    "laravel/framework",
    "spring-projects/spring-boot",
    "rust-lang/cargo",
    "vitejs/vite",
]


class CaptureGitHub(GitHub):
    directory = None

    def download(self, url):
        archive = super().download(url)
        (self.directory / "logs.zip").write_bytes(archive)
        return archive

    def json(self, repo, method, path, **kwargs):
        result = super().json(repo, method, path, **kwargs)
        if self.directory is not None and "/attempts/" in path:
            (self.directory / "attempt.json").write_text(json.dumps(result, indent=2))
        return result


def capture(output, repositories, per_repo=2):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    # Keep token in this process only. Never print or persist it, including signed log URLs.
    token = subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()
    os.environ["BUILDRELAY_VALIDATION_TOKEN"] = token
    os.environ["BUILDRELAY_VALIDATION_SECRET"] = secrets.token_urlsafe(32)
    source = CaptureGitHub()
    manifest = {
        "kind": "fresh_public_github_actions_read_only_capture",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "records": [],
        "errors": [],
        "native_webhook_deliveries": False,
        "external_writes": 0,
    }

    def save_manifest():
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def add(repo, metadata, *, fetch_logs):
        event = parse_webhook(
            "workflow_run",
            {
                "action": "completed",
                "repository": {"id": repo["github_id"], "full_name": repo["name"]},
                "workflow_run": metadata,
            },
        )
        ident = f"{event.repository_id}-{event.run_id}-{event.attempt}"
        if any(r["id"] == ident for r in manifest["records"]):
            return
        path = output / ident
        path.mkdir()
        (path / "event.json").write_text(event.model_dump_json(indent=2))
        record = {
            "id": ident,
            "repository": event.repository,
            "run_id": event.run_id,
            "attempt": event.attempt,
            "conclusion": event.conclusion,
            "source_url": event.source_url,
            "status": "metadata_captured",
            "artifacts": {},
        }
        source.directory = path
        if fetch_logs:
            try:
                evidence = source.evidence(repo, event)
                (path / "evidence.json").write_text(json.dumps(evidence, indent=2))
                record.update(
                    status="evidence_captured",
                    truncated=evidence["truncated"],
                    evidence_chars=len(evidence["text"]),
                )
            except Failure as exc:
                record.update(status="source_failure", error=exc.code)
        for file in sorted(path.iterdir()):
            record["artifacts"][file.name] = {
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "bytes": file.stat().st_size,
            }
        manifest["records"].append(record)
        save_manifest()
        print(
            json.dumps({k: record[k] for k in ("id", "repository", "conclusion", "status")}),
            flush=True,
        )

    try:
        for name in repositories:
            repo = {
                "name": name,
                "token_ref": "BUILDRELAY_VALIDATION_TOKEN",
                "secret_ref": "BUILDRELAY_VALIDATION_SECRET",
            }
            source.directory = None
            try:
                identity = source.json(repo, "GET", f"/repos/{name}")
                repo["github_id"] = identity["id"]
                failures = source.json(
                    repo,
                    "GET",
                    f"/repos/{name}/actions/runs",
                    params={"status": "failure", "per_page": per_repo},
                )
                for run in failures["workflow_runs"]:
                    add(repo, run, fetch_logs=True)
                source.directory = None
                successes = source.json(
                    repo,
                    "GET",
                    f"/repos/{name}/actions/runs",
                    params={"status": "success", "per_page": 10},
                )
                if successes["workflow_runs"]:
                    # Prefer an actual rerun-success for a genuine attempt-history lifecycle pair.
                    run = next(
                        (r for r in successes["workflow_runs"] if r["run_attempt"] > 1),
                        successes["workflow_runs"][0],
                    )
                    add(repo, run, fetch_logs=False)
                    if run["run_attempt"] > 1:
                        source.directory = None
                        previous = source.json(
                            repo,
                            "GET",
                            f"/repos/{name}/actions/runs/{run['id']}/attempts/{run['run_attempt'] - 1}",
                        )
                        if previous.get("conclusion") in {"failure", "timed_out"}:
                            add(repo, previous, fetch_logs=True)
            except (Failure, KeyError, ValueError) as exc:
                manifest["errors"].append(
                    {
                        "repository": name,
                        "code": exc.code if isinstance(exc, Failure) else type(exc).__name__,
                    }
                )
                save_manifest()
    finally:
        source.client.close()
        os.environ.pop("BUILDRELAY_VALIDATION_TOKEN", None)
        os.environ.pop("BUILDRELAY_VALIDATION_SECRET", None)
        save_manifest()
    print(
        json.dumps({"records": len(manifest["records"]), "errors": manifest["errors"]}), flush=True
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--repos", nargs="+", default=REPOSITORIES)
    p.add_argument("--per-repo", type=int, default=2, choices=range(1, 4))
    a = p.parse_args()
    capture(a.output, a.repos, a.per_repo)
