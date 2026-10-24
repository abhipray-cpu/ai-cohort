"""Allowlisted, DNS-pinned official HTTPS reads. No portal credentials or proxies."""

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit

from repairclaim_api.errors import DomainError

HOSTS = frozenset(
    {
        "www.nhtsa.gov",
        "static.nhtsa.gov",
        "api.nhtsa.gov",
        "owners.honda.com",
        "mygarage.honda.com",
        "automobiles.honda.com",
    }
)


def validate_source_url(url):
    try:
        parsed = urlsplit(url)
        if (
            len(url) > 2000
            or parsed.scheme != "https"
            or parsed.hostname not in HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or parsed.fragment
            or any(ord(char) < 33 for char in url)
        ):
            raise ValueError()
    except (ValueError, TypeError) as error:
        raise DomainError("source_url_denied", 422) from error
    return parsed


def _resolve(host):
    return list({entry[4][0] for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})


class PinnedConnection(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=15, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class SourceFetcher:
    def __init__(self, *, resolve=_resolve, request=None, max_bytes=20 * 1024 * 1024):
        self.resolve, self.request, self.max_bytes = resolve, request, max_bytes

    def _request(self, url, address):
        parsed = validate_source_url(url)
        connection = PinnedConnection(parsed.hostname, address)
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            connection.request(
                "GET",
                path,
                headers={"Accept-Encoding": "identity", "User-Agent": "RepairClaim/0.1"},
            )
            response = connection.getresponse()
            body = response.read(self.max_bytes + 1)
            return (
                response.status,
                {key.lower(): value for key, value in response.getheaders()},
                body,
            )
        finally:
            connection.close()

    def fetch(self, url):
        for _ in range(4):
            parsed = validate_source_url(url)
            try:
                addresses = self.resolve(parsed.hostname)
                if not addresses or any(
                    not ipaddress.ip_address(address).is_global
                    or ipaddress.ip_address(address).is_multicast
                    or ipaddress.ip_address(address).is_reserved
                    for address in addresses
                ):
                    raise DomainError("source_address_denied", 422)
                status, headers, body = (self.request or self._request)(url, addresses[0])
            except (OSError, ValueError, http.client.HTTPException) as error:
                raise DomainError("source_unavailable", 503) from error
            if len(body) > self.max_bytes:
                raise DomainError("source_too_large", 413)
            if status in {301, 302, 303, 307, 308}:
                url = urljoin(url, headers.get("location", ""))
                continue
            if status != 200 or headers.get("content-encoding", "identity") != "identity":
                raise DomainError("source_unavailable", 503)
            return {"url": url, "body": body, "sha256": hashlib.sha256(body).hexdigest()}
        raise DomainError("source_redirect_limit", 422)


def classify_change(old_text, new_text):
    return (
        "formatting_only"
        if re.sub(r"\s+", " ", old_text).strip() == re.sub(r"\s+", " ", new_text).strip()
        else "review_required"
    )
