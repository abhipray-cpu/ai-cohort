import json

import pytest
from agent_core.provider import ProviderTimeoutError, StructuredGeneration
from clausegate_api.worker import run_once
from test_clausegate_core import decide, findings, setup


def test_full_context_planning_keeps_related_clauses_together_when_request_fits(tmp_path):
    from clausegate_api.worker import plan_chunks, request_parts

    s, c = setup(tmp_path)
    c = s.import_text(
        "owner",
        c["id"],
        c["revision"],
        "Return all copies.\n" + "x" * 26000,
        "context.txt",
    )
    doc = s.document("owner", c["document_id"])
    groups = plan_chunks(c, doc)
    assert len(groups) == 1
    prompt, schema = request_parts(c, doc, groups[0], 0, 1)
    assert len(prompt) + len(json.dumps(schema)) <= 47800
    from clausegate_api.worker import INSTRUCTIONS

    payload = json.loads(prompt[len(INSTRUCTIONS) :])
    assert [s["quote"] for s in payload["source_spans"]] == [s["quote"] for s in doc["spans"]]


def test_provider_failure_has_safe_diagnostics_without_raw_stderr(tmp_path):
    s, c = queue(tmp_path)

    class Unavailable:
        def generate(self, **kwargs):
            return StructuredGeneration(
                text="", exit_code=42, elapsed_ms=1, stderr="sensitive-token", tools_audited=False
            )

    run_once(s, provider=Unavailable())
    events = s.audit("owner", c["id"])["items"]
    diagnostic = next(e for e in events if e["kind"] == "provider_failed")
    assert diagnostic["detail"]["exit_code"] == 42
    assert "sensitive-token" not in json.dumps(events)


class Provider:
    def __init__(self, values):
        self.values = iter(values)
        self.prompts = []

    def generate(self, **kwargs):
        self.prompts.append(kwargs["prompt"])
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return StructuredGeneration(
            text=value if isinstance(value, str) else json.dumps(value),
            exit_code=0,
            elapsed_ms=1,
            tools_audited=True,
        )


def queue(tmp_path):
    s, c = setup(tmp_path)
    c = s.set_egress("owner", c["id"], c["revision"], True)
    s.enqueue("owner", c["id"], c["revision"], "analysis-1")
    return s, c


def test_invalid_json_repair_logs_failure_then_pauses_without_live_process(tmp_path):
    s, c = queue(tmp_path)
    p = Provider(["not json", {"findings": [f.model_dump() for f in findings(s, c)]}])
    assert run_once(s, provider=p)
    current = s.case("owner", c["id"])
    assert current["state"] == "waiting_human"
    assert len(p.prompts) == 2
    assert not run_once(s, provider=p)
    assert any(e["kind"] == "validation_failed" for e in s.audit("owner", c["id"])["items"])
    assert "gold" not in p.prompts[0] and "long-test-password" not in p.prompts[0]


def test_timeout_is_partial_not_an_approval_and_usage_survives_restart(tmp_path):
    s, c = queue(tmp_path)
    run_once(s, provider=Provider([ProviderTimeoutError("timeout")]))
    assert s.case("owner", c["id"])["state"] == "partial"
    j = s.jobs("owner", c["id"])[0]
    assert j["calls"] == 1 and j["status"] == "partial"
    assert any(e["kind"] == "provider_timeout" for e in s.audit("owner", c["id"])["items"])


def test_unaudited_provider_cannot_publish_findings(tmp_path):
    s, c = queue(tmp_path)

    class Bad:
        def generate(self, **kwargs):
            return StructuredGeneration(
                text=json.dumps({"findings": [f.model_dump() for f in findings(s, c)]}),
                exit_code=0,
                elapsed_ms=1,
            )

    run_once(s, provider=Bad())
    assert s.case("owner", c["id"])["state"] == "partial"


def test_human_approval_resumes_and_final_review_is_exact_and_independent(tmp_path):
    s, c = queue(tmp_path)
    run_once(s, provider=Provider([{"findings": [f.model_dump() for f in findings(s, c)]}]))
    c = s.case("owner", c["id"])
    decide(s, c)
    assert run_once(s, provider=Provider([]))
    current = s.case("owner", c["id"])
    assert current["state"] == "review_ready"
    with pytest.raises(ValueError):
        s.export("reviewer", c["id"])
    reviewed = s.finalize(
        "reviewer",
        c["id"],
        current["revision"],
        current["packet"]["sha256"],
        "Reviewed entire internal packet",
        True,
    )
    assert reviewed["state"] == "finalized"
    assert s.export("owner", c["id"])["reviewer"] == "reviewer"
    s.import_text("owner", c["id"], reviewed["revision"], "Different wording.", "nda.txt")
    with pytest.raises(ValueError):
        s.export("owner", c["id"])


def test_source_change_during_provider_call_never_commits_old_analysis(tmp_path):
    s, c = queue(tmp_path)

    class Race:
        def generate(self, **kwargs):
            current = s.case("owner", c["id"])
            s.import_text("owner", c["id"], current["revision"], "New source.", "nda.txt")
            return StructuredGeneration(
                text=json.dumps({"findings": [f.model_dump() for f in findings(s, c)]}),
                exit_code=0,
                elapsed_ms=1,
                tools_audited=True,
            )

    run_once(s, provider=Race())
    current = s.case("owner", c["id"])
    assert current["state"] == "stale" and not current["packet"] and not current["findings"]


def test_later_timeout_keeps_chunk_checkpoint_and_explicit_retry_resumes(tmp_path):
    from clausegate_api.worker import plan_chunks

    s, c = setup(tmp_path)
    c = s.import_text(
        "owner", c["id"], c["revision"], "Return all copies.\n" + "x" * 55000, "long.txt"
    )
    c = s.set_egress("owner", c["id"], c["revision"], True)
    doc = s.document("owner", c["document_id"])
    assert len(plan_chunks(c, doc)) == 2
    first = {
        "findings": [
            {
                "check_id": "h",
                "label": "Entailment",
                "assessment": "supported",
                "evidence_ids": [doc["spans"][0]["id"]],
                "rationale": "First chunk evidence",
            }
        ]
    }
    s.enqueue("owner", c["id"], c["revision"], "first")
    run_once(s, provider=Provider([first, ProviderTimeoutError("second chunk")]))
    assert s.jobs("owner", c["id"])[0]["cursor"] == 1
    c = s.case("owner", c["id"])
    s.enqueue("owner", c["id"], c["revision"], "explicit-retry")
    p = Provider(
        [
            {
                "findings": [
                    {
                        "check_id": "h",
                        "label": "NotMentioned",
                        "assessment": "supported",
                        "evidence_ids": [],
                        "rationale": "No additional clause in remaining chunk",
                    }
                ]
            }
        ]
    )
    run_once(s, provider=p)
    assert len(p.prompts) == 1
    assert s.case("owner", c["id"])["state"] == "waiting_human"
    assert sum(j["calls"] for j in s.jobs("owner", c["id"])) == 3
    with pytest.raises(ValueError, match="exhausted"):
        s.enqueue("owner", c["id"], s.case("owner", c["id"])["revision"], "third-grant")


def test_pipeline_upgrade_does_not_reuse_old_chunk_cursor(tmp_path, monkeypatch):
    import clausegate_api.store as domain

    s, c = queue(tmp_path)
    run_once(s, provider=Provider([ProviderTimeoutError("first version")]))
    with s.connect() as db:
        old_snapshot = db.execute("SELECT snapshot FROM jobs").fetchone()[0]
        db.execute("UPDATE jobs SET cursor=1, results='[[]]'")
    monkeypatch.setattr(domain, "ANALYSIS_VERSION", "future-test-version")
    c = s.case("owner", c["id"])
    job = s.enqueue("owner", c["id"], c["revision"], "new-pipeline")
    with s.connect() as db:
        job = dict(db.execute("SELECT * FROM jobs WHERE id=?", (job["id"],)).fetchone())
    assert job["cursor"] == 0
    assert job["results"] == "[]" and job["snapshot"] != old_snapshot


def test_egress_denial_calls_no_provider_and_preserves_manual_review(tmp_path):
    s, c = setup(tmp_path)
    s.enqueue("owner", c["id"], c["revision"], "denied")
    p = Provider([])
    run_once(s, provider=p)
    assert not p.prompts
    assert s.jobs("owner", c["id"])[0]["calls"] == 0
    c = s.case("owner", c["id"])
    assert c["state"] == "partial"
    c = s.submit_findings(
        "reviewer", c["id"], c["revision"], findings(s, c), "Explicit manual fallback review"
    )
    assert c["state"] == "waiting_human"


def test_expired_worker_lease_cannot_publish_and_reservation_is_preserved(tmp_path):
    s, c = queue(tmp_path)
    old = s.claim()
    s.reserve(old)
    with s.connect() as db:
        db.execute("UPDATE jobs SET lease_until='2000-01-01' WHERE id=?", (old["id"],))
    new = s.claim()
    assert new["lease"] != old["lease"] and new["calls"] == 1 and new["deadline"] == old["deadline"]
    with pytest.raises(ValueError):
        s.complete_analysis(old, findings(s, c), complete=True, reason="Late worker")


def test_actor_expiry_during_model_call_is_audited_and_does_not_stick_job(tmp_path):
    s, c = queue(tmp_path)
    values = {"findings": [f.model_dump() for f in findings(s, c)]}

    class Expire(Provider):
        def generate(self, **kwargs):
            with s.connect() as db:
                db.execute("UPDATE members SET expires='2000-01-01' WHERE actor='owner'")
            return super().generate(**kwargs)

    run_once(s, provider=Expire([values]))
    with s.connect() as db:
        assert db.execute("SELECT status FROM jobs").fetchone()[0] == "cancelled"
    assert s.case("reviewer", c["id"])["state"] == "stale"
