"""Frozen public real-thread acquisition; quota-bound, checkpointed and never overwriting.

No tokens are discovered. The connector honors only explicitly configured
RELAYDESK_GITHUB_READ_TOKEN. Partial threads are retained as partial, not passes.
"""

import argparse
import json
import shutil
import time
from pathlib import Path
from urllib.parse import quote

from relaydesk_api.common import file_hash, now
from relaydesk_api.ingest import GithubSources, GithubTransport

REPOSITORIES = [
    "microsoft/vscode",
    "microsoft/TypeScript",
    "elastic/elasticsearch",
    "nodejs/node",
    "nodejs/undici",
    "node-red/node-red",
    "postmanlabs/newman",
    "fastify/fastify",
    "expressjs/express",
    "axios/axios",
    "nock/nock",
    "websockets/ws",
    "webpack/webpack",
    "vitejs/vite",
    "rollup/rollup",
    "eslint/eslint",
    "babel/babel",
    "jestjs/jest",
    "jupyterlab/jupyterlab",
    "pandas-dev/pandas",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--previous", default="var/validation/relaydesk-2026-10-16-implementation/raw"
    )
    parser.add_argument("--core-budget", type=int, default=56)
    parser.add_argument("--per-repository", type=int, choices=range(1, 11), default=2)
    parser.add_argument(
        "--issue", help="Explicit verified repository#issue supplement, no discovery"
    )
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    raw = root / "raw"
    raw.mkdir()
    (root / "batches").mkdir()
    report = {
        "started_at": now(),
        "selection": {
            "repositories": REPOSITORIES,
            "short": f"first {args.per_repository} ranked eligible issues/repository with 20..99 comments; discovery candidates, not human-screened technical gold",
            "long": "not acquired by short-thread search; explicit supplements separately frozen",
            "target_threads": 200,
            "target_repositories": 20,
            "target_human_messages": 5000,
            "limit": "public quota and explicit per-run core allowance; no quota bypass",
        },
        "threads": [],
        "failures": [],
        "requests": 0,
    }
    cache, manifest = {}, []
    previous = Path(args.previous)
    for row in json.loads((previous / "manifest.json").read_text()):
        src = previous / row["path"]
        if file_hash(src) != row["sha256"]:
            raise ValueError("Prior capture hash mismatch")
        dest = raw / f"{len(manifest):05}.json"
        shutil.copyfile(src, dest)
        manifest.append({**row, "path": dest.name, "reused_capture": True})
        cache[row["url"]] = json.loads(dest.read_text())
    transport = GithubTransport()
    core_requests = 0

    def checkpoint():
        (raw / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    def request(url):
        nonlocal core_requests
        if url in cache:
            return cache[url]
        if "/search/" not in url:
            if core_requests >= args.core_budget:
                raise OSError("Explicit acquisition core allowance exhausted; checkpoint retained")
            core_requests += 1
        report["requests"] += 1
        value = transport.request(url)
        dest = raw / f"{len(manifest):05}.json"
        dest.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        manifest.append(
            {"url": url, "path": dest.name, "sha256": file_hash(dest), "observed_at": now()}
        )
        cache[url] = value
        checkpoint()
        return value

    selected, known = [], set()
    if args.issue:
        repo, number = args.issue.rsplit("#", 1)
        issue = request(f"https://api.github.com/repos/{repo}/issues/{int(number)}")
        selected.append((repo, issue))
        report["selection"]["explicit_issue"] = args.issue
    # Search has its own quota. Ten two-repository queries, no unbounded retry.
    for index in range(0, 0 if args.issue else len(REPOSITORIES), 2):
        pair = REPOSITORIES[index : index + 2]
        query = "is:issue comments:20..99 " + " ".join("repo:" + r for r in pair)
        try:
            listing = request(
                "https://api.github.com/search/issues?q="
                + quote(query)
                + "&sort=comments&order=desc&per_page=100"
            )
            if listing.get("incomplete_results"):
                report["failures"].append(
                    {
                        "stage": "discovery",
                        "repositories": pair,
                        "reason": "search incomplete_results=true",
                    }
                )
            for repo in pair:
                rows = [
                    i
                    for i in listing["items"]
                    if i["repository_url"].endswith("/repos/" + repo)
                    and i.get("body")
                    and "pull_request" not in i
                ]
                for issue in rows[: args.per_repository]:
                    selected.append((repo, issue))
            if index < len(REPOSITORIES) - 2:
                time.sleep(1)  # Politeness, not a rate-limit bypass.
        except (OSError, ValueError, TimeoutError, KeyError) as error:
            report["failures"].append(
                {"stage": "discovery", "repositories": pair, "reason": str(error)[:240]}
            )
            checkpoint()
            if "403" in str(error) or "429" in str(error):
                break
    # Prior complete threads remain real evidence, not newly acquired unique data.
    for row in [] if args.issue else list(cache):
        parts = row.split("/")
        if (
            row.startswith("https://api.github.com/repos/")
            and "/issues/" in row
            and "?" not in row
            and not row.endswith("comments")
        ):
            issue = cache[row]
            if isinstance(issue, dict) and "number" in issue and "pull_request" not in issue:
                selected.append(("/".join(parts[4:6]), issue))
    # Round-robin repository order keeps the final quota-bound cohort broad.
    by_repo = {}
    for repo, issue in selected:
        key = (repo, issue["number"])
        if key not in known:
            known.add(key)
            by_repo.setdefault(repo, []).append(issue)
    ordered = []
    for position in range(max((len(v) for v in by_repo.values()), default=0)):
        ordered.extend(
            (repo, values[position]) for repo, values in by_repo.items() if position < len(values)
        )
    for repo, issue in ordered:
        try:
            batch = GithubSources(request=request).fetch(repo, issue["number"], issue_payload=issue)
            name = repo.replace("/", "--") + "--" + str(issue["number"]) + ".json"
            path = root / "batches" / name
            path.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
            report["threads"].append(
                {
                    "repository": repo,
                    "issue": issue["number"],
                    "batch": name,
                    "sha256": file_hash(path),
                    "messages": len(batch.messages),
                    "human_messages": sum(not m.bot for m in batch.messages),
                    "complete": batch.complete,
                    "gaps": batch.gaps,
                    "observed_comment_count": issue.get("comments"),
                }
            )
        except (OSError, ValueError, TimeoutError, KeyError) as error:
            report["failures"].append(
                {
                    "stage": "thread",
                    "repository": repo,
                    "issue": issue["number"],
                    "reason": str(error)[:240],
                }
            )
        checkpoint()
    report["finished_at"] = now()
    report["totals"] = {
        "threads": len(report["threads"]),
        "complete_threads": sum(t["complete"] for t in report["threads"]),
        "repositories": len({t["repository"] for t in report["threads"]}),
        "human_messages": sum(t["human_messages"] for t in report["threads"]),
        "core_requests": core_requests,
        "failures": len(report["failures"]),
    }
    checkpoint()
    print(json.dumps(report["totals"], indent=2))


if __name__ == "__main__":
    main()
