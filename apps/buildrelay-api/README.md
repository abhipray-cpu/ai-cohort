# BuildRelay API & worker

Day 8 event-triggered CI response service. See the [delivery pack](../../docs/buildrelay/README.md)
and [operations](../../docs/buildrelay/implementation-and-operations.md).

Start/stop: `make buildrelay-up` / `make buildrelay-down`; loopback port 8007.
Requires explicit credentials, installed Python workspace, built web app, and
authenticated installed Codex for AI generation. Queue ingress additionally needs
a separately provisioned authenticated NATS JetStream server.

Implementation-tested pilot, not full product/release acceptance.
