import json


def markdown(output):
    p = output["payload"]
    lines = [
        "# RelayDesk investigation handover",
        "",
        p.get("summary", ""),
        "",
        f"State: {output['state']}; reviewed by: {output['reviewer']}; case revision: {output['case_revision']}",
        "",
        "## Qualified findings",
        "",
    ]
    for claim in p.get("claims", []):
        lines.append("- " + claim["text"] + " — memories: " + ", ".join(claim["memory_ids"]))
        if claim.get("attribution"):
            a = claim["attribution"]
            lines.append(
                f"  Attributed to {a['author']} · {a['state']} · exact source quotation, not independent verification."
            )
        for e in claim.get("citations", []):
            lines.append(
                f"  Supporting source {e['source_id']} revision {e['source_revision']}, span {e['start']}:{e['end']}, SHA-256 {e['sha256']}"
            )
    lines.extend(["", "## Source-linked recall", ""])
    for h in p.get("recall", {}).get("hits", []):
        e = h["evidence"]
        lines.extend(
            [
                f"### {h['kind']} · {h['state']}",
                "",
                h["body"],
                "",
                f"Source {e['source_id']} revision {e['source_revision']}, span {e['start']}:{e['end']}, SHA-256 {e['sha256']}",
                "",
            ]
        )
    lines.extend(
        ["## Limits", ""]
        + ["- " + v for v in [*p.get("limitations", []), *p.get("coverage_gaps", [])]]
    )
    lines.extend(
        [
            "",
            "## Reproducibility and coverage",
            "",
            "```json",
            json.dumps(
                {k: p.get(k) for k in ["context_manifest", "buffer", "prompt_version"]}, indent=2
            ),
            "```",
            "",
            "No independently verified technical resolution, customer commitment or executed remediation is established.",
        ]
    )
    return "\n".join(lines)
