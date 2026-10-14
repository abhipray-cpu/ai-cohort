"""Live two-turn RAG chat acceptance against the running local API and Codex worker."""

import argparse
import base64
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from dev_stack import environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    parts = urlsplit(args.url)
    if parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit("Credentials may only be sent to loopback HTTP")
    config = environment()
    username = config.get("RESOLVEDESK_USERNAME") or config.get("TENDERLENS_USERNAME")
    password = config.get("RESOLVEDESK_PASSWORD") or config.get("TENDERLENS_PASSWORD")
    if not username or not password:
        raise SystemExit("Configure local credentials first")
    token = base64.b64encode(f"{username}:{password}".encode()).decode()

    def request(path, method="GET", body=None, key=None):
        req = Request(
            args.url + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": "Basic " + token,
                "Content-Type": "application/json",
                **({"Idempotency-Key": key} if key else {}),
            },
        )
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read())

    chat = request(
        "/v1/chats",
        "POST",
        {"title": "Live RAG chat acceptance", "server_version": "17", "client_version": "16"},
    )
    report = {"chat_id": chat["id"], "captured_at": datetime.now(UTC).isoformat(), "turns": []}
    folder = Path("var/resolvedesk-evaluation/reports")
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-chat.json")
    try:
        for number, content in enumerate(
            (
                "Can my pg_dump 16 client back up my PostgreSQL 17 server? Explain the version compatibility rule.",
                "Does that same rule also apply to PostgreSQL 16? Cite the version 16 documentation.",
            )
        ):
            started = time.monotonic()
            key = str(uuid.uuid4())
            body = {"content": content, "expected_turn_count": number}
            chat = request(f"/v1/chats/{chat['id']}/messages", "POST", body, key)
            duplicate = request(f"/v1/chats/{chat['id']}/messages", "POST", body, key)
            assert duplicate["turns"][-1]["id"] == chat["turns"][-1]["id"]
            while chat["turns"][-1]["run"]["status"] in ("queued", "running"):
                if time.monotonic() - started > 660:
                    raise AssertionError("Chat run exceeded acceptance deadline")
                time.sleep(2)
                chat = request(f"/v1/chats/{chat['id']}")
            run = chat["turns"][-1]["run"]
            report["turns"].append(
                {
                    "message": content,
                    "elapsed_seconds": round(time.monotonic() - started, 1),
                    "run": run,
                }
            )
            assert run["status"] == "draft", (
                f"Expected grounded answer, received {run['status']}: {run['error']}"
            )
            assert run["answer"]["draft"]["claims"], "No answer claims"
            mapping = {p["id"]: p for p in run["answer"]["evidence"]}
            for claim in run["answer"]["draft"]["claims"]:
                assert claim["citations"]
                for citation in claim["citations"]:
                    passage = mapping[citation["passage_id"]]
                    assert " ".join(citation["quote"].split()) in " ".join(passage["text"].split())
                    if number == 1:
                        assert passage["version"] == "16", (
                            "Follow-up did not retrieve version 16 evidence"
                        )
            assert any(e["stage"] == "conversation_context" for e in run["events"])
            print(
                json.dumps(
                    {
                        "turn": number + 1,
                        "status": run["status"],
                        "elapsed_seconds": report["turns"][-1]["elapsed_seconds"],
                        "claims": len(run["answer"]["draft"]["claims"]),
                    }
                ),
                flush=True,
            )
        reloaded = request(f"/v1/chats/{chat['id']}")
        assert reloaded["turns"][0]["run"]["answer"] == report["turns"][0]["run"]["answer"], (
            "First answer changed after follow-up"
        )
        report["result"] = "passed"
    except Exception as error:
        report["result"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {"report": str(destination), "chat_id": chat["id"], "result": report["result"]}
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
