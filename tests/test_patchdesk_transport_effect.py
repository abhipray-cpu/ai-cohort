import pytest
from patchdesk_api.adapters import Transport


def test_effect_transport_never_retries_ambiguous_post(monkeypatch):
    count = 0

    class Response:
        status = 503

        def read(self, _):
            return b"{}"

        def getheader(self, *_):
            return "0"

    class Connection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, *_args, **_kwargs):
            nonlocal count
            count += 1

        def getresponse(self):
            return Response()

        def close(self):
            pass

    class TLS:
        def wrap_socket(self, sock, **_):
            return sock

    monkeypatch.setattr(
        "patchdesk_api.adapters.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        "patchdesk_api.adapters.socket.create_connection", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr("patchdesk_api.adapters.ssl.create_default_context", lambda: TLS())
    monkeypatch.setattr("patchdesk_api.adapters.http.client.HTTPSConnection", Connection)
    with pytest.raises(OSError):
        Transport().request(
            "https://api.github.com/repos/owned/test/issues",
            data={"title": "Approved"},
            retry=False,
        )
    assert count == 1
    count = 0
    with pytest.raises(OSError):
        Transport().request("https://api.osv.dev/v1/querybatch", data={"queries": []})
    assert count == 2
