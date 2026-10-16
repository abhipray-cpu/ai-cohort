"""Deterministic matches, source conflicts and qualified candidate checks."""

import re

from patchdesk_api.common import digest
from patchdesk_api.inventory import matches, osv_match


def reference(result, index, field, value):
    return {
        "snapshot_id": result.get("snapshot_id"),
        "adapter": result["adapter"],
        "path": ["records", index, *field],
        "value": value,
    }


def github_match(record, name, version):
    if record.get("withdrawn_at"):
        return None
    answers = [
        matches(version, entry.get("vulnerable_version_range", ""))
        for entry in record.get("vulnerabilities", [])
        if entry.get("package", {}).get("ecosystem") == "npm"
        and entry["package"].get("name") == name
    ]
    return True if True in answers else None if not answers or None in answers else False


def fixed_versions(record, name):
    values = set()
    for affected in record.get("affected", []):
        if (
            affected.get("package", {}).get("name") == name
            and affected["package"].get("ecosystem") == "npm"
        ):
            for span in affected.get("ranges", []):
                if span.get("type") == "SEMVER":
                    values.update(e["fixed"] for e in span.get("events", []) if "fixed" in e)
    for entry in record.get("vulnerabilities", []):
        if entry.get("package", {}).get("name") == name and entry.get("first_patched_version"):
            fixed = entry["first_patched_version"]
            values.add(fixed.get("identifier") if isinstance(fixed, dict) else fixed)
    return sorted(v for v in values if isinstance(v, str))


def reconcile(inventory, results, policy):
    advisories, releases = {}, []
    for _, result in sorted(results.items()):
        if result.get("capability") == "advisories.detail":
            for index, record in enumerate(result.get("records", [])):
                aid = record.get("id", record.get("ghsa_id"))
                if aid:
                    advisories.setdefault(aid, []).append((result, index, record))
        elif result.get("capability") == "releases.lookup":
            releases.extend(
                (result, index, record) for index, record in enumerate(result.get("records", []))
            )
    parents = {aid: aid for aid in advisories}

    def root(aid):
        while parents[aid] != aid:
            parents[aid] = parents[parents[aid]]
            aid = parents[aid]
        return aid

    seen = {}
    for aid, assertions in sorted(advisories.items()):
        identities = {aid}
        for _, _, record in assertions:
            identities.update(
                a for a in record.get("aliases", []) if a.startswith(("CVE-", "GHSA-"))
            )
            if record.get("cve_id"):
                identities.add(record["cve_id"])
        for alias in sorted(identities):
            if alias in seen:
                a, b = root(aid), root(seen[alias])
                parents[max(a, b)] = min(a, b)
            else:
                seen[alias] = aid
    grouped, group_ids = {}, {}
    for aid, assertions in sorted(advisories.items()):
        canonical = root(aid)
        grouped.setdefault(canonical, []).extend(assertions)
        group_ids.setdefault(canonical, set()).add(aid)
    advisories = grouped
    findings, conflicts, candidates = [], [], []
    for package in sorted(inventory["packages"], key=lambda p: p["location"]):
        for aid, assertions in sorted(advisories.items()):
            applicable = []
            for result, index, record in assertions:
                value = (
                    osv_match(record, package["name"], package["version"])
                    if "affected" in record
                    else github_match(record, package["name"], package["version"])
                )
                mentioned = any(
                    a.get("package", {}).get("name") == package["name"]
                    and a.get("package", {}).get("ecosystem") == "npm"
                    for a in record.get("affected", record.get("vulnerabilities", []))
                )
                if mentioned:
                    field = "affected" if "affected" in record else "vulnerabilities"
                    applicable.append(
                        {
                            "adapter": result["adapter"],
                            "match": value,
                            "range_fingerprint": digest(record.get(field, [])),
                            "evidence": reference(result, index, [field], record.get(field, [])),
                            "record": record,
                        }
                    )
            if not applicable or all(item["match"] is False for item in applicable):
                continue
            fid = digest([package["id"], aid])[:24]
            values = {item["match"] for item in applicable}
            conflict = len(values) > 1 or None in values
            if conflict:
                conflicts.append(
                    {
                        "id": "conflict-" + fid,
                        "category": "affected_range",
                        "finding_id": fid,
                        "reason": "Sources disagree or range/withdrawal semantics are unresolved; no source majority vote",
                        "assertions": [
                            {k: v for k, v in item.items() if k != "record"} for item in applicable
                        ],
                    }
                )
            finding = {
                "id": fid,
                "package_id": package["id"],
                "package": package["name"],
                "version": package["version"],
                "location": package["location"],
                "dev": package["dev"],
                "advisory_id": aid,
                "aliases": sorted(
                    group_ids[aid] - {aid}
                    | {alias for item in applicable for alias in item["record"].get("aliases", [])}
                    | {
                        item["record"]["cve_id"]
                        for item in applicable
                        if item["record"].get("cve_id")
                    }
                ),
                "status": "needs_investigation" if conflict else "needs_action",
                "claim": "Recorded dependency matches an advisory; application reachability/exploitability is not established.",
                "summary": next(
                    (
                        item["record"]["summary"][:1200]
                        for item in applicable
                        if isinstance(item["record"].get("summary"), str)
                    ),
                    "Recorded dependency advisory requires review.",
                ),
                "evidence": [item["evidence"] for item in applicable],
                "lineage_note": "OSV/GitHub assertions may share upstream data; not independent votes.",
            }
            for source_result, source_index, source_record in assertions:
                if (
                    isinstance(source_record.get("summary"), str)
                    and source_record["summary"][:1200] == finding["summary"]
                ):
                    finding["evidence"].append(
                        reference(
                            source_result, source_index, ["summary"], source_record["summary"]
                        )
                    )
                    break
            findings.append(finding)
            for result, index, release in releases:
                if (
                    release.get("name") != package["name"]
                    or release.get("version") == package["version"]
                ):
                    continue
                target = release["version"]
                checks = [
                    osv_match(item["record"], package["name"], target)
                    if "affected" in item["record"]
                    else github_match(item["record"], package["name"], target)
                    for item in applicable
                ]
                declared = package.get("declared", "")
                if declared.startswith("npm:"):
                    declared = declared.rsplit("@", 1)[-1]
                engine = release.get("engines", {}).get("node")
                candidates.append(
                    {
                        "id": digest([fid, target])[:24],
                        "finding_id": fid,
                        "package": package["name"],
                        "target": target,
                        "advisory_check": "outside_captured_range"
                        if checks and all(check is False for check in checks)
                        else "unresolved_or_affected",
                        "declared_check": matches(target, declared) if declared else None,
                        "engine_check": matches(policy["node_version"], engine)
                        if engine and policy.get("node_version")
                        else None,
                        "engine_requirement": engine,
                        "declared_node_version": policy.get("node_version") or None,
                        "peer_check": "requires_solver_review"
                        if release.get("peerDependencies")
                        else "no_declared_peers_in_metadata",
                        "verification": "pending",
                        "other_advisories_check": "pending_target_query",
                        "additional_advisory_ids": [],
                        "evidence": [reference(result, index, ["version"], target)],
                        "limitations": [
                            "Published release metadata does not prove install, build, test or runtime compatibility.",
                            "Transitive updates may require a parent change or explicit override.",
                        ],
                    }
                )
    finding_map = {finding["id"]: finding for finding in findings}
    for candidate in candidates:
        finding = finding_map[candidate["finding_id"]]
        for _, result in sorted(results.items()):
            if (
                result.get("capability") != "advisories.lookup"
                or result.get("completeness") != "complete_for_query"
            ):
                continue
            for index, record in enumerate(result.get("records", [])):
                if (
                    record["package"] == candidate["package"]
                    and record["version"] == candidate["target"]
                ):
                    other = sorted(
                        set(record["advisory_ids"]) - {finding["advisory_id"], *finding["aliases"]}
                    )
                    candidate["additional_advisory_ids"] = other
                    candidate["other_advisories_check"] = (
                        "additional_advisories_reported"
                        if other
                        else "no_additional_matches_in_captured_query"
                    )
                    candidate["evidence"].append(
                        reference(result, index, ["advisory_ids"], record["advisory_ids"])
                    )
                    break
    return {
        "findings": findings,
        "conflicts": conflicts,
        "candidates": sorted(candidates, key=lambda c: c["id"]),
    }


def validate_narrative(value, findings):
    ids = {finding["id"] for finding in findings}
    if any(not set(task.finding_ids).issubset(ids) for task in value.tasks):
        raise ValueError("Unknown finding reference")
    text = " ".join(
        [value.summary, *[task.reason + " " + task.verification for task in value.tasks]]
    )
    if re.search(
        r"\b(guaranteed secure|fully secure|safe to deploy|no vulnerabilities|exploitability confirmed|tests passed|compatible upgrade)\b",
        text,
        re.IGNORECASE,
    ):
        raise ValueError("Unsupported security/compatibility guarantee")


def validate_references(payload, snapshots):
    for item in [*payload.get("findings", []), *payload.get("candidates", [])]:
        for ref in item.get("evidence", []):
            if ref["snapshot_id"] not in snapshots:
                raise ValueError("Unknown evidence snapshot")
            current = snapshots[ref["snapshot_id"]]
            for part in ref["path"]:
                current = current[part]
            if current != ref["value"]:
                raise ValueError("Evidence value mismatch")
