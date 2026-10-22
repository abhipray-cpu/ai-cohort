"""Pinned-address HTTP transport; no proxy inheritance, redirects or raw response logging."""

import http.client
import ipaddress
import socket
import ssl
import threading
from urllib.parse import urlsplit


def resolve_destination(url, *, lab_loopback=False, resolver=None):
    parsed = urlsplit(url)
    if (
        len(url) > 2000
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not parsed.hostname
    ):
        raise ValueError("invalid destination")
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if parsed.scheme != "https" and not (
        lab_loopback and parsed.scheme == "http" and host in {"127.0.0.1", "::1"}
    ):
        raise ValueError("HTTPS required")
    resolver = resolver or (
        lambda h, p: [(r[4][0], p) for r in socket.getaddrinfo(h, p, type=socket.SOCK_STREAM)]
    )
    addresses = resolver(host, port)
    if not addresses or any(
        not ipaddress.ip_address(a).is_global
        and not (
            lab_loopback and ipaddress.ip_address(a).is_loopback and host in {"127.0.0.1", "::1"}
        )
        for a, _ in addresses
    ):
        raise ValueError("destination address denied")
    return parsed, addresses[0][0], port


def request(
    url,
    body=None,
    *,
    headers=None,
    lab_loopback=False,
    method="POST",
    limit=65536,
    timeout_seconds=5,
    deadline_seconds=10,
):
    if not 0 < timeout_seconds <= 3600 or not 0 < deadline_seconds <= 3600:
        raise ValueError("finite request deadline required")
    parsed, address, port = resolve_destination(url, lab_loopback=lab_loopback)

    class Pinned(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.create_connection((address, port), timeout=5)
            if parsed.scheme == "https":
                self.sock = ssl.create_default_context().wrap_socket(
                    self.sock, server_hostname=parsed.hostname
                )
            self.sock.settimeout(timeout_seconds)

    connection = Pinned(parsed.hostname, port, timeout=timeout_seconds)

    # Wall-clock cap after DNS resolution, including a slow-trickling response.
    # Closing the pinned socket interrupts reads without following any redirect.
    def expire():
        sock = connection.sock
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(deadline_seconds, expire)
    timer.daemon = True
    timer.start()
    try:
        connection.request(
            method,
            parsed.path + ("?" + parsed.query if parsed.query else "") or "/",
            body=body,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        response = connection.getresponse()
        content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError("response too large")
        return response.status, content
    except http.client.HTTPException as exc:
        raise OSError("destination protocol unavailable") from exc
    finally:
        timer.cancel()
        connection.close()
