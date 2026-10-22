"""Explicit acceptance helpers. Public source replay is not live-model evidence."""

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from agent_core.codex_local import LocalCodexProvider
from pydantic import BaseModel, ConfigDict

from .core import digest


def campaign_checks(report):
    orgs = report["organizations"]
    result = {"three_isolated_organizations": len({o["id"] for o in orgs}) == 3}
    if report["mode"] == "source":
        result.update(
            source_volume=sum(o.get("products", 0) for o in orgs) >= 1000,
            unique_events=sum(o.get("unique_events", 0) for o in orgs) >= 10000,
            privacy=bool(orgs) and all(o.get("raw_payload_leaks") == 0 for o in orgs),
            healthy_no_incidents=bool(orgs) and all(o.get("healthy_incidents") == 0 for o in orgs),
        )
    else:
        tasks = report["tasks"]
        result.update(
            source_fidelity=len(tasks) == 6 and all(t["source_fidelity_passed"] for t in tasks),
            six_distinct_products=len({t["source_ref"] for t in tasks}) == 6,
            bounded_calls=(
                report.get("calls_reserved", 0) == 0
                if report["mode"] == "integration"
                else 0 < report.get("calls_reserved", 0) <= 24
            ),
            rollback=bool(orgs) and all(o.get("rollback_verified_at") for o in orgs),
            signed_control_evidence=bool(orgs)
            and all(o.get("independent_signature_verification") is True for o in orgs),
            alert_delivery=report.get("notifications_received", 0) >= 3,
            phoenix_readback=bool(orgs)
            and all(
                o.get("phoenix", {}).get("status") == "verified"
                and len(o.get("phoenix", {}).get("verified_releases", {})) == 2
                and o.get("phoenix_privacy_checked") is True
                for o in orgs
            ),
        )
        if report.get("trace_profile") == "mlflow-phoenix-v1":
            result["measured_trace_gate"] = bool(orgs) and all(
                o.get("measured_trace_gate_passed") is True for o in orgs
            )
            result["mlflow_readback"] = bool(orgs) and all(
                o.get("mlflow", {}).get("status") == "verified"
                and len(o.get("mlflow", {}).get("verified_releases", {})) == 2
                and o.get("mlflow_privacy_checked") is True
                for o in orgs
            )
    return {k: bool(v) for k, v in result.items()}


def cohort_checks(report):
    """Fail-closed terminal checks for the separately authorized larger campaign."""
    tasks = report.get("tasks", [])
    calls = report.get("calls_reserved", 0)
    values = report.get("metrics", {}).values()
    spans = report.get("unique_spans", 0)
    return {
        "bounded_approval": report.get("approval")
        == "user-2026-10-22-releasefence-200-products-240-calls"
        and report.get("calls_cap") == 240
        and report.get("products_cap") == 200
        and 0 < calls <= 240,
        "distinct_inferred_products": len(tasks) == 200
        and len({t["source_ref"] for t in tasks if t.get("attempts")}) == 200,
        "source_fidelity": len(tasks) == 200
        and all(t.get("source_fidelity_passed") is True for t in tasks),
        "clock_continuity": bool(tasks)
        and all(0 <= t.get("ended_at", 0) - t.get("started_at", 0) <= 240 for t in tasks),
        "call_accounting": calls > 0
        and sum(len(t.get("attempts", [])) for t in tasks) == calls
        and sum(v.get("model_calls", 0) for v in values) == calls,
        "accepted_task_accounting": sum(v.get("accepted", 0) for v in values) == 200,
        "complete_dual_export": spans >= 400 and report.get("verified_export_count") == 2 * spans,
        "safe_inconclusive": report.get("decision", {}).get("decision") == "inconclusive"
        and report.get("expansion_rejected_status") in {403, 409},
        "verified_rollback": report.get("control_evidence", {}).get("rollout", {}).get("state")
        == "rollback_verified",
        "owned_cleanup": report.get("owned_api_worker_stopped") is True
        and report.get("owned_backends_stopped") is True,
    }


def archive_sources(paths, destination, workspace):
    """Normalize absolute runner paths before joining under the evidence root."""
    workspace = Path(workspace).resolve()
    for path in paths:
        source = Path(path).resolve()
        relative = source.relative_to(workspace)
        target = Path(destination) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


def source_checks(row):
    f, raw = row["facts"], row["raw"]
    quantity = re.fullmatch(r"\s*([\d.]+)\s*(fl oz|[A-Za-z]+)\s*", raw.get("packageWeight", ""))
    return {
        "product_id": bool(f["product_id"]),
        "brand": bool(f["brand"].strip()) and f["brand"] == raw.get("brandName"),
        "name": bool(f["name"].strip()) and f["name"] == raw.get("description"),
        "ingredients": bool(f["ingredients"].strip())
        and f["ingredients"] == raw.get("ingredients"),
        "positive_quantity": Decimal(f["net_quantity"]) > 0,
        "unit": f["net_unit"] in {"g", "kg", "ml", "mL", "l", "L", "oz", "fl oz", "lb"},
        "source_ref": f["source_ref"] == f"USDA:FDC:{raw['fdcId']}@2026-04-30",
        "fdc_id": type(raw["fdcId"]) is int and raw["fdcId"] > 0,
        "gtin": raw["gtinUpc"] == f["product_id"],
        "package_quantity": bool(quantity)
        and Decimal(quantity[1]) == Decimal(f["net_quantity"])
        and quantity[2].lower() == f["net_unit"].lower(),
    }


def load_corpus(root):
    root = Path(root)
    manifest_raw = (root / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    raw = (root / "records.jsonl").read_bytes()
    if len(raw) > 100_000_000 or digest(raw) != manifest["records_hash"]:
        raise ValueError("corpus hash/size mismatch")
    rows = [json.loads(line) for line in raw.splitlines() if line]
    ids = [r["facts"]["product_id"] for r in rows]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("empty or duplicate source product")
    for row in rows:
        checks = source_checks(row)
        if not all(checks.values()):
            raise ValueError(
                "source facts failed: " + ",".join(k for k, v in checks.items() if not v)
            )
    return rows, {
        "records_sha256": digest(raw),
        "manifest_sha256": digest(manifest_raw),
        "unique_products": len(ids),
        "source_url": manifest.get("url"),
        "license": manifest.get("license"),
        "human_labels": 0,
    }


class CallBudget:
    """Reserve before spawn. Failed/unknown calls remain spent across restarts."""

    def __init__(self, path, approval, *, limit=24):
        if not approval or type(limit) is not int or not 1 <= limit <= 240:
            raise ValueError("explicit bounded approval required")
        self.path = Path(path)
        with self.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS approval(identity TEXT, cap INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, ordinal INTEGER)")
            row = db.execute("SELECT identity,cap FROM approval").fetchone()
            if row and row != (approval, limit):
                raise ValueError("approval identity/cap mismatch")
            if not row:
                db.execute("INSERT INTO approval VALUES(?,?)", (approval, limit))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        if os.name != "nt":
            os.chmod(self.path, 0o600)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def reserve(self, id):
        with self.db() as db:
            count = db.execute("SELECT count(*) FROM calls").fetchone()[0]
            cap = db.execute("SELECT cap FROM approval").fetchone()[0]
            if count >= cap:
                raise ValueError("live budget exhausted")
            db.execute("INSERT INTO calls VALUES(?,?)", (id, count + 1))
            return count + 1

    def count(self):
        with self.db() as db:
            return db.execute("SELECT count(*) FROM calls").fetchone()[0]


class FactAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str
    brand: str
    name: str
    ingredients: str
    net_quantity: str
    net_unit: str
    source_ref: str


class AcceptanceCodex(LocalCodexProvider):
    """Shared provider port, no model/auth setting overrides, no external tools."""

    def __init__(self):
        allowed = {
            "PATH",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "TMPDIR",
            "CODEX_HOME",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "HTTPS_PROXY",
            "HTTP_PROXY",
            "NO_PROXY",
        }
        disabled = (
            "shell_tool",
            "apps",
            "multi_agent",
            "hooks",
            "memories",
            "plugins",
            "browser_use",
            "computer_use",
            "image_generation",
            "in_app_browser",
            "in_app_local_automation",
            "goals",
            "view_image",
            "unified_exec",
        )
        super().__init__(
            isolated=True,
            timeout_seconds=90,
            max_output_bytes=100_000,
            config_overrides=tuple(f"features.{name}=false" for name in disabled)
            + ('web_search="disabled"', "mcp_servers={}", "features.code_mode.enabled=false"),
            environment={k: v for k, v in os.environ.items() if k.upper() in allowed},
        )
        self.receipt = None

    def _run(self, args, prompt):
        result = super()._run(args, prompt)
        self.receipt = None
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "turn.completed":
                u = event.get("usage", {})
                keys = ("input_tokens", "output_tokens", "cached_input_tokens")
                if all(type(u.get(k)) is int and u[k] >= 0 for k in keys):
                    self.receipt = {k: u[k] for k in keys}
        return result
