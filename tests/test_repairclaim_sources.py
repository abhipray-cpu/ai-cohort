"""Official-source boundaries exercised with injected transports, never real sources."""

import pytest
from repairclaim_api.errors import DomainError
from repairclaim_api.sources import SourceFetcher, classify_change, validate_source_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x",
        "https://example.com/x",
        "file:///secret",
        "https://static.nhtsa.gov@evil.test/x",
        "https://static.nhtsa.gov:444/x",
    ],
)
def test_unregistered_or_private_source_destinations_are_blocked(url):
    with pytest.raises(DomainError):
        validate_source_url(url)


def test_public_host_resolving_to_private_address_is_blocked():
    fetcher = SourceFetcher(resolve=lambda host: ["127.0.0.1"])
    with pytest.raises(DomainError, match="source_address_denied"):
        fetcher.fetch("https://static.nhtsa.gov/odi/fixture.pdf")


def test_redirects_are_rechecked_and_bytes_are_bounded():
    fetcher = SourceFetcher(
        resolve=lambda host: ["8.8.8.8"],
        request=lambda *args: (302, {"location": "http://169.254.169.254/"}, b""),
    )
    with pytest.raises(DomainError):
        fetcher.fetch("https://static.nhtsa.gov/odi/fixture.pdf")
    fetcher = SourceFetcher(
        resolve=lambda host: ["8.8.8.8"],
        request=lambda *args: (200, {}, b"x" * 1025),
        max_bytes=1024,
    )
    with pytest.raises(DomainError, match="source_too_large"):
        fetcher.fetch("https://static.nhtsa.gov/odi/fixture.pdf")


def test_source_failure_is_not_a_withdrawal_or_fresh_unchanged_capture():
    fetcher = SourceFetcher(resolve=lambda host: ["8.8.8.8"], request=lambda *args: (404, {}, b""))
    with pytest.raises(DomainError, match="source_unavailable"):
        fetcher.fetch("https://static.nhtsa.gov/odi/fixture.pdf")
    assert classify_change("Limit 100000 miles", "Limit\n100000   miles") == "formatting_only"
    assert classify_change("Limit 100000 miles", "Limit 90000 miles") == "review_required"
