"""Canonical signatures and encrypted-at-rest destination credentials."""

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .core import canonical


def public_key(private):
    return base64.b64encode(private.public_key().public_bytes_raw()).decode()


def private_key(encoded):
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(encoded, validate=True))


def signed(body, key):
    if hasattr(body, "model_dump"):
        body = body.model_dump(mode="json")
    return {
        "body": body,
        "signature": base64.b64encode(key.sign(canonical(body).encode())).decode(),
    }


def verify(envelope, public):
    try:
        if set(envelope) != {"body", "signature"}:
            raise ValueError("invalid envelope")
        signature = base64.b64decode(envelope["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public, validate=True)).verify(
            signature, canonical(envelope["body"]).encode()
        )
        return envelope["body"]
    except (InvalidSignature, ValueError, TypeError, KeyError):
        raise ValueError("signature verification failed") from None
