"""Bounded HTTPS adapters. Endpoint builders are trusted; source/model URLs never dispatch."""

import base64
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import threading
import time
from urllib.parse import quote, urlsplit

from contracts.patchdesk import ToolResult

from patchdesk_api.common import digest, now
from patchdesk_api.inventory import NAME

HOSTS = {
    "api.osv.dev",
    "registry.npmjs.org",
    "api.github.com",
    "raw.githubusercontent.com",
    "api.first.org",
    "www.cisa.gov",
    "api.deps.dev",
}
GHSA = re.compile(r"^GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$")
CVE = re.compile(r"^CVE-\d{4}-\d{4,}$")


class Transport:
    def __init__(self, reserve=lambda *_: None, deadline=None):
        self.reserve = reserve
        self.deadline = deadline or time.monotonic() + 900
        self.lock = threading.Lock()
        self.bytes = 0

    def request(self, url, data=None, headers=None, retry=True):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in HOSTS
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.fragment
        ):
            raise ValueError("URL outside approved HTTPS hosts")
        payload = json.dumps(data).encode() if data is not None else None
        for attempt in range(2 if retry else 1):
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Source deadline")
            self.reserve("http_attempts", 1)
            # Resolve once and pin the actual TLS socket to a public address; SNI keeps hostname verification.
            addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(
                not ipaddress.ip_address(row[4][0]).is_global for row in addresses
            ):
                raise ValueError("Non-public source destination")
            destination = addresses[0][4][0]
            timeout = min(20, remaining)
            connection = http.client.HTTPSConnection(parsed.hostname, timeout=timeout)
            connection.sock = ssl.create_default_context().wrap_socket(
                socket.create_connection((destination, 443), timeout=timeout),
                server_hostname=parsed.hostname,
            )
            try:
                request_headers = {
                    "User-Agent": "PatchDesk/0.1",
                    "Accept": "application/json",
                    **(headers or {}),
                }
                if payload is not None:
                    request_headers["Content-Type"] = "application/json"
                connection.request(
                    "POST" if data is not None else "GET",
                    parsed.path + ("?" + parsed.query if parsed.query else ""),
                    body=payload,
                    headers=request_headers,
                )
                response = connection.getresponse()
                raw = response.read(4 * 1024**2 + 1)
                self.reserve("acquired_bytes", len(raw))
                with self.lock:
                    self.bytes += len(raw)
                    if len(raw) > 4 * 1024**2 or self.bytes > 64 * 1024**2:
                        raise ValueError("Source response byte allowance exceeded")
                if retry and response.status in (429, 500, 502, 503, 504) and attempt == 0:
                    try:
                        delay = min(2, max(0, float(response.getheader("Retry-After", "0.2"))))
                    except ValueError:
                        delay = 0.2
                    if time.monotonic() + delay >= self.deadline:
                        raise TimeoutError("Retry deadline")
                    time.sleep(delay)
                    continue
                if response.status != 200 and response.status != 201:
                    raise OSError(f"Upstream HTTP {response.status}")
                return json.loads(raw)
            finally:
                connection.close()
        raise OSError("Read retries exhausted")


def make_result(
    adapter,
    capability,
    records,
    raw,
    *,
    completeness="complete_for_query",
    outcome=None,
    error=None,
):
    if outcome is None:
        empty = (
            not records
            or capability == "advisories.lookup"
            and not any(r.get("advisory_ids") for r in records)
        )
        outcome = (
            "partial"
            if completeness != "complete_for_query"
            else "no_matches"
            if empty
            else "success"
        )
    return ToolResult(
        adapter=adapter,
        capability=capability,
        records=records,
        raw=raw,
        retrieved_at=now(),
        sha256=digest(raw),
        completeness=completeness,
        outcome=outcome,
        error=error,
    ).model_dump()


class Sources:
    def __init__(self, request=None, transport=None):
        self.transport = transport or Transport()
        self.request = request or self.transport.request

    def execute(self, adapter, request):
        cap, args = request.capability, request.arguments
        try:
            if adapter == "osv" and cap == "advisories.lookup":
                return self.lookup(args["packages"])
            if cap == "advisories.detail":
                aid = args["id"]
                if not GHSA.fullmatch(aid):
                    raise ValueError("Unsupported advisory ID")
                if adapter == "osv":
                    raw = self.request(f"https://api.osv.dev/v1/vulns/{aid}")
                    if raw.get("id") != aid:
                        raise ValueError("Advisory identity mismatch")
                elif adapter == "github_advisory":
                    raw = self.request(f"https://api.github.com/advisories/{aid}")
                    if raw.get("ghsa_id") != aid:
                        raise ValueError("Advisory identity mismatch")
                elif adapter == "github_publisher":
                    repo = {"axios": "axios/axios"}.get(args["package"])
                    if not repo:
                        raise ValueError("Publisher mapping unavailable")
                    raw = self.request(
                        f"https://api.github.com/repos/{repo}/security-advisories/{aid}"
                    )
                    if raw.get("ghsa_id") != aid:
                        raise ValueError("Publisher advisory identity mismatch")
                else:
                    raise ValueError("Capability provider mismatch")
                return make_result(adapter, cap, [raw], raw)
            if adapter == "npm" and cap == "releases.lookup":
                name, version = args["package"], args["version"]
                if not NAME.fullmatch(name) or not re.fullmatch(r"[0-9A-Za-z.+-]{1,80}", version):
                    raise ValueError("Invalid release identity")
                raw = self.request(
                    f"https://registry.npmjs.org/{quote(name, safe='')}/{quote(version, safe='')}"
                )
                if raw.get("name") != name or raw.get("version") != version:
                    raise ValueError("Release identity mismatch")
                selected = {
                    k: raw[k]
                    for k in (
                        "name",
                        "version",
                        "engines",
                        "peerDependencies",
                        "deprecated",
                        "dependencies",
                        "dist",
                    )
                    if k in raw
                }
                return make_result(adapter, cap, [selected], raw)
            if adapter == "epss" and cap == "threat.epss":
                cve = args["cve"]
                if not CVE.fullmatch(cve):
                    raise ValueError("Invalid CVE")
                raw = self.request(f"https://api.first.org/data/v1/epss?cve={cve}")
                if raw.get("status") != "OK" or any(
                    row.get("cve") != cve for row in raw.get("data", [])
                ):
                    raise ValueError("EPSS identity/schema mismatch")
                return make_result(adapter, cap, raw.get("data", []), raw)
            if adapter == "kev" and cap == "threat.kev":
                cve = args["cve"]
                if not CVE.fullmatch(cve):
                    raise ValueError("Invalid CVE")
                raw = self.request(
                    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
                )
                return make_result(
                    adapter, cap, [r for r in raw["vulnerabilities"] if r["cveID"] == cve], raw
                )
            if adapter == "depsdev" and cap == "dependency.context":
                name, version = args["package"], args["version"]
                if not NAME.fullmatch(name) or not re.fullmatch(r"[0-9A-Za-z.+-]{1,80}", version):
                    raise ValueError("Invalid dependency metadata identity")
                raw = self.request(
                    f"https://api.deps.dev/v3/systems/NPM/packages/{quote(name, safe='')}/versions/{quote(version, safe='')}:dependencies"
                )
                return make_result(
                    adapter,
                    cap,
                    [{"context_only": True, "node_count": len(raw.get("nodes", []))}],
                    raw,
                )
            raise ValueError("Unsupported capability/provider")
        except (OSError, ValueError, TypeError, KeyError, TimeoutError) as error:
            return make_result(
                adapter,
                cap,
                [],
                None,
                completeness="unknown",
                outcome="unavailable",
                error=type(error).__name__,
            )

    def lookup(self, packages):
        if (
            not packages
            or len(packages) > 2000
            or any(
                not NAME.fullmatch(p["name"])
                or not re.fullmatch(r"[0-9A-Za-z.+-]{1,80}", p["version"])
                for p in packages
            )
        ):
            raise ValueError("Invalid bounded package identities")
        raw_pages, records, complete = [], [], True
        for start in range(0, len(packages), 200):
            group = packages[start : start + 200]
            pending = [
                (i, {"package": {"name": p["name"], "ecosystem": "npm"}, "version": p["version"]})
                for i, p in enumerate(group)
            ]
            found = {i: set() for i in range(len(group))}
            for _ in range(10):
                raw = self.request(
                    "https://api.osv.dev/v1/querybatch",
                    data={"queries": [query for _, query in pending]},
                )
                raw_pages.append(raw)
                if not isinstance(raw.get("results"), list) or len(raw["results"]) != len(pending):
                    raise ValueError("Batch result correspondence mismatch")
                following = []
                for (i, query), response in zip(pending, raw["results"], strict=True):
                    for vuln in response.get("vulns", []):
                        if GHSA.fullmatch(vuln["id"]):
                            found[i].add(vuln["id"])
                        else:
                            complete = False
                    if response.get("next_page_token"):
                        following.append((i, {**query, "page_token": response["next_page_token"]}))
                pending = following
                if not pending:
                    break
            if pending:
                complete = False
            records.extend(
                {"package": p["name"], "version": p["version"], "advisory_ids": sorted(found[i])}
                for i, p in enumerate(group)
            )
        return make_result(
            "osv",
            "advisories.lookup",
            records,
            raw_pages,
            completeness="complete_for_query" if complete else "truncated",
        )

    def repository(self, policy, ref):
        repo = policy["repository"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not policy.get(
            "repository_id"
        ):
            raise ValueError("Exact repository identity must be configured")
        headers = {}
        if token := os.getenv("PATCHDESK_GITHUB_READ_TOKEN"):
            headers["Authorization"] = "Bearer " + token
        info = self.request(f"https://api.github.com/repos/{repo}", headers=headers)
        if info.get("id") != policy["repository_id"]:
            raise ValueError("Configured repository identity changed")
        commit = self.request(
            f"https://api.github.com/repos/{repo}/commits/{quote(ref, safe='')}", headers=headers
        )["sha"]
        if not re.fullmatch(r"[a-f0-9]{40}", commit):
            raise ValueError("Invalid commit")
        values = {}
        for path in ("package.json", "package-lock.json"):
            raw = self.request(
                f"https://api.github.com/repos/{repo}/contents/{path}?ref={commit}", headers=headers
            )
            if raw.get("encoding") != "base64" or raw.get("size", 0) > 10 * 1024**2:
                raise ValueError("Unsupported repository file")
            values[path] = json.loads(base64.b64decode(raw["content"]))
        return {
            "manifest": values["package.json"],
            "lockfile": values["package-lock.json"],
            "origin": repo,
            "commit": commit,
        }
