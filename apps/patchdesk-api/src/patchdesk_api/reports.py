"""Text-only reviewed maintenance packs; source gaps always survive export."""

import json


def markdown(report):
    value = report["payload"]
    lines = [
        "# PatchDesk maintenance pack",
        "",
        f"Status: {value['status']}",
        f"Report: {report['id']} / revision {report['revision']}",
        "",
        value["narrative"]["summary"],
        "",
        "## Recorded findings",
        "",
    ]
    for item in value["findings"]:
        lines += [
            f"- {item['package']} {item['version']} at {item['location']}: {item['advisory_id']} — {item['status']}. {item['claim']}"
        ]
        for ref in item["evidence"]:
            lines.append(
                f"  - Snapshot {ref['snapshot_id']}, path {json.dumps(ref['path'])}: {json.dumps(ref['value'], ensure_ascii=False)}"
            )
    lines += ["", "## Maintenance tasks", ""]
    lines += [
        f"- [{task['priority']}] {task['title']}. {task['reason']} Verification: {task['verification']}"
        for task in value["narrative"]["tasks"]
    ]
    lines += ["", "## Candidates — verification pending", ""]
    lines += [
        f"- {c['package']} → {c['target']}; advisory check={c['advisory_check']}; engine={c['engine_check']}; other advisories={c['other_advisories_check']}; verification={c['verification']}"
        for c in value["candidates"]
    ]
    lines += ["", "## Coverage and limitations", ""]
    lines += [f"- {key}: {json.dumps(check)}" for key, check in value["coverage"].items()]
    lines += [f"- {gap}" for gap in value.get("gaps", []) + value["narrative"]["limitations"]]
    lines += [
        "",
        "## Conflicts",
        "",
        *[f"- {item['category']}: {item['reason']}" for item in value["conflicts"]],
        "",
        "## Source manifest",
        "",
    ]
    lines += [
        f"- {entry.get('adapter')}, {entry.get('retrieved_at')}; SHA-256 {entry.get('sha256')}; snapshot {entry.get('snapshot_id')}"
        for entry in value.get("source_manifest", [])
    ]
    lines += [
        "",
        f"Stop reason: {value.get('stop_reason', 'not recorded')}",
        f"Reviewed by: {report.get('reviewed_by') or 'not reviewed'}",
        f"Notes: {report.get('notes', '')}",
        "",
        "This pack is not proof of reachability, compatible upgrades, successful tests, deployment or general application security.",
    ]
    return "\n".join(lines)
