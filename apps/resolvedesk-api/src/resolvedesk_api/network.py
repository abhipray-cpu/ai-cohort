"""Bounded search and HTTPS fetch with an exact source allowlist and pinned DNS."""

import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit

from contracts.resolvedesk import SearchHit


def approved_url(url):
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname != "www.postgresql.org"
            or parts.port not in (None, 443)
            or parts.username
            or parts.password
            or not re.match(r"^/docs/(16|17)/[a-zA-Z0-9_.-]+(?:\.html)?$", parts.path)
            or parts.query
            or "\\" in url
        ):
            raise ValueError("Source must be a versioned official PostgreSQL documentation page")
    except (ValueError, TypeError) as error:
        raise ValueError(
            "Source must be a versioned official PostgreSQL documentation page"
        ) from error
    return parts._replace(fragment="").geturl()


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("Source resolved to a non-public destination")
        # Resolve once, connect to that exact address, keep hostname TLS verification.
        self.sock = socket.create_connection((addresses[0][4][0], self.port), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def request(host, path, *, headers=None, timeout=15, max_bytes=2_000_000):
    connection = PinnedHTTPSConnection(host, timeout=timeout, context=ssl.create_default_context())
    try:
        connection.request(
            "GET",
            path,
            headers={"User-Agent": "ResolveDesk/0.1 evidence-fetcher", **(headers or {})},
        )
        response = connection.getresponse()
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Source exceeded response size limit")
        return response.status, dict(response.getheaders()), data
    finally:
        connection.close()


def fetch_page(url):
    for _ in range(4):
        url = approved_url(url)
        parts = urlsplit(url)
        status, headers, data = request(parts.hostname, parts.path)
        headers = {k.lower(): v for k, v in headers.items()}
        if status in (301, 302, 303, 307, 308):
            url = urljoin(url, headers.get("location", ""))
            continue
        if status != 200:
            raise RuntimeError(f"Official source returned HTTP {status}")
        if "text/html" not in headers.get("content-type", ""):
            raise ValueError("Official source must be HTML")
        return data.decode("utf-8", errors="strict")
    raise ValueError("Source exceeded redirect limit")


PUBLIC_TERMS = {
    "pg_dump",
    "pg_restore",
    "pg_dumpall",
    "pg_upgrade",
    "psql",
    "backup",
    "restore",
    "version",
    "mismatch",
    "unsupported",
    "archive",
    "header",
    "connection",
    "connect",
    "authentication",
    "password",
    "failed",
    "refused",
    "timeout",
    "ssl",
    "tls",
    "upgrade",
    "replication",
    "permission",
    "role",
    "database",
    "server",
    "client",
    "format",
    "peer",
    "scram",
    "certificate",
    "hba",
    "pg_hba",
    "minor",
    "major",
    "logical",
    "physical",
    "error",
}


def public_query(question, version):
    # Fixed vocabulary only: no open-ended strings, domains, IDs or ticket quoting.
    sanitized = re.sub(
        r"\b\S*(?:password|token|secret|postgresql://|postgres://)\S*",
        " ",
        question,
        flags=re.IGNORECASE,
    )
    tokens = re.findall(r"\b[a-z_]+\b", sanitized.lower())
    chosen = list(dict.fromkeys(t for t in tokens if t in PUBLIC_TERMS and t != "password"))[:12]
    version = version.split(".")[0] if version and version.split(".")[0] in ("16", "17") else "17"
    return f"site:www.postgresql.org/docs/{version}/ PostgreSQL {version} " + " ".join(chosen)


class BraveSearch:
    def __init__(self, key=None):
        self.key = key if key is not None else os.getenv("BRAVE_SEARCH_API_KEY", "")
        self.configured = bool(self.key)

    def search(self, query):
        if not self.configured:
            raise RuntimeError("Official-source search is not configured")
        path = "/res/v1/web/search?" + urlencode({"q": query, "count": 5})
        status, _, data = request(
            "api.search.brave.com",
            path,
            headers={"Accept": "application/json", "X-Subscription-Token": self.key},
            max_bytes=500_000,
        )
        if status != 200:
            raise RuntimeError(f"Search provider returned HTTP {status}")
        payload = json.loads(data)
        results = payload.get("web", {}).get("results", [])
        if not isinstance(results, list):
            raise TypeError("Invalid search tool result")
        hits = []
        for raw in results[:5]:
            hit = SearchHit(
                url=raw["url"],
                title=raw.get("title", "")[:500],
                snippet=raw.get("description", "")[:4000],
            )
            try:
                approved_url(hit.url)
            except ValueError:
                continue
            hits.append(hit.model_dump())
        return hits


class SearchPageParser(HTMLParser):
    def __init__(self, version):
        super().__init__(convert_charrefs=True)
        self.version = version
        self.hits = {}
        self.url = None
        self.title = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            try:
                url = approved_url(dict(attrs).get("href", ""))
                self.url = url if f"/docs/{self.version}/" in url else None
            except ValueError:
                self.url = None
            self.title = []

    def handle_data(self, text):
        if self.url:
            self.title.append(text)

    def handle_endtag(self, tag):
        if tag == "a" and self.url:
            self.hits.setdefault(
                self.url,
                {"url": self.url, "title": "".join(self.title).strip()[:500], "snippet": ""},
            )
            self.url = None


class PostgresSearch:
    """Remote PostgreSQL site search, scoped with its documented form's u parameter."""

    configured = True

    def search(self, query):
        match = re.search(r"site:www\.postgresql\.org/docs/(16|17)/", query)
        if not match:
            raise ValueError("Official search requires a version-scoped sanitized query")
        version = match.group(1)
        terms = [t for t in query.split() if t in PUBLIC_TERMS]
        utility = next((t for t in terms if t.startswith("pg_") or t == "psql"), None)
        utility_pages = {
            "pg_dump": "app-pgdump.html",
            "pg_restore": "app-pgrestore.html",
            "pg_dumpall": "app-pg-dumpall.html",
            "pg_upgrade": "pgupgrade.html",
            "pg_hba": "auth-pg-hba-conf.html",
            "psql": "app-psql.html",
        }
        target_page = utility_pages.get(utility)
        focus = next(
            (
                t
                for t in ("version", "authentication", "connection", "archive", "upgrade")
                if t in terms
            ),
            None,
        )
        # The official search index treats the literal configuration filename
        # differently from its stem: pg_hba alone can miss the reference page.
        search_topic = "pg_hba.conf" if utility == "pg_hba" else utility
        phrases = (
            [" ".join(t for t in (search_topic, focus) if t)] if utility else [" ".join(terms[:3])]
        )
        if utility and focus:
            phrases.append(search_topic)
        hits = {}
        for phrase in phrases[:2]:
            if not phrase:
                continue
            path = "/search/?" + urlencode({"q": phrase, "u": f"/docs/{version}/"})
            status, headers, data = request("www.postgresql.org", path, max_bytes=500_000)
            if status != 200:
                raise RuntimeError(f"Official site search returned HTTP {status}")
            if "text/html" not in {k.lower(): v for k, v in headers.items()}.get(
                "content-type", ""
            ):
                raise ValueError("Official search returned an invalid content type")
            parser = SearchPageParser(version)
            parser.feed(data.decode("utf-8"))
            hits.update(parser.hits)
            # A broad query can return only release notes. Try the bounded topic-only
            # query unless the expected reference page was actually discovered.
            if hits and (
                not target_page
                or any(urlsplit(url).path.endswith("/" + target_page) for url in hits)
            ):
                break
        ranked = sorted(
            hits.values(),
            key=lambda hit: (
                0 if target_page and urlsplit(hit["url"]).path.endswith("/" + target_page) else 1
            ),
        )
        return [SearchHit.model_validate(hit).model_dump() for hit in ranked[:5]]


def make_search():
    provider = os.getenv("RESOLVEDESK_SEARCH_PROVIDER", "postgresql")
    if provider == "postgresql":
        return PostgresSearch()
    if provider == "brave":
        return BraveSearch()
    if provider == "disabled":
        return BraveSearch(key="")
    raise ValueError("Unknown ResolveDesk search provider")
