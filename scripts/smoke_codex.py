"""Check the configured local Codex executable and JSON Schema output path."""

from __future__ import annotations

import json
import os
import sys

from agent_core.codex_local import LocalCodexProvider
from contracts.tenderlens import DraftBrief


def main():
    provider = LocalCodexProvider(command=os.getenv("CODEX_COMMAND", "codex"), timeout_seconds=120)
    if "--brief" in sys.argv:
        result = provider.generate(
            prompt=(
                "Extract this source: Document demo, page 1: City Council. Deadline 1 Dec 2026. "
                "Return a draft brief with one verified deadline claim and exact citation."
            ),
            schema=DraftBrief.model_json_schema(),
        )
        print(
            json.dumps(
                {
                    "exit_code": result.exit_code,
                    "elapsed_ms": result.elapsed_ms,
                    "stderr": result.stderr[-300:],
                }
            )
        )
        if result.exit_code != 0:
            raise SystemExit("Codex exited with a nonzero status")
        brief = DraftBrief.model_validate_json(result.text)
        print(json.dumps({"title": brief.title, "claim_count": len(brief.claims)}))
        return
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["document_type", "has_deadline"],
        "properties": {
            "document_type": {"type": "string"},
            "has_deadline": {"type": "boolean"},
        },
    }
    result = provider.generate(
        prompt="Classify this text: 'Request for proposal. Submit by 1 December 2026.' Return only JSON.",
        schema=schema,
    )
    print(
        json.dumps(
            {
                "exit_code": result.exit_code,
                "elapsed_ms": result.elapsed_ms,
                "stderr": result.stderr[-300:],
            }
        )
    )
    if result.exit_code != 0:
        raise SystemExit("Codex exited with a nonzero status")
    value = json.loads(result.text)
    assert isinstance(value["document_type"], str)
    assert value["has_deadline"] is True
    print(json.dumps(value))


if __name__ == "__main__":
    main()
