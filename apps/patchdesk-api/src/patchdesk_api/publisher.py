"""Exact approved GitHub issue effects; ambiguous writes never blindly retry."""

import json
import os
from datetime import UTC, datetime, timedelta

from patchdesk_api.adapters import Transport
from patchdesk_api.common import digest, identifier, now
from patchdesk_api.reports import markdown


class Publisher:
    def __init__(self, store, request=None, enabled=None):
        self.store = store
        self.injected = request is not None
        self.request = request or Transport().request
        self.enabled = (
            bool(enabled) if enabled is not None else os.getenv("PATCHDESK_ENABLE_PUBLISH") == "1"
        )

    def get(self, actor, iid):
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM publications WHERE id=?", (iid,)).fetchone()
        if not row:
            raise ValueError("Publication not found")
        result = dict(row)
        self.store.scope(actor, result["project_id"], "publisher")
        result["payload"] = json.loads(result["payload"])
        result["receipt"] = json.loads(result["receipt"]) if result["receipt"] else None
        if digest(result["payload"]) != result["payload_hash"]:
            raise ValueError("Publication payload integrity failure")
        return result

    def draft(self, actor, report_id, title):
        report = self.store.object(actor, report_id)
        scope = self.store.scope(actor, report["project_id"], "publisher")
        if report["kind"] != "report" or not report["reviewed_by"]:
            raise ValueError("Review report before drafting publication")
        policy = scope["policy"]
        if not policy.get("repository") or not policy.get("repository_id"):
            raise ValueError("Configure exact repository name and numeric ID first")
        iid = identifier()
        body = markdown(report) + f"\n\n<!-- patchdesk-operation:{iid} -->"
        if len(body) > 50000:
            raise ValueError(
                "Report too large for issue body; export instead or create a narrower report"
            )
        payload = {
            "title": title,
            "body": body,
            "repository": policy["repository"],
            "repository_id": policy["repository_id"],
            "connector_epoch": policy["connector_epoch"],
            "connector_fingerprint": digest(os.getenv("PATCHDESK_GITHUB_PUBLISH_TOKEN", "")),
            "operation_id": iid,
        }
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO publications(id,project_id,report_id,report_revision,payload,payload_hash,policy_revision,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    iid,
                    scope["id"],
                    report_id,
                    report["revision"],
                    json.dumps(payload),
                    digest(payload),
                    scope["revision"],
                    now(),
                ),
            )
        return self.get(actor, iid)

    def _valid(self, actor, value):
        scope = self.store.scope(actor, value["project_id"], "publisher")
        report = self.store.object(actor, value["report_id"])
        policy = scope["policy"]
        latest = self.store.latest_report(actor, scope["id"])
        if (
            scope["revision"] != value["policy_revision"]
            or report["revision"] != value["report_revision"]
            or not report["reviewed_by"]
            or not latest
            or latest["id"] != report["id"]
            or report["payload"].get("input_id") != scope["latest_input"]
        ):
            raise ValueError("Stale report/policy/destination approval")
        if (
            policy["repository"] != value["payload"]["repository"]
            or policy["repository_id"] != value["payload"]["repository_id"]
            or policy["connector_epoch"] != value["payload"]["connector_epoch"]
            or digest(os.getenv("PATCHDESK_GITHUB_PUBLISH_TOKEN", ""))
            != value["payload"]["connector_fingerprint"]
        ):
            raise ValueError("Connector or target changed; new approval required")
        return scope

    def approve(self, actor, iid, approval):
        value = self.get(actor, iid)
        self._valid(actor, value)
        if (
            value["status"] != "draft"
            or value["revision"] != approval.expected_revision
            or value["payload_hash"] != approval.payload_hash
        ):
            raise ValueError("Approval must bind exact draft revision/hash")
        with self.store.connect() as db:
            changed = db.execute(
                "UPDATE publications SET status='approved',revision=revision+1,approved_by=?,expires=? WHERE id=? AND status='draft' AND revision=?",
                (
                    actor,
                    (datetime.now(UTC) + timedelta(minutes=15)).isoformat(),
                    iid,
                    approval.expected_revision,
                ),
            ).rowcount
            if not changed:
                raise ValueError("Stale publication approval")
        self.store.event(None, value["project_id"], "publication", "approved", iid)
        return self.get(actor, iid)

    def dispatch(self, actor, iid):
        value = self.get(actor, iid)
        self._valid(actor, value)
        if value["status"] == "published":
            return value
        if value["status"] != "approved" or value["expires"] <= now():
            raise ValueError("Publication is not approved, expired or outcome unknown")
        if not self.enabled or self.store.setting("publisher_quarantine", False):
            raise ValueError("Publisher disabled/quarantined")
        token = os.getenv("PATCHDESK_GITHUB_PUBLISH_TOKEN", "")
        if not token and not self.injected:
            raise ValueError("Publisher connector credential unavailable")
        headers = {"Authorization": "Bearer " + token} if token else {}
        repo = value["payload"]["repository"]
        info = self.request(f"https://api.github.com/repos/{repo}", headers=headers)
        if info.get("id") != value["payload"]["repository_id"]:
            raise ValueError("Remote repository identity changed")
        self._valid(
            actor, value
        )  # Recheck after network preflight, immediately before reservation/effect.
        with self.store.connect() as db:
            changed = db.execute(
                "UPDATE publications SET status='sending',revision=revision+1 WHERE id=? AND status='approved' AND revision=? AND expires>?",
                (iid, value["revision"], now()),
            ).rowcount
            if not changed:
                raise ValueError("Publication already dispatched or approval expired")
        try:
            # An accepted-but-lost write must never use the read retry loop.
            response = self.request(
                f"https://api.github.com/repos/{repo}/issues",
                data={"title": value["payload"]["title"], "body": value["payload"]["body"]},
                headers=headers,
                retry=False,
            )
            if (
                not isinstance(response.get("number"), int)
                or response["number"] <= 0
                or response.get("body") != value["payload"]["body"]
                or response.get("title") != value["payload"]["title"]
            ):
                raise ValueError("Publication response could not be verified")
            receipt = {
                "number": response["number"],
                "url": f"https://github.com/{repo}/issues/{response['number']}",
                "received_at": now(),
            }
            status = "published"
        except (OSError, ValueError, TimeoutError, KeyError, TypeError):
            status, receipt = "outcome_unknown", None
        with self.store.connect() as db:
            db.execute(
                "UPDATE publications SET status=?,receipt=?,revision=revision+1 WHERE id=?",
                (status, json.dumps(receipt) if receipt else None, iid),
            )
        self.store.event(None, value["project_id"], "publication", status, iid)
        return self.get(actor, iid)

    def reconcile(self, actor, iid):
        value = self.get(actor, iid)
        # Reading a prior result remains scoped to its original repository; no authority to republish.
        if value["status"] not in ("sending", "outcome_unknown", "quarantined"):
            raise ValueError("Publication does not need reconciliation")
        repo = value["payload"]["repository"]
        policy = self.store.scope(actor, value["project_id"], "publisher")["policy"]
        if (
            repo != policy["repository"]
            or policy["repository_id"] != value["payload"]["repository_id"]
        ):
            raise ValueError("Original target no longer authorized")
        token = os.getenv("PATCHDESK_GITHUB_PUBLISH_TOKEN", "")
        headers = {"Authorization": "Bearer " + token} if token else {}
        info = self.request(f"https://api.github.com/repos/{repo}", headers=headers)
        if info.get("id") != value["payload"]["repository_id"]:
            raise ValueError("Original repository identity changed")
        matches = []
        for page in range(1, 6):
            rows = self.request(
                f"https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}",
                headers=headers,
            )
            if not isinstance(rows, list):
                raise ValueError("Invalid reconciliation response")  # noqa: TRY004 - upstream shape
            matches.extend(
                row
                for row in rows
                if f"<!-- patchdesk-operation:{iid} -->" in (row.get("body") or "")
                and row.get("title") == value["payload"]["title"]
                and row.get("body") == value["payload"]["body"]
            )
            if len(rows) < 100:
                break
        if len(matches) == 1 and isinstance(matches[0].get("number"), int):
            receipt = {
                "number": matches[0]["number"],
                "url": f"https://github.com/{repo}/issues/{matches[0]['number']}",
                "reconciled_at": now(),
            }
            with self.store.connect() as db:
                db.execute(
                    "UPDATE publications SET status='published',receipt=?,revision=revision+1 WHERE id=?",
                    (json.dumps(receipt), iid),
                )
        return self.get(actor, iid)
