"""Independent authenticated JetStream ingress; ACK means durable inbox acceptance."""

import asyncio
import hashlib
import os
import sqlite3

from contracts.buildrelay import QueueEnvelope


async def consume_message(store, message):
    try:
        if len(message.data) > 65536:
            raise ValueError("oversized queue envelope")
        envelope = QueueEnvelope.model_validate_json(message.data)
        store.accept(envelope.repo_id, envelope.event, "queue", envelope.delivery_id)
    except (ValueError, KeyError):
        # Invalid input cannot safely be replayed. Retain a digest, not potential secrets.
        try:
            with store.write() as db:
                store.record(
                    db,
                    "queue_rejected",
                    actor="queue",
                    detail={
                        "sha256": hashlib.sha256(message.data).hexdigest(),
                        "bytes": len(message.data),
                        "resolution": "correct producer envelope; original payload not retained",
                    },
                )
            await message.term()
        except (sqlite3.Error, OSError):
            await message.nak(delay=10)
    except (sqlite3.Error, OSError):
        await message.nak(delay=10)
    else:
        await message.ack_sync()


async def listen(store, stop):
    import nats
    from nats.errors import TimeoutError
    from nats.js.api import AckPolicy, ConsumerConfig

    url = os.environ.get("BUILDRELAY_NATS_URL", "")
    if not url:
        return
    kwargs = {}
    if os.environ.get("BUILDRELAY_NATS_CREDS"):
        kwargs["user_credentials"] = os.environ["BUILDRELAY_NATS_CREDS"]
    nc = await nats.connect(url, name="buildrelay-ingress", **kwargs)
    try:
        js = nc.jetstream()
        # Operator provisions the stream. Never mutate an existing broker's stream policy.
        sub = await js.pull_subscribe(
            os.environ.get("BUILDRELAY_NATS_SUBJECT", "buildrelay.runs"),
            durable="buildrelay-inbox-v1",
            stream=os.environ.get("BUILDRELAY_NATS_STREAM", "BUILDRELAY"),
            config=ConsumerConfig(
                ack_policy=AckPolicy.EXPLICIT, ack_wait=30, max_ack_pending=16, max_deliver=-1
            ),
        )
        while not stop.is_set():
            store.beat("queue", "connected")
            try:
                messages = await sub.fetch(batch=8, timeout=1)
                for message in messages:
                    await consume_message(store, message)
            except TimeoutError:
                continue
    finally:
        await nc.close()


async def resilient_listen(store, stop):
    while not stop.is_set():
        try:
            await listen(store, stop)
            return
        except Exception:  # noqa: BLE001 -- supervisor boundary; never print credentials/payload
            store.beat("queue", "disconnected")
            await asyncio.sleep(5)
