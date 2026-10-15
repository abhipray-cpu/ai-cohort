"""Conservative source interpretation and deterministic provenance checks."""

import re
from datetime import datetime

from propertybrief_api.sources import DEFINITIONS, derive_bbl, digest


def parsed_date(value):
    if not value:
        return None
    for format in ("%Y-%m-%d", "%Y%m%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:10] if "T" in value else value, format).date()
        except ValueError:
            continue
    return None


def normalize_record(source, row, identity):
    definition = DEFINITIONS[source]
    flags = []
    bid = row.get("buildingid", row.get("building_id"))
    bin_value = row.get("bin")
    if bid:
        if bid != identity["building_id"]:
            raise ValueError("Wrong building")
        scope = "building"
    elif bin_value:
        if bin_value != identity.get("bin"):
            raise ValueError("Wrong BIN")
        scope = "building"
        if source == "dob_violations" and all(row.get(field) for field in ("boro", "block", "lot")):
            try:
                if derive_bbl(row["boro"], row["block"], row["lot"]) != identity["bbl"]:
                    flags.append("parcel_identifier_differs")
            except ValueError:
                flags.append("invalid_parcel_fields")
    else:
        bbl = row.get("bbl") or derive_bbl(row.get("boro"), row.get("block"), row.get("lot"))
        if bbl != identity["bbl"]:
            raise ValueError("Wrong parcel")
        scope = "parcel"
        flags.append("parcel_scope")
    if row.get("bbl") and row["bbl"] != identity["bbl"]:
        flags.append("identity_conflict")
    if bid and bin_value and bin_value != identity.get("bin"):
        flags.append("identity_conflict")
    status = "unknown"
    if source == "hpd_violations":
        status = {"Open": "recorded_open", "Close": "historical"}.get(
            row.get("violationstatus"), "unknown"
        )
        text = row.get("novdescription", "")
    elif source in ("hpd_complaints", "dob_complaints"):
        raw_status = row.get("complaint_status", row.get("status", "")).upper()
        status = "historical" if raw_status in ("CLOSE", "CLOSED") else "reported"
        text = row.get("status_description", row.get("complaint_category", "Complaint record"))
        flags.append("complaint_not_verified_violation")
    elif source in ("underlying", "aep"):
        raw_status = row.get("current_status", "")
        status = (
            "historical"
            if "discharg" in raw_status.lower()
            else "recorded_open"
            if raw_status.lower() in ("active", "aep active")
            else "unknown"
        )
        text = raw_status
    elif source == "vacate":
        effective = parsed_date(row.get("vacate_effective_date"))
        rescind = parsed_date(row.get("actual_rescind_date"))
        status = "historical" if rescind else "recorded_open" if effective else "unknown"
        if rescind and effective and rescind < effective:
            flags.append("temporal_conflict")
            status = "unknown"
        text = row.get("primary_vacate_reason", "Order record")
    elif source == "dob_violations":
        category = row.get("violation_category", "").upper()
        status = (
            "historical"
            if "DISMISS" in category or "INACTIVE" in category
            else "recorded_open"
            if "ACTIVE" in category
            else "unknown"
        )
        text = row.get("description", row.get("violation_type", "Violation record"))
        if re.search(
            r"\b(TEST RECORD|DELETED)\b", row.get("disposition_comments", ""), re.IGNORECASE
        ):
            flags.append("test_or_deleted_record")
            status = "unknown"
    else:
        status = (
            "historical"
            if row.get("ecb_violation_status") in ("RESOLVE", "RESOLVED")
            else "unknown"
        )
        text = row.get("violation_description", "ECB record")
    if "identity_conflict" in flags:
        status = "unknown"
    if status == "unknown":
        flags.append("unresolved_status")
    return {
        "id": str(row[definition.key]),
        "source": source,
        "scope": scope,
        "status": status,
        "description": str(text)[:3000],
        "flags": flags,
        "fields": {str(k): str(v) for k, v in row.items()},
    }


def identity_observation(identity):
    raw = identity.get("raw", {})
    row = {
        "id": identity["building_id"],
        "source": "buildings",
        "scope": "building",
        "status": "reported",
        "description": identity["address"],
        "flags": [],
        "fields": {key: str(value) for key, value in raw.items()},
    }
    return {
        "source": "buildings",
        "catalog": DEFINITIONS["buildings"].catalog,
        "records": [row],
        "count": 1,
        "outcome": "success",
        "completeness": "complete_for_query",
        "flags": [],
        "raw": [raw],
        "sha256": digest([raw]),
        "retrieved_at": identity.get(
            "retrieved_at", "Not recorded; refer to corpus acquisition manifest"
        ),
    }


def validate_draft(draft, observations, identity=None):
    if identity:
        observations = {**observations, "buildings": identity_observation(identity)}
    ids = [finding.id for finding in draft.findings]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate finding ID")
    for finding in draft.findings:
        for ref in finding.evidence:
            observation = observations.get(ref.source)
            record = (
                next((row for row in observation["records"] if row["id"] == ref.record_id), None)
                if observation
                else None
            )
            if not record or record["fields"].get(ref.field) != ref.value:
                raise ValueError(
                    f"Citation does not match supplied record fields: {ref.source}/{ref.record_id}/{ref.field}"
                )
            text = finding.text.lower()
            if record["status"] == "historical" and re.search(
                r"\b(currently open|currently active|remains open)\b", text
            ):
                raise ValueError("Historical record described as current")
            if (
                "complaint_not_verified_violation" in record["flags"]
                and "verified violation" in text
                and not re.search(r"\b(not|no|never)\b[^.]{0,60}\bverified violation", text)
            ):
                raise ValueError("Complaint described as verified violation")
            if record["scope"] == "parcel" and "parcel" not in text:
                raise ValueError("Parcel-level evidence requires explicit scope")
    if re.search(
        r"\b(no issues|safe to buy|legally clear|problem.free|guaranteed)\b",
        draft.summary,
        re.IGNORECASE,
    ):
        raise ValueError("Unsupported blanket property conclusion")
    for task in draft.tasks:
        if not set(task.finding_ids).issubset(ids):
            raise ValueError("Task references unknown finding")
