"""GitHub-only API adapter. Never follow event-provided URLs or execute logs."""

import io
import os
import re
import time
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx
from contracts.buildrelay import RunEvent

from .workflow import Failure, redact

MAX_EVIDENCE_CHARS = 64000


def parse_webhook(kind, payload):
    if kind != "workflow_run" or payload.get("action") != "completed":
        return None
    try:
        r, repo = payload["workflow_run"], payload["repository"]
        if r["status"] != "completed":
            return None
        return RunEvent(
            repository_id=repo["id"],
            repository=repo["full_name"],
            run_id=r["id"],
            attempt=r["run_attempt"],
            conclusion=r["conclusion"],
            workflow=r["name"],
            branch=r.get("head_branch") or "",
            sha=r["head_sha"],
            source_url=r["html_url"],
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("invalid workflow event") from exc


def select_archive(archive, source, secrets=()):
    """Pure production selector, shared with corpus evaluation; never uses gold labels."""
    files, truncated = [], False
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            members = z.infolist()
            if len(members) > 2000 or sum(m.file_size for m in members) > 40_000_000:
                raise Failure("log_expansion_limit")
            for m in sorted(members, key=lambda m: m.filename):
                p = PurePosixPath(m.filename)
                if m.is_dir():
                    continue
                if p.is_absolute() or ".." in p.parts or "\\" in m.filename:
                    truncated = True
                    continue
                if m.file_size > 4_000_000:
                    truncated = True
                    continue
                text = redact(z.read(m).decode("utf-8", errors="replace"), secrets)
                files.append((redact(m.filename, secrets), text))
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise Failure("invalid_log_archive") from exc
    complete = "\n".join(f"FILE: {name}\n{text}\n" for name, text in files)
    spans = []
    if len(complete) <= MAX_EVIDENCE_CHARS:
        selected = complete
    else:
        truncated = True
        # Generic diagnostics, never corpus labels or repository-specific keywords.
        signal = re.compile(
            r"\b(?:error|fatal|failed|failure|fail|cannot|undefined|unsatisfied|timeout|panic)\b|\w+Exception\b|\w*Assertion\w*|could not|not found|timed out|segmentation",
            re.IGNORECASE,
        )
        benign = re.compile(r"\b(?:0|no) (?:errors?|failures?)\b", re.IGNORECASE)
        candidates = []
        lines_by_file = []
        for index, (_, text) in enumerate(files):
            lines = text.splitlines()
            lines_by_file.append(lines)
            hits = [
                n for n, line in enumerate(lines) if signal.search(line) and not benign.search(line)
            ]
            # The initiating failure may precede cascades and long cleanup. Keep
            # an early diagnostic cluster as well as the terminal slice.
            if hits:
                n = hits[0]
                candidates.append((6, index, max(0, n - 12), min(len(lines), n + 28)))
            # Preserve terminal summaries/diffs even without English error keywords.
            tail_start, tail_chars = len(lines), 0
            while tail_start and tail_chars + len(lines[tail_start - 1]) + 1 <= 28000:
                tail_start -= 1
                tail_chars += len(lines[tail_start]) + 1
            candidates.append((5 if hits else 2, index, tail_start, len(lines)))
            # Recent diagnostics outrank setup chatter; cap candidates, not initial hits.
            for n in reversed(hits[-256:]):
                candidates.append((4, index, max(0, n - 10), min(len(lines), n + 20)))
            candidates.append((1, index, 0, min(20, len(lines))))
        pieces, used, seen = [], 0, set()
        # Rank across ALL files before spending the budget; alphabetical success
        # logs must not crowd out a later failed job. Deduplicate overlapping lines.
        for _, index, start, end in sorted(candidates, key=lambda c: (-c[0], c[1], -c[2])):
            name = files[index][0]
            fresh = [n for n in range(start, end) if (index, n) not in seen]
            if not fresh:
                continue
            # Split at gaps so each provenance range remains truthful.
            groups = []
            for n in fresh:
                if not groups or n != groups[-1][-1] + 1:
                    groups.append([])
                groups[-1].append(n)
            for group in groups:
                header = f"FILE: {name} (redacted source lines {group[0] + 1}-{group[-1] + 1})\n"
                body = "\n".join(lines_by_file[index][n] for n in group)
                piece = header + body + "\n"
                if used + len(piece) + bool(pieces) > MAX_EVIDENCE_CHARS:
                    continue
                pieces.append(piece)
                used += len(piece) + (len(pieces) > 1)
                seen.update((index, n) for n in group)
                spans.append(
                    {"file": name, "redacted_start": group[0] + 1, "redacted_end": group[-1] + 1}
                )
        selected = "\n".join(pieces)
    return {
        "text": selected,
        "truncated": truncated,
        "source": source,
        "archive_bytes": len(archive),
        "selection": "early diagnostics, terminal summaries, recent diagnostic windows, then heads; <=64000 characters; citation line numbers refer to captured evidence, redacted-source ranges in headers (not raw archive lines)",
        "spans": spans,
    }


class GitHub:
    def __init__(self, client=None):
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(30, connect=5), follow_redirects=False
        )

    def request(self, repo, method, path, **kwargs):
        token = os.environ.get(repo["token_ref"], "")
        if not token:
            raise Failure("github_credentials_missing")
        url = "https://api.github.com" + path
        try:
            response = self.client.request(
                method,
                url,
                headers={
                    "Authorization": "Bearer " + token,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise Failure("github_network", transient=True) from exc
        if response.status_code in {429, 403} and (
            response.status_code == 429
            or "retry-after" in response.headers
            or response.headers.get("x-ratelimit-remaining") == "0"
        ):
            try:
                delay = max(
                    float(response.headers.get("retry-after", 0)),
                    float(response.headers.get("x-ratelimit-reset", 0)) - time.time(),
                )
            except ValueError:
                delay = 60
            raise Failure(
                "github_rate_limited", transient=True, retry_after=max(1, min(delay, 86400))
            )
        if response.status_code >= 500:
            raise Failure("github_unavailable", transient=True)
        if response.status_code in {401, 403}:
            raise Failure("github_permission_denied")
        if response.status_code in {404, 410}:
            raise Failure("github_source_unavailable")
        if response.status_code >= 400:
            raise Failure("github_request_rejected")
        return response

    def json(self, repo, method, path, **kwargs):
        try:
            return self.request(repo, method, path, **kwargs).json()
        except (ValueError, TypeError) as exc:
            raise Failure("github_invalid_response") from exc

    def download(self, url):
        for _ in range(3):
            u = urlparse(url)
            if (
                u.scheme != "https"
                or u.port not in {None, 443}
                or u.username
                or u.password
                or not u.hostname
                or not (
                    u.hostname.endswith(".blob.core.windows.net")
                    or u.hostname.endswith(".githubusercontent.com")
                )
            ):
                raise Failure("unsafe_log_redirect")
            try:
                with self.client.stream(
                    "GET", url, headers={"Accept": "application/zip"}, follow_redirects=False
                ) as r:
                    if r.status_code in {301, 302, 303, 307, 308}:
                        url = r.headers.get("location", "")
                        continue
                    if r.status_code >= 400:
                        raise Failure("log_download_unavailable", transient=r.status_code >= 500)
                    result = bytearray()
                    started = time.monotonic()
                    for chunk in r.iter_bytes():
                        result.extend(chunk)
                        if len(result) > 10_000_000 or time.monotonic() - started > 60:
                            raise Failure("log_download_limit")
                    return bytes(result)
            except httpx.HTTPError as exc:
                raise Failure("log_download_network", transient=True) from exc
        raise Failure("too_many_log_redirects")

    def evidence(self, repo, event):
        base = f"/repos/{repo['name']}/actions/runs/{event.run_id}/attempts/{event.attempt}"
        metadata = self.json(repo, "GET", base)
        if (
            metadata.get("id") != event.run_id
            or metadata.get("run_attempt") != event.attempt
            or metadata.get("repository", {}).get("id") != repo["github_id"]
        ):
            raise Failure("github_run_identity_mismatch")
        response = self.request(repo, "GET", base + "/logs")
        if response.status_code != 302:
            raise Failure("log_redirect_missing")
        archive = self.download(response.headers.get("location", ""))
        secrets = [os.environ.get(repo["token_ref"], ""), os.environ.get(repo["secret_ref"], "")]
        return select_archive(archive, event.source_url, secrets)

    def find_issue(self, repo, marker):
        # Search index lag is unsafe for reconciling an ambiguous POST; enumerate repository issues.
        for page in range(1, 11):
            issues = self.json(
                repo,
                "GET",
                f"/repos/{repo['name']}/issues",
                params={"state": "all", "per_page": 100, "page": page},
            )
            if not isinstance(issues, list):
                raise Failure("github_invalid_issue_list")
            for issue in issues:
                if not issue.get("pull_request") and marker in (issue.get("body") or ""):
                    return issue
            if len(issues) < 100:
                return None
        raise Failure("issue_reconciliation_window_exceeded")

    def create_issue(self, repo, title, body):
        return self.json(
            repo, "POST", f"/repos/{repo['name']}/issues", json={"title": title, "body": body}
        )

    def update_issue(self, repo, number, title, body, state):
        return self.json(
            repo,
            "PATCH",
            f"/repos/{repo['name']}/issues/{int(number)}",
            json={"title": title, "body": body, "state": state},
        )

    def recent_runs(self, repo, page=1):
        return self.json(
            repo,
            "GET",
            f"/repos/{repo['name']}/actions/runs",
            params={"per_page": 100, "page": page},
        )
