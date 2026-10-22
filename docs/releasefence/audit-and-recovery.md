# Durable decisions, command reconciliation and recovery

Use PostgreSQL transactional state transitions plus an outbox. Persist exact
decision evidence and authorized command before network delivery. Workers claim
finite leases with fencing epochs; stale workers cannot commit either success
or failure after another owner has taken over. Deliveries are at-least-once.

## Evidence chain

Preserve original release/policy versions, assignment/metric-window hashes,
analysis result, approval, command, delivery attempts, runtime attestations/probes,
unknowns, incident resolution and actor identities. Append corrections or successor
records; do not overwrite old failure states into a pass. A changed analysis policy
cannot retroactively justify a command already executed under another policy.

Runtime evidence is retained as both the decoded attestation and its original
signed envelope. Verified command records include `proof_envelope`; enrollment
heartbeat/window records preserve `attestation_envelope` and
`window_attestation_envelope`. The verification audit binds the envelope hash as
well as the decoded proof hash. Exported commands retain their signed server
envelopes. Independent readers verify with the enrolled runtime and server public
keys, not an API's `verified` label alone. No private signing key is exported.
Decoded-only records from earlier builds cannot have signatures reconstructed;
do not fabricate them or claim retroactive cryptographic qualification.

Unknown cost, unknown task outcome and unknown command execution are separate
liabilities. An operator cannot close them all with one generic “retry” button.
No automatic incident forgiveness or grant reset is part of this product.

## Critical crash/partition cases

| Failure point | Required recovery |
| --- | --- |
| Before outbox transaction commits | No command exists and no external execution may occur |
| After commit, before delivery | Reclaim same command ID under a new delivery lease |
| Runtime applies change, acknowledgement lost | Read back actual revision/command ID; never infer non-execution or create a different blind command |
| Stale worker resumes | Fencing/expected revision rejects writes/execution |
| Telemetry arrives after decision | Store late evidence/correction; do not rewrite original decision window |
| Connector offline | Hold promotion, mark rollback partial/unverified and preserve serving-scope uncertainty |
| Notification response lost | Retry stable delivery ID; receiver dedups; no exactly-once claim |
| Control-plane restart | Resume durable decisions/outboxes without reauthorizing expired actions |

Customer runtime persists command result/epoch and current manifest locally with
crash-safe writes. Test process termination before/after each persistence/network
boundary. Do not rely only on exceptions inside a single-process unit test.

## Backup and restore

Plan consistent PostgreSQL backups, migration/version manifest, encryption/key
separation, restore checks and retention. Restore to a new isolated target in
quarantine; do not overwrite the live root. Reconcile runtime commands/current
epochs and revocations against live connectors before releasing control. Old
restored approvals cannot replay production commands. Reapply newer deletion or
revocation authority from an independently retained record.

Administrative recovery is a filesystem/operator-authorized procedure with a
current evidence head, ownership checks, bounded action and audit—not a public
unauthenticated endpoint. No restore/erase/credential mutation is authorized by
writing this plan. Logical data deletion must disclose backup/WAL/export remnants;
it is not advertised as guaranteed physical erasure.
