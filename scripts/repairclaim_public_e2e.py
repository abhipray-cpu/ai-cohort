"""Actual HTTP/worker evaluation: real official sources plus explicitly authored repair facts.

This is exploratory source-conditioned engineering evaluation, not independent domain
labelling, an actual consumer journey, a model benchmark or a deployment qualification.
"""

import hashlib
import io
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from contracts.repairclaim import Condition, EvidenceAnchor, ProgrammeRevision
from repairclaim_api.store import Store

BASE = "/api/repairclaim/v1"
ROOT = Path(__file__).resolve().parents[1]
# These are assistant-authored exploratory interpretations, not specialist-reviewed gold.
SPECS = [
    (
        "accord-condenser",
        "honda-2021-10199345",
        "Accord Hybrid",
        2018,
        2020,
        "A/C condenser",
        120,
        None,
        "2018–20",
        [
            "defective A/C condenser from the factory",
            "foreign object damage",
            "branded or similar title",
        ],
    ),
    (
        "clarity-condenser",
        "honda-2021-10194957",
        "Clarity Plug-In Hybrid",
        2018,
        2021,
        "A/C condenser",
        120,
        None,
        "2018-21",
        [
            "Check the iN VIN status for eligibility.",
            "foreign object damage",
            "branded or similar title",
        ],
    ),
    (
        "hrv-cvt",
        "honda-2021-10191763",
        "HR-V",
        2016,
        2020,
        "CVT",
        84,
        "150000",
        "2016-2020",
        ["Product Update completed", "VIN"],
    ),
    (
        "crv-powertrain",
        "honda-2024-10253308",
        "CR-V",
        2017,
        2018,
        "engine",
        72,
        None,
        "2017-18",
        ["EX, EX-L, Touring", "requiring repair due to damage", "total loss", "S/B 18-147"],
    ),
    (
        "odyssey-injector",
        "honda-2021-10187289",
        "Odyssey",
        2018,
        2019,
        "fuel injectors",
        120,
        "150000",
        "2018-19",
        ["soŌware update", "VIN"],
    ),
    (
        "pilot-idle-stop",
        "honda-2025-11020578",
        "Pilot",
        2016,
        2016,
        "starter",
        138,
        None,
        "2016–21",
        ["with 9AT", "PGM-FI software must", "VIN", "related to this condition"],
    ),
]


def load_sources(corpus):
    corpus = Path(corpus)
    manifest = json.loads((corpus / "acquisition.json").read_text())
    sources = {}
    for record in manifest["records"]:
        if record["status"] != "parsed":
            continue
        raw = (corpus / "raw" / f"{record['id']}.pdf").read_bytes()
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ValueError("Frozen source hash mismatch")
        parsed = json.loads((corpus / "parsed" / f"{record['id']}.json").read_text())
        if parsed["sha256"] != record["sha256"]:
            raise ValueError("Parsed/source binding mismatch")
        sources[record["id"]] = {**record, "raw": raw, "parsed": parsed}
    return sources


def anchored(source, needle):
    for page in source["parsed"]["pages"]:
        if needle in page["text"]:
            return EvidenceAnchor(
                document_id=source["id"], sha256=source["sha256"], page=page["page"], quote=needle
            )
    raise ValueError(f"Reviewed literal not found: {source['id']}: {needle}")


def programme(spec, sources, *, revision="review-a", old=False):
    family, source_id, model, low, high, component, months, mileage, year_quote, manual = spec
    source = sources[source_id]

    def condition(name, field, operator, expected=None, needle=None, **kwargs):
        return Condition(
            id=name,
            field=field,
            operator=operator,
            expected=expected,
            anchor=anchored(source, needle or str(expected)),
            **kwargs,
        )

    conditions = [
        condition("model", "model", "equals", model),
        condition("year-min", "model_year", "at_least", low, year_quote),
        condition("year-max", "model_year", "at_most", high, year_quote),
        condition("component", "component", "equals", component),
        condition(
            "age",
            "repair_date",
            "within_months",
            months,
            "eighteen (18) month" if months == 138 else f"{months // 12} years",
            reference_field="in_service_date",
            anniversary_policy="clamp_to_last_day",
        ),
    ]
    if mileage:
        conditions.append(
            condition(
                "repair-mileage", "repair_mileage", "at_most", mileage, "150,000 miles", unit="mi"
            )
        )
    conditions += [
        condition(
            f"manual-{index}", "vehicle_confirmation", "manufacturer_confirmation", needle=quote
        )
        for index, quote in enumerate(manual)
    ]
    if old:
        source = sources["honda-2023-10229678"]
        conditions = [
            condition("model", "model", "equals", "Pilot"),
            condition("year-min", "model_year", "at_least", 2016, "2016-2023"),
            condition("year-max", "model_year", "at_most", 2016, "2016-2023"),
            condition("component", "component", "equals", "starter"),
            condition(
                "age",
                "repair_date",
                "within_months",
                120,
                "10 years",
                reference_field="in_service_date",
                anniversary_policy="clamp_to_last_day",
            ),
            condition(
                "manual-vin", "vehicle_confirmation", "manufacturer_confirmation", needle="VIN"
            ),
            condition(
                "manual-prerequisite",
                "vehicle_confirmation",
                "manufacturer_confirmation",
                needle="software must be updated first",
            ),
        ]
    return ProgrammeRevision(
        family_id=family,
        revision=revision,
        category="warranty_extension",
        jurisdiction="US",
        make="Honda",
        reviewer_id="assistant-exploratory-not-independent",
        reviewed_at=datetime.now(UTC),
        conditions=tuple(conditions),
    )


def scenario_matrix(spec):
    family, _, model, year, _, component, months, mileage, _, _ = spec
    endyear = 2018 + months // 12
    endmonth = 1 + months % 12
    date = f"{endyear:04d}-{endmonth:02d}-01"
    base = {
        "model": model,
        "model_year": year,
        "component": component,
        "in_service_date": "2018-01-01",
        "repair_date": "2019-01-01",
        "repair_mileage": "90000",
    }
    return [
        (family + "-within", base, "potentially_applicable"),
        (family + "-at-anniversary", {**base, "repair_date": date}, "potentially_applicable"),
        (
            family + "-past-anniversary",
            {**base, "repair_date": date[:-2] + "02"},
            "appears_outside_conditions",
        ),
        (
            family + "-missing-origin",
            {k: v for k, v in base.items() if k != "in_service_date"},
            "missing_evidence",
        ),
        (
            family + "-wrong-component",
            {**base, "component": "unrelated brake repair"},
            "appears_outside_conditions",
        ),
        (
            family + "-wrong-model",
            {**base, "model": "UNSUPPORTED-FIXTURE-MODEL"},
            "appears_outside_conditions",
        ),
        (
            family + "-mile-boundary",
            {**base, "repair_mileage": mileage or "999999"},
            "potentially_applicable",
        ),
        (
            family + "-over-mile-boundary",
            {**base, "repair_mileage": str(int(mileage) + 1) if mileage else "1000000"},
            "appears_outside_conditions" if mileage else "potentially_applicable",
        ),
    ]


def public_record_scenarios(records, spec):
    if not isinstance(records, list) or not 1 <= len(records) <= 400:
        raise ValueError("invalid_public_record_count")
    seen, scenarios = set(), []
    for record in records:
        facts = record["facts"]
        identifier = record["odi_number"]
        if (
            record["record_type"] != "public_unverified_consumer_complaint_metadata"
            or set(facts) != {"model", "model_year"}
            or identifier in seen
            or not isinstance(identifier, str)
            or not identifier.isdecimal()
        ):
            raise ValueError("invalid_public_record")
        seen.add(identifier)
        # Identity-only checks, not independently reviewed eligibility labels.
        expected = (
            "missing_evidence"
            if facts["model"].casefold() == spec[2].casefold()
            and spec[3] <= facts["model_year"] <= spec[4]
            else "appears_outside_conditions"
        )
        scenarios.append(("nhtsa-" + identifier, facts, expected))
    return scenarios


def repair_document_scenarios():
    """Human-reviewed identity only; no inferred repair date, coverage or payment."""
    identities = [
        ("accord-2008-invoices", "Honda", "Accord", 2008),
        ("odyssey-2002-transmission", "Honda", "Odyssey", 2002),
        ("civic-2015-transmission", "Honda", "Civic", 2015),
        ("accord-2009-inspection", "Honda", "Accord", 2009),
        ("civic-handwritten", "Honda", "Civic", 2015),
        ("crv-2004-consumer-letter", "Honda", "CR-V", 2004),
        ("kia-pre-invoice", "Kia", "Sportage", 2006),
    ]
    return [
        (
            key,
            {"make": make, "model": model, "model_year": year},
            "appears_outside_conditions" if make == "Honda" else None,
        )
        for key, make, model, year in identities
    ]


def run(
    corpus,
    out,
    *,
    jev=False,
    jev_route="vercel",
    families=6,
    programme_index=0,
    public_records=None,
    repair_documents=None,
):
    if (
        jev_route not in {"vercel", "jevmodel"}
        or not 1 <= families <= 6
        or not 0 <= programme_index < 6
    ):
        raise ValueError("invalid_campaign_scope")
    if repair_documents is not None and (public_records is not None or jev):
        raise ValueError("Repair-document track is local-only; no personal document egress")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    sources = load_sources(corpus)
    # Freeze interpretations and declared expected outcomes before running the product.
    selected_specs = SPECS[programme_index : programme_index + families]
    programmes = [programme(spec, sources) for spec in selected_specs]
    scenarios = [scenario for spec in selected_specs for scenario in scenario_matrix(spec)]
    live_keys, packet_indices = set(), set()
    repair_sources = load_sources(repair_documents) if repair_documents is not None else {}
    if repair_documents is not None:
        scenarios = repair_document_scenarios()
        if {name for name, _, _ in scenarios} != set(repair_sources):
            raise ValueError("Reviewed repair-document corpus mismatch")
        packet_indices = set(range(len(scenarios)))
    if public_records is not None:
        if families != 1:
            raise ValueError("Public metadata track requires one explicitly scoped programme")
        records = json.loads(Path(public_records).read_text())
        scenarios = public_record_scenarios(records, selected_specs[0])
        (out / "public-records.json").write_text(json.dumps(records, indent=2))
        models_seen = set()
        for i, (name, facts, _) in enumerate(scenarios):
            if facts["model"] not in models_seen:
                models_seen.add(facts["model"])
                live_keys.add(name)
                packet_indices.add(i)
    (out / "interpretations.json").write_text(
        json.dumps([p.model_dump(mode="json") for p in programmes], indent=2)
    )
    (out / "scenarios.json").write_text(json.dumps(scenarios, indent=2))
    store = Store(out / "state" / "repairclaim.sqlite3")
    password = secrets.token_urlsafe(24)
    store.provision_owner("validation-owner", password)
    store.provision_owner("validation-other", password)
    for source in sources.values():
        store.capture_source(source["id"], source["final_url"], source["raw"], source["parsed"])
    for p in programmes:
        store.activate_programme(p)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "REPAIRCLAIM_DATA_DIR": str((out / "state").resolve()),
        "REPAIRCLAIM_PUBLIC_ORIGIN": origin,
        "REPAIRCLAIM_ENABLE_CODEX": "0",
        "REPAIRCLAIM_ENABLE_SOURCE_CHECKS": "0",
        "REPAIRCLAIM_ENABLE_JEV": "1" if jev else "0",
        "REPAIRCLAIM_JEV_ROUTE": jev_route,
        "REPAIRCLAIM_JEVMODEL_TOKEN_LIMIT": "50000" if public_records is not None else "90000",
        "REPAIRCLAIM_JEV_BUDGET_DB": str((out / "jev-budget.sqlite3").resolve()),
    }
    processes = []
    results = []
    checks = []
    started = time.monotonic()
    report = {
        "evidence_type": "actual_official_PDF_sources_plus_authored_repair_facts",
        "consumer_e2e": False,
        "actual_provider_calls": 0,
        "browser_e2e": False,
        "independent_labels": False,
        "quality_gate_passed": False,
        "source_count": len(sources),
        "programme_configurations": len(programmes),
        "cases": results,
        "checks": checks,
        "live_decisions": [],
        "campaign_status": "running",
        "jev_route": jev_route if jev else None,
    }
    if jev:
        if not os.environ.get("JEV_API_KEY"):
            raise ValueError("JEV_API_KEY required for explicit live campaign")
        report["evidence_type"] += "_with_live_jev_advisory"
    if public_records is not None:
        report["evidence_type"] = (
            "actual_official_public_consumer_complaint_vehicle_metadata_and_official_programme_PDF"
        )
        report["actual_private_invoices"] = 0
        report["public_complaint_records"] = len(scenarios)
        report["narratives_or_personal_identifiers_sent_to_model"] = False
    if repair_documents is not None:
        report.update(
            evidence_type="actual_public_repair_document_packs_with_human_entered_vehicle_identity",
            actual_repair_document_packs=len(repair_sources),
            private_consented_customer_cases=0,
            automatic_invoice_understanding_passed=False,
            narratives_or_personal_identifiers_sent_to_model=False,
        )

    def credits():
        from decimal import Decimal

        with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as gateway:
            response = gateway.get(
                "https://ai-gateway.vercel.sh/v1/credits",
                headers={"Authorization": "Bearer " + os.environ["JEV_API_KEY"]},
            )
            response.raise_for_status()
            data = response.json()
            return {k: str(Decimal(data[k])) for k in ("balance", "total_used")}

    if jev and jev_route == "vercel":
        from decimal import Decimal

        report["credits_before"] = credits()
        if Decimal(report["credits_before"]["balance"]) < Decimal("0.60"):
            raise ValueError(
                "Insufficient existing balance for bounded campaign; no purchase attempted"
            )

    def save():
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        report["passed_cases"] = sum(r["pass"] for r in results)
        report["failed_cases"] = sum(not r["pass"] for r in results)
        if jev and (out / "jev-budget.sqlite3").exists():
            import sqlite3
            from decimal import Decimal

            with sqlite3.connect(out / "jev-budget.sqlite3") as db:
                rows = db.execute("SELECT status,receipt FROM calls").fetchall()
            report["actual_provider_calls"] = len(rows)
            report["reserved_usd"] = (
                str(Decimal(len(rows)) * Decimal("0.01")) if jev_route == "vercel" else None
            )
            priced = [
                json.loads(r)["cost_usd"]
                for _, r in rows
                if r and json.loads(r).get("cost_usd") is not None
            ]
            report["known_cost_usd"] = (
                str(sum((Decimal(r) for r in priced), Decimal(0)))
                if jev_route == "vercel"
                else None
            )
            if jev_route == "jevmodel":
                report["actual_input_tokens"] = sum(
                    json.loads(r)["input_tokens"] for _, r in rows if r
                )
                report["remaining_proxy_tokens"] = next(
                    (json.loads(r)["tokens_remaining"] for _, r in reversed(rows) if r), None
                )
            report["unknown_or_invalid_calls"] = sum(s != "success" for s, _ in rows)
        (out / "report.json").write_text(json.dumps(report, indent=2))

    with (
        (out / "process.log").open("wb") as log,
        httpx.Client(base_url=origin, headers={"origin": origin}, timeout=75) as client,
        httpx.Client(base_url=origin, headers={"origin": origin}, timeout=20) as other,
    ):

        def call(method, path, **kwargs):
            response = client.request(method, BASE + path, **kwargs)
            if response.status_code not in {200, 201, 202, 204}:
                raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:160]}")
            return None if response.status_code == 204 else response.json()

        def wait_job(job):
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                result = call("GET", "/jobs/" + job["id"])
                if result["status"] not in {"queued", "running"}:
                    return result
                time.sleep(0.1)
            raise TimeoutError("Actual worker job exceeded validation wait bound")

        def new_case(facts, title):
            vehicle = call(
                "POST",
                "/vehicles",
                json={
                    "make": facts.get("make", "Honda"),
                    "model": facts["model"],
                    "model_year": facts["model_year"],
                    "jurisdiction": "US",
                },
            )
            case = call("POST", "/cases", json={"vehicle_id": vehicle["id"], "title": title})
            values = [
                {
                    "field": key,
                    "value": value,
                    "status": "user_reported",
                    **({"unit": "mi"} if key == "repair_mileage" else {}),
                }
                for key, value in facts.items()
            ]
            call(
                "POST",
                f"/cases/{case['id']}/fact-revisions",
                json={
                    "expected_revision": 1,
                    "facts": [
                        *(
                            []
                            if "make" in facts
                            else [{"field": "make", "value": "Honda", "status": "user_reported"}]
                        ),
                        *values,
                    ],
                },
            )
            return vehicle, case

        def investigate(case, key):
            revision = call("GET", f"/cases/{case['id']}")["revision"]
            request = {"expected_revision": revision, "key": key}
            use_jev = jev and (
                public_records is None or key.removesuffix("-after-upload") in live_keys
            )
            if use_jev:
                preview = call("GET", f"/cases/{case['id']}/analysis-preview?mode=jev")
                assert preview["context"]["destination"] == (
                    "jevmodel.org" if jev_route == "jevmodel" else "vercel_ai_gateway_jev"
                )
                request.update(mode="jev", allowance=1, egress_fingerprint=preview["fingerprint"])
            job = wait_job(
                call(
                    "POST",
                    f"/cases/{case['id']}/investigations",
                    json=request,
                )
            )
            if use_jev:
                advice = job.get("result", {}).get("jev_advice")
                report["live_decisions"].append(
                    {
                        "scenario": key,
                        "job_status": job["status"],
                        "rules_state": job.get("result", {}).get("search", {}).get("state"),
                        "advice": advice,
                        "attempts": job.get("attempts", []),
                        "approved_context_sha256": preview["fingerprint"],
                    }
                )
                save()
                if (
                    advice is None
                    or len(job["attempts"]) != 1
                    or job["attempts"][0]["status"] != "success"
                ):
                    report["campaign_status"] = "halted_provider_failure"
                    results.append(
                        {
                            "scenario": key,
                            "pass": False,
                            "error": "live_provider_no_validated_decision",
                        }
                    )
                    save()
                    raise InterruptedError(
                        "Live Jev failed; campaign halted without retries; inspect report"
                    )
                if advice["assessment"]["choice"] != job["result"]["search"]["state"]:
                    assert job["status"] == "manual_review"
            return job

        def erase(case):
            revision = call("GET", f"/cases/{case['id']}")["revision"]
            call("DELETE", f"/cases/{case['id']}", headers={"if-match": str(revision)})

        try:
            for arguments in [
                [
                    "-m",
                    "uvicorn",
                    "repairclaim_api.api:app_from_env",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                ["-m", "repairclaim_api.worker"],
            ]:
                child_env = dict(env)
                if arguments[0] != "-m" or arguments[1] != "repairclaim_api.worker":
                    child_env.pop("JEV_API_KEY", None)
                processes.append(
                    subprocess.Popen(
                        [sys.executable, *arguments],
                        env=child_env,
                        cwd=ROOT,
                        stdout=log,
                        stderr=log,
                    )
                )
            for _ in range(150):
                try:
                    if client.get("/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError("Owned process exited during startup")
                time.sleep(0.1)
            if client.get("/health/ready").status_code != 200:
                raise RuntimeError("Product not ready")
            for connection, username in [(client, "validation-owner"), (other, "validation-other")]:
                session = connection.post(
                    BASE + "/sessions", json={"username": username, "password": password}
                )
                session.raise_for_status()
                connection.headers["x-csrf-token"] = session.json()["csrf_token"]
            for index, (name, facts, expected) in enumerate(scenarios):
                case = None
                try:
                    vehicle, case = new_case(
                        facts,
                        (
                            "PUBLIC NHTSA metadata; not a verified invoice: "
                            if public_records is not None
                            else "AUTHORED boundary scenario: "
                        )
                        + name,
                    )
                    job = investigate(case, name)
                    actual = job["result"]["search"]["state"]
                    okay = actual == expected
                    result = {
                        "scenario": name,
                        "expected": expected,
                        "actual": actual,
                        "pass": okay,
                        "job_state": job["status"],
                        "provider_attempts": len(job["attempts"]),
                    }
                    if repair_documents is not None or (
                        (index in packet_indices)
                        if public_records is not None
                        else (index % 8 == 0)
                    ):
                        # An actual public document is classified other, never called a consumer invoice.
                        source = (
                            repair_sources[name]
                            if repair_documents is not None
                            else sources[
                                selected_specs[0 if public_records is not None else index // 8][1]
                            ]
                        )
                        revision = call("GET", f"/cases/{case['id']}")["revision"]
                        document = call(
                            "POST",
                            f"/cases/{case['id']}/documents?filename={source['id']}.pdf&kind=other&revision={revision}",
                            content=source["raw"],
                            headers={"content-type": "application/octet-stream"},
                        )
                        wait_job({"id": document["job_id"]})
                        document = call("GET", "/documents/" + document["id"])
                        assert document["status"] == "ready"
                        assert document["sha256"] == source["sha256"]
                        if repair_documents is not None:
                            result["automatic_proposal_count"] = len(
                                document["parsed"]["proposals"]
                            )
                            result["source_sha256"] = source["sha256"]
                            result["document_kind"] = "other"
                            if document["parsed"]["proposals"]:
                                revision = call("GET", f"/cases/{case['id']}")["revision"]
                                confirmed = call(
                                    "POST",
                                    f"/documents/{document['id']}/confirm",
                                    json={"selected": [0], "expected_revision": revision},
                                )
                                assert any(
                                    fact["status"] == "confirmed"
                                    and fact.get("anchor", {}).get("sha256") == source["sha256"]
                                    for fact in confirmed["facts"]
                                    if fact.get("anchor")
                                )
                                result["actual_proposal_confirmation_verified"] = True
                            if name == "accord-2008-invoices":
                                # Visually reviewed invoice, p5. Total is NOT payment evidence.
                                revision = call("GET", f"/cases/{case['id']}")["revision"]
                                corrected = call(
                                    "POST",
                                    f"/cases/{case['id']}/corrections",
                                    json={
                                        "expected_revision": revision,
                                        "replacement": {
                                            "field": "invoice_total",
                                            "value": "106.45",
                                            "unit": "USD",
                                            "status": "user_reported",
                                        },
                                    },
                                )
                                total = next(
                                    f for f in corrected["facts"] if f["field"] == "invoice_total"
                                )
                                assert (
                                    total["status"] == "user_reported" and total["anchor"] is None
                                )
                                assert not any(
                                    f["field"] in {"paid_amount", "payment_proof"}
                                    for f in corrected["facts"]
                                )
                                result["manual_invoice_total_not_promoted_to_payment"] = True
                                rejected = client.post(
                                    BASE + f"/cases/{case['id']}/outcomes",
                                    json={
                                        "key": "must-not-invent-refund",
                                        "evidence_page": 5,
                                        "evidence_quote": "106.45",
                                        "event": {
                                            "id": "not-a-refund",
                                            "kind": "received",
                                            "amount": {"amount": "106.45", "currency": "USD"},
                                            "evidence_class": "documented",
                                            "evidence_ref": document["id"],
                                            "repair_line_id": "historical-invoice",
                                        },
                                    },
                                )
                                assert rejected.status_code == 422
                                assert rejected.json()["code"] == "outcome_evidence_ambiguous"
                                result["invoice_cannot_be_recorded_as_documented_refund"] = True
                            workspace = call("GET", f"/cases/{case['id']}/workspace")
                            assert workspace["totals"] == {}
                            result["no_invented_financial_outcome"] = True
                            reminder = call(
                                "POST",
                                f"/cases/{case['id']}/reminders",
                                json={
                                    "due_at": "2026-11-01T12:00:00+00:00",
                                    "timezone": "UTC",
                                    "provenance": "user_entered",
                                    "label": "VALIDATION ONLY: review historical record",
                                },
                            )
                            call("DELETE", "/reminders/" + reminder["id"])
                            result["reminder_create_cancel_verified"] = True
                            export = client.get(BASE + f"/cases/{case['id']}/export")
                            export.raise_for_status()
                            with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
                                assert archive.namelist()
                            assert (
                                other.get(BASE + f"/cases/{case['id']}/export").status_code == 404
                            )
                            result["private_case_export_verified"] = True
                        assert other.get(BASE + "/documents/" + document["id"]).status_code == 404
                        # Actual source PDF upload changed inputs, so recompute before drafting.
                        job = investigate(case, name + "-after-upload")
                        if repair_documents is not None and facts["make"] != "Honda":
                            assert job["result"]["search"]["reason"] == "unsupported_make"
                            denied = client.post(
                                BASE + f"/cases/{case['id']}/packets",
                                json={
                                    "job_id": job["id"],
                                    "recipient": "Not contacted",
                                    "key": name + "-blocked",
                                    "attachments": [],
                                },
                            )
                            assert denied.status_code == 409
                            assert denied.json()["code"] == "assessment_not_ready"
                            result["unsupported_make_packet_blocked"] = True
                            results.append(result)
                            print(json.dumps(result), flush=True)
                            continue
                        packet = call(
                            "POST",
                            f"/cases/{case['id']}/packets",
                            json={
                                "job_id": job["id"],
                                "recipient": "AUTHORED validation dealer (not contacted)",
                                "key": name + "-packet",
                                "attachments": [
                                    {
                                        "document_id": document["id"],
                                        "mode": "sanitized",
                                        "redactions": [],
                                    }
                                ],
                            },
                        )
                        render = wait_job(call("POST", f"/packets/{packet['id']}/render", json={}))
                        packet = call("GET", "/packets/" + packet["id"])
                        assert packet["status"] == "rendered", render
                        assert (
                            client.post(
                                BASE + f"/packets/{packet['id']}/download", json={}
                            ).status_code
                            == 409
                        )
                        call(
                            "POST",
                            f"/packets/{packet['id']}/approve",
                            json={"fingerprint": packet["fingerprint"]},
                        )
                        response = client.post(BASE + f"/packets/{packet['id']}/download", json={})
                        response.raise_for_status()
                        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                            manifest = json.loads(archive.read("manifest.json"))
                            pdf = archive.read("packet.pdf")
                            assert hashlib.sha256(pdf).hexdigest() == manifest["pdf_sha256"]
                            assert manifest["fingerprint"] == packet["fingerprint"]
                        (out / f"{name}-packet.pdf").write_bytes(pdf)
                        (out / f"{name}-manifest.json").write_text(json.dumps(manifest, indent=2))
                        if repair_documents is not None and name == "accord-2008-invoices":
                            revision = call("GET", f"/cases/{case['id']}")["revision"]
                            call(
                                "POST",
                                f"/cases/{case['id']}/corrections",
                                json={
                                    "expected_revision": revision,
                                    "replacement": {
                                        "field": "invoice_total",
                                        "value": "106.45",
                                        "unit": "USD",
                                        "status": "user_reported",
                                    },
                                },
                            )
                            assert (
                                client.post(
                                    BASE + f"/packets/{packet['id']}/download", json={}
                                ).status_code
                                == 409
                            )
                            result["fact_revision_invalidates_approved_download"] = True
                        call("POST", f"/packets/{packet['id']}/revoke", json={})
                        assert (
                            client.post(
                                BASE + f"/packets/{packet['id']}/download", json={}
                            ).status_code
                            == 409
                        )
                        result["actual_packet_pages_and_manifest_verified"] = True
                        result["original_source_pages"] = source["pages"]
                        if repair_documents is not None:
                            call(
                                "POST",
                                f"/vehicles/{vehicle['id']}/monitoring",
                                json={"case_ids": [case["id"]], "ttl": 3600},
                            )
                            call("DELETE", f"/vehicles/{vehicle['id']}/monitoring")
                            result["monitoring_consent_revoke_verified"] = True
                            if name == "civic-handwritten":
                                # Historical regulator correspondence, NOT a reply to our unsent packet.
                                revision = call("GET", f"/cases/{case['id']}")["revision"]
                                response_doc = call(
                                    "POST",
                                    f"/cases/{case['id']}/documents?filename=historical-correspondence.pdf&kind=response&revision={revision}",
                                    content=source["raw"],
                                    headers={"content-type": "application/octet-stream"},
                                )
                                wait_job({"id": response_doc["job_id"]})
                                response_request = {
                                    "document_id": response_doc["id"],
                                    "key": "historical-response",
                                }
                                recorded = call(
                                    "POST", f"/cases/{case['id']}/responses", json=response_request
                                )
                                repeated = call(
                                    "POST", f"/cases/{case['id']}/responses", json=response_request
                                )
                                assert recorded["id"] == repeated["id"]
                                assert recorded["review_required"] is True
                                assert recorded["comparison"]["manufacturer_confirmation"] is False
                                assert any(
                                    r["page"] == 2 and r["category"] == "missing_evidence"
                                    for r in recorded["reasons"]
                                )
                                followup_job = investigate(case, name + "-historical-followup")
                                followup = call(
                                    "POST",
                                    f"/cases/{case['id']}/packets",
                                    json={
                                        "job_id": followup_job["id"],
                                        "recipient": "VALIDATION ONLY: not contacted",
                                        "key": "historical-followup",
                                        "purpose": "followup",
                                        "attachments": [],
                                    },
                                )
                                wait_job(call("POST", f"/packets/{followup['id']}/render", json={}))
                                followup = call("GET", "/packets/" + followup["id"])
                                assert followup["status"] == "rendered"
                                assert call("GET", f"/cases/{case['id']}/workspace")["totals"] == {}
                                result["historical_correspondence_review_and_followup_verified"] = (
                                    True
                                )
                    results.append(result)
                except (
                    AssertionError,
                    RuntimeError,
                    TimeoutError,
                    httpx.HTTPError,
                    KeyError,
                    ValueError,
                ) as error:
                    results.append({"scenario": name, "pass": False, "error": str(error)[:500]})
                finally:
                    if case:
                        try:
                            erase(case)
                        except (RuntimeError, httpx.HTTPError) as error:
                            checks.append(
                                {"check": "cleanup", "pass": False, "error": str(error)[:160]}
                            )
                    save()
                print(json.dumps(results[-1]), flush=True)
            if repair_documents is not None:
                call("POST", "/account/erase", json={"confirmation": "DELETE MY ACCOUNT"})
                checks.append(
                    {
                        "check": "owned_validation_account_erasure_revokes_session_and_preserves_other_owner",
                        "pass": client.get(BASE + "/vehicles").status_code == 401
                        and other.get(BASE + "/vehicles").status_code == 200,
                    }
                )
            if public_records is not None or repair_documents is not None:
                report["local_mixed_data_workflow_passed"] = (
                    len(results) == len(scenarios)
                    and all(r["pass"] for r in results)
                    and all(c["pass"] for c in checks)
                )
                report["campaign_status"] = (
                    (
                        "passed_public_repair_document_transport"
                        if repair_documents is not None
                        else "passed_public_metadata_integration"
                    )
                    if report["local_mixed_data_workflow_passed"]
                    else "failed"
                )
                save()
                return report
            # Genuine source evolution: 2023 ten-year notice -> 2025 2016-Pilot +18 months.
            pilot = SPECS[-1]
            store.activate_programme(
                programme(pilot, sources, revision="historical-2023", old=True)
            )
            vehicle, case = new_case(
                {
                    "model": "Pilot",
                    "model_year": 2016,
                    "component": "starter",
                    "in_service_date": "2016-01-01",
                    "repair_date": "2027-01-01",
                    "repair_mileage": "90000",
                },
                "AUTHORED retrospective boundary; future repair date, not an actual invoice",
            )
            before = investigate(case, "genuine-old-version")
            call(
                "POST",
                f"/vehicles/{vehicle['id']}/monitoring",
                json={"case_ids": [case["id"]], "ttl": 86400},
            )
            store.activate_programme(programme(pilot, sources, revision="revised-2025"))
            store.rematch_monitoring()
            notifications = call("GET", "/notifications")
            relevant = [
                n
                for n in notifications
                if n["case_id"] == case["id"] and n["change"]["family"] == "pilot-idle-stop"
            ]
            after = investigate(case, "genuine-new-version")
            check = {
                "check": "genuine_source_evolution_and_consented_notification",
                "before": before["result"]["search"]["state"],
                "after": after["result"]["search"]["state"],
                "notification_count": len(relevant),
            }
            check["pass"] = (
                check["before"] == "appears_outside_conditions"
                and check["after"] == "potentially_applicable"
                and len(relevant) == 1
            )
            checks.append(check)
            call("DELETE", f"/vehicles/{vehicle['id']}/monitoring")
            checks.append(
                {"check": "monitoring_revoke", "pass": call("GET", "/notifications") == []}
            )
            erase(case)
            checks.append(
                {
                    "check": "deleted_case_hidden_from_owner",
                    "pass": client.get(BASE + f"/cases/{case['id']}").status_code == 404,
                }
            )
        finally:
            if jev and jev_route == "vercel":
                try:
                    report["credits_after"] = credits()
                except httpx.HTTPError:
                    report["credits_after"] = "unavailable"
            save()
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
    report["local_mixed_data_workflow_passed"] = (
        len(results) == len(scenarios)
        and all(r["pass"] for r in results)
        and all(c["pass"] for c in checks)
    )
    report["campaign_status"] = (
        "passed_bounded_integration" if report["local_mixed_data_workflow_passed"] else "failed"
    )
    save()
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--jev-route", choices=["vercel", "jevmodel"], default="vercel")
    parser.add_argument("--families", type=int, choices=range(1, 7), default=6)
    parser.add_argument("--programme-index", type=int, choices=range(6), default=0)
    parser.add_argument("--public-records", type=Path)
    parser.add_argument("--repair-documents", type=Path)
    parser.add_argument(
        "--jev",
        action="store_true",
        help="Explicit live advisory campaign: max 60 attempts at $0.01 reservation each; prompts for credential",
    )
    args = parser.parse_args()
    if args.jev:
        import getpass

        os.environ["JEV_API_KEY"] = getpass.getpass("Gateway credential (not echoed): ")
    report = run(
        args.corpus,
        args.out,
        jev=args.jev,
        jev_route=args.jev_route,
        families=args.families,
        programme_index=args.programme_index,
        public_records=args.public_records,
        repair_documents=args.repair_documents,
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in {"cases", "checks", "live_decisions"}},
            indent=2,
        )
    )
    raise SystemExit(0 if report["local_mixed_data_workflow_passed"] else 1)
