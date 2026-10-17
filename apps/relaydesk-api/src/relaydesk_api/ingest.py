"""Bounded GitHub-only read connector; comments are data, never commands/URLs to execute."""

import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import time
from urllib.parse import urlsplit

from contracts.relaydesk import ImportBatch, SourceMessage


class GithubTransport:
    def __init__(self):
        self.deadline = time.monotonic() + 600
        self.bytes = 0
        self.attempts = 0

    def request(self, url):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.github.com"
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("Only trusted GitHub HTTPS endpoints are permitted")
        if time.monotonic() > self.deadline or self.attempts >= 200:
            raise TimeoutError("Source allowance exhausted")
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("Non-public destination")
        connection = http.client.HTTPSConnection(
            parsed.hostname, timeout=min(20, max(0.1, self.deadline - time.monotonic()))
        )
        connection.sock = ssl.create_default_context().wrap_socket(
            socket.create_connection((addresses[0][4][0], 443), timeout=20),
            server_hostname=parsed.hostname,
        )
        headers = {
            "User-Agent": "RelayDesk/0.1 read-only validation",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token := os.getenv("RELAYDESK_GITHUB_READ_TOKEN"):
            headers["Authorization"] = "Bearer " + token
        self.attempts += 1
        try:
            connection.request(
                "GET", parsed.path + ("?" + parsed.query if parsed.query else ""), headers=headers
            )
            response = connection.getresponse()
            body = response.read(4 * 1024**2 + 1)
            self.bytes += len(body)
            if len(body) > 4 * 1024**2 or self.bytes > 64 * 1024**2:
                raise ValueError("Source byte allowance exceeded")
            if response.status != 200:
                raise OSError(
                    f"GitHub HTTP {response.status}; retry only after reviewing quota/permission"
                )
            return json.loads(body)
        finally:
            connection.close()


class GithubSources:
    def __init__(self, request=None, page_size=100):
        self.transport = GithubTransport()
        self.request = request or self.transport.request
        self.page_size = page_size

    def fetch(self, repo, number, issue_payload=None):
        if (
            not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            or not isinstance(number, int)
            or number < 1
        ):
            raise ValueError("Invalid repository/issue identity")
        metadata = self.request(f"https://api.github.com/repos/{repo}")
        if metadata.get("full_name", "").lower() != repo.lower():
            raise ValueError("Repository identity mismatch")
        issue = issue_payload or self.request(
            f"https://api.github.com/repos/{repo}/issues/{number}"
        )
        if issue.get("number") != number or "pull_request" in issue:
            raise ValueError("Expected exact issue, not a pull request")
        messages = []
        gaps = []
        rows = [issue]
        seen = set()
        for page in range(1, 22):
            try:
                values = self.request(
                    f"https://api.github.com/repos/{repo}/issues/{number}/comments?per_page={self.page_size}&page={page}"
                )
            except (OSError, ValueError, TimeoutError) as error:
                gaps.append(type(error).__name__ + ": comment acquisition unavailable")
                break
            if not isinstance(values, list):
                raise ValueError("Unexpected comment schema")  # noqa: TRY004 — upstream contract error
            for value in values:
                if value["id"] in seen:
                    raise ValueError("Duplicate paged comment identity")
                seen.add(value["id"])
                rows.append(value)
            if len(values) < self.page_size:
                break
        else:
            gaps.append("Comment page allowance reached")
        if len(seen) != issue.get("comments", len(seen)):
            gaps.append(
                "Issue comment counter differs from acquired records; capture may be concurrent/partial"
            )
        for i, row in enumerate(rows[:2000]):
            body = row.get("body")
            if not body:
                gaps.append("Empty/deleted body excluded")
                continue
            if len(body.encode("utf-8")) > 32768:
                gaps.append("Oversized body excluded, not truncated")
                continue
            user = row.get("user") or {}
            messages.append(
                SourceMessage(
                    source_key=f"github:{metadata['id']}:{issue['id']}:{'issue' if i == 0 else 'comment'}:{row['id']}",
                    author=user.get("login", "unknown"),
                    body=body,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    bot=user.get("type") == "Bot" or user.get("login", "").endswith("[bot]"),
                )
            )
        if len(rows) > 2000:
            gaps.append("Case message allowance reached")
        if not messages:
            raise ValueError("No usable source messages")
        return ImportBatch(
            messages=messages,
            origin=f"github:{repo}#{number}; repository_id={metadata['id']}",
            complete=not gaps,
            gaps=gaps,
        )
