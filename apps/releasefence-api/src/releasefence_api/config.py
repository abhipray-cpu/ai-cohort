import os

from .crypto import private_key
from .store import Store


def load_store():
    required = (
        "RELEASEFENCE_DATABASE_URL",
        "RELEASEFENCE_ENCRYPTION_KEY",
        "RELEASEFENCE_SIGNING_KEY",
    )
    if any(not os.environ.get(k) for k in required):
        raise RuntimeError("explicit ReleaseFence database and key configuration required")
    return Store(
        os.environ[required[0]],
        os.environ[required[1]].encode(),
        private_key(os.environ[required[2]]),
        schema=os.environ.get("RELEASEFENCE_SCHEMA", "releasefence"),
    )
