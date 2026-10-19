"""Explicitly provision a dedicated broker stream or publish a validated run envelope."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from contracts.buildrelay import QueueEnvelope
from dev_stack import environment


async def main(args):
    import nats
    from nats.js.api import StorageType, StreamConfig

    os.environ.update(environment())
    url = os.environ.get("BUILDRELAY_NATS_URL")
    if not url:
        raise ValueError("BUILDRELAY_NATS_URL required")
    kwargs = {}
    if os.environ.get("BUILDRELAY_NATS_CREDS"):
        kwargs["user_credentials"] = os.environ["BUILDRELAY_NATS_CREDS"]
    nc = await nats.connect(url, **kwargs)
    try:
        js = nc.jetstream()
        stream = os.environ.get("BUILDRELAY_NATS_STREAM", "BUILDRELAY")
        subject = os.environ.get("BUILDRELAY_NATS_SUBJECT", "buildrelay.runs")
        if args.action == "provision":
            # add_stream does not overwrite incompatible existing stream settings.
            await js.add_stream(
                config=StreamConfig(
                    name=stream,
                    subjects=[subject],
                    storage=StorageType.FILE,
                    max_bytes=64000000,
                    max_age=604800,
                    max_msg_size=65536,
                )
            )
            print(
                "Dedicated stream provisioned; retention 7 days / 64 MB. Use scoped producer credentials."
            )
        elif args.action == "publish":
            body = QueueEnvelope.model_validate_json(Path(args.envelope).read_bytes())
            result = await js.publish(subject, body.model_dump_json().encode())
            print(json.dumps({"stream": result.stream, "sequence": result.seq}))
        else:
            info = await js.stream_info(stream)
            print(json.dumps({"messages": info.state.messages, "bytes": info.state.bytes}))
    finally:
        await nc.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("provision", "publish", "inspect"))
    p.add_argument("--envelope")
    a = p.parse_args()
    if a.action == "publish" and not a.envelope:
        p.error("publish requires --envelope path")
    asyncio.run(main(a))
