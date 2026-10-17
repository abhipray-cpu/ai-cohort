"""Local reviewed internal packet; untrusted source text remains fenced inert text."""

import re


def fenced(text):
    size = max([len(s) for s in re.findall(r"`+", text)] + [2]) + 1
    fence = "`" * size
    return f"{fence}text\n{text}\n{fence}"


def markdown(packet):
    lines = [
        "# ClauseGate internal review packet",
        "",
        "Not legal advice, a signature, or permission to send externally.",
        "",
        f"Document: {packet['document_id']}",
        f"Source hash: {packet['text_hash']}",
        f"Playbook hash: {packet['playbook_hash']}",
        f"Approval binding: {packet['binding']}",
        f"Packet hash: {packet['sha256']}",
        f"Final reviewer: {packet['reviewer']}",
        "",
        "## Findings",
        "",
    ]
    for f in packet["findings"]:
        lines += [
            f"### {f['check_id']} / {f['label']} / {f['assessment']}",
            fenced(f["rationale"]),
            "",
        ]
        for e in f["evidence"]:
            lines += [f"Original span {e['id']} [{e['start']}, {e['end']})", fenced(e["quote"]), ""]
    lines += ["## Decisions", ""]
    for d in packet["decisions"]:
        lines += [f"{d['id']} · {d['actor']} · {d['kind']} · {d['at']}", fenced(d["rationale"]), ""]
    lines += ["## Limitations", "", *["- " + item for item in packet["limitations"]]]
    return "\n".join(lines) + "\n"
