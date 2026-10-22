"""Versioned rollout state machine and exact-target deployment authority."""

import secrets

from contracts.releasefence import Attestation, Command, Policy

from .core import analyze, assignment, digest, metrics, scoped_events
from .crypto import signed, verify
from .errors import Conflict, Forbidden


class Operations:
    def cancel(self, actor, tenant, rollout, revision):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "operator"})
            roll = self._get(db, "rollout", rollout)
            if roll["revision"] != revision or roll["state"] != "ready" or roll["commands"]:
                raise Conflict("only an unstarted rollout can be cancelled")
            env = self._get(db, "environment", roll["application"] + ":" + roll["environment"])
            if env["active_rollout"] != rollout:
                raise Conflict("environment changed")
            roll["state"] = "cancelled"
            env["active_rollout"] = None
            self._save(db, "rollout", roll)
            self._save(db, "environment", env)
            self._audit(db, actor, "rollout_cancelled", {"rollout": rollout})

    def recover(self, actor, tenant, rollout, expires):
        """Reconcile expired commands, never assume timeout means not applied.

        Recovery only permits a newly approved rollback; it cannot promote.
        """
        if not self.now() < expires <= self.now() + 86400:
            raise ValueError("finite recovery required")
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            roll = self._get(db, "rollout", rollout)
            if roll["state"] in {"ready", "promoted", "rollback_verified", "cancelled"}:
                raise Conflict("no active recovery")
            for cid in roll["commands"]:
                command = self._get(db, "command", cid)
                cmd = Command.model_validate(command["envelope"]["body"])
                enrolled = self._get(db, "enrollment", cmd.enrollment)
                proof = enrolled["attestation"]
                if (
                    not proof
                    or self.now() - enrolled["last_seen"] > 30
                    or proof["at"] <= cmd.expires + 60
                ):
                    raise Conflict("fresh post-expiry runtime reconciliation required")
                if proof["revision"] not in {cmd.expected_revision, cmd.expected_revision + 1}:
                    raise Conflict("unrecognized runtime revision")
                if proof["revision"] == cmd.expected_revision + 1 and any(
                    proof[k] != getattr(cmd, k) for k in ("epoch", "stable", "candidate", "weight")
                ):
                    raise Conflict("runtime target mismatch")
                command.update(state="reconciled", proof=proof)
                self._save(db, "command", command)
            roll.update(state="recovery_required", expires=expires, decision=None)
            self._save(db, "rollout", roll)
            self._audit(
                db,
                actor,
                "rollout_recovery_scoped",
                {"rollout": rollout, "expires": expires, "revision": roll["revision"]},
            )

    def destination(self, actor, tenant, url, secret, key, *, lab_loopback=False):
        from .network import resolve_destination

        resolve_destination(url, lab_loopback=lab_loopback)
        if not 24 <= len(secret) <= 512:
            raise ValueError("strong webhook secret required")
        payload = {
            "url_hash": digest(url.encode()),
            "secret_hash": digest(secret.encode()),
            "lab_loopback": lab_loopback,
        }
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            prior = self._intent(db, "destination:" + actor, key, payload)
            if prior:
                return prior
            if len(self._rows(db, "destination")) >= 10:
                raise Conflict("destination quota")
            id = secrets.token_hex(16)
            self._insert(
                db,
                "destination",
                id,
                {
                    "url_box": self.box.encrypt(url.encode()).decode(),
                    "secret_box": self.box.encrypt(secret.encode()).decode(),
                    "enabled": True,
                    "lab_loopback": lab_loopback,
                },
            )
            self._remember(db, "destination:" + actor, key, payload, id)
            self._audit(
                db, actor, "destination_registered", {"id": id, "url_hash": payload["url_hash"]}
            )
            return id

    def notification_replay(self, actor, tenant, notification):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            row = self._get(db, "notification", notification)
            if row["state"] != "dead_letter" or row["replayed"]:
                raise Conflict("one bounded dead-letter replay only")
            row.update(state="retry", replayed=True, maximum_attempts=10, due=self.now())
            self._save(db, "notification", row)
            self._audit(db, actor, "notification_replayed", {"id": notification})

    def acknowledge(self, actor, tenant, incident):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "operator"})
            row = self._get(db, "incident", incident)
            if row["state"] == "resolved":
                raise Conflict("resolved episode cannot be reopened by acknowledgement")
            row["state"] = "acknowledged"
            self._save(db, "incident", row)
            self._audit(db, actor, "incident_acknowledged", {"id": incident})

    def resolve(self, actor, tenant, incident, note):
        if not 12 <= len(note.strip()) <= 500:
            raise ValueError("bounded resolution reason required")
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "operator"})
            row = self._get(db, "incident", incident)
            if row["state"] != "acknowledged":
                raise Conflict("acknowledgement required")
            enrolled = self._get(db, "enrollment", row["enrollment"])
            proof = enrolled["attestation"]
            if not proof or self.now() - enrolled["last_seen"] > 60:
                raise Conflict("fresh runtime evidence required")
            if row["severity"] == "critical":
                roll = self._get(db, "rollout", row["rollout"]) if row["rollout"] else None
                if (
                    not roll
                    or roll["state"] != "rollback_verified"
                    or proof["active_candidate"]
                    or proof["probe_release"] != roll["stable"]
                ):
                    raise Conflict("verified mitigation required")
            elif row["rule"] != "telemetry_stale":
                if not any(
                    r["enrollment"] == row["enrollment"]
                    and r["event"]["task"] == row["task"]
                    and r["event"]["kind"] == "terminal"
                    for r in self._rows(db, "event", 50001)
                ):
                    raise Conflict("task remains unresolved")
            row.update(
                state="resolved",
                resolution={
                    "note": note,
                    "actor": actor,
                    "at": self.now(),
                    "proof_hash": digest(proof),
                },
            )
            self._save(db, "incident", row)
            self._audit(
                db, actor, "incident_resolved", {"incident": incident, "proof_hash": digest(proof)}
            )

    def create_rollout(
        self,
        actor,
        tenant,
        application,
        environment,
        stable,
        candidate,
        policy,
        enrollments,
        expires,
        key,
    ):
        policy = Policy.model_validate(policy)
        if (
            not self.now() < expires <= self.now() + 86400
            or not enrollments
            or len(enrollments) > 100
            or len(set(enrollments)) != len(enrollments)
        ):
            raise ValueError("finite explicit runtime scope required")
        payload = {
            "application": application,
            "environment": environment,
            "stable": stable,
            "candidate": candidate,
            "policy": policy.model_dump(),
            "enrollments": enrollments,
            "expires": expires,
        }
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "operator"})
            prior = self._intent(db, "rollout:" + actor, key, payload)
            if prior:
                return prior
            env = self._get(db, "environment", application + ":" + environment)
            if (
                env["active_rollout"]
                or env["paused"]
                or env["stable"] != stable
                or stable == candidate
            ):
                raise Conflict("known baseline or exclusive environment unavailable")
            for id in (stable, candidate):
                if self._get(db, "release", id)["application"] != application:
                    raise Conflict("application mismatch")
            for id in enrollments:
                row = self._get(db, "enrollment", id)
                if (
                    row["application"] != application
                    or row["environment"] != environment
                    or row["mode"] != "controlled"
                    or row["revoked"]
                ):
                    raise Forbidden("scoped control capability required")
            active = sum(
                r["state"] not in {"promoted", "rollback_verified", "cancelled"}
                for r in self._rows(db, "rollout")
            )
            if active >= 10:
                raise Conflict("active rollout quota")
            id = secrets.token_hex(16)
            body = {
                **payload,
                "creator": actor,
                "state": "ready",
                "stage": 0,
                "seed": secrets.token_hex(16),
                "started": None,
                "decision": None,
                "commands": [],
                "issues": [],
            }
            self._insert(db, "rollout", id, body)
            env["active_rollout"] = id
            self._save(db, "environment", env)
            self._remember(db, "rollout:" + actor, key, payload, id)
            self._audit(
                db, actor, "rollout_registered", {"rollout": id, "binding": digest(payload)}
            )
            return id

    def _scope(self, roll):
        return digest(
            {
                k: roll[k]
                for k in (
                    "application",
                    "environment",
                    "stable",
                    "candidate",
                    "policy",
                    "enrollments",
                    "expires",
                    "seed",
                )
            }
        )

    def _hard_failure(self, db, roll):
        for row in self._rows(db, "event", 50001):
            event = row["event"]
            if (
                row["enrollment"] not in roll["enrollments"]
                or event["release"] != roll["candidate"]
                or row["created"] < roll["created"]
            ):
                continue
            if event["stop_reason"] in {"iteration_exhausted", "deadline", "schema_exhausted"} or (
                event["iteration"] is not None
                and event["iteration"] > roll["policy"]["max_iterations"]
            ):
                return True
        return False

    def approve(
        self, actor, tenant, rollout, revision, actions, expires, key, *, auto_rollback=False
    ):
        if (
            not actions
            or not set(actions) <= {"canary", "promote", "rollback"}
            or type(auto_rollback) is not bool
        ):
            raise ValueError("invalid actions")
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "approver"})
            roll = self._get(db, "rollout", rollout)
            if actor == roll["creator"]:
                raise Forbidden("independent approval required")
            payload = {
                "rollout": rollout,
                "revision": revision,
                "actions": sorted(set(actions)),
                "expires": expires,
                "auto_rollback": auto_rollback,
            }
            prior = self._intent(db, "approval:" + actor, key, payload)
            if prior:
                return prior
            if roll["revision"] != revision or not self.now() < expires <= roll["expires"]:
                raise Conflict("exact current approval context required")
            id = secrets.token_hex(16)
            self._insert(
                db,
                "approval",
                id,
                {**payload, "actor": actor, "scope": self._scope(roll), "revoked": False},
            )
            self._remember(db, "approval:" + actor, key, payload, id)
            self._audit(
                db,
                actor,
                "control_approved",
                {
                    "approval": id,
                    "rollout": rollout,
                    "actions": actions,
                    "auto_rollback": auto_rollback,
                },
            )
            return id

    def _authority(self, db, roll, action, *, automatic=False):
        if self.now() >= roll["expires"]:
            raise Conflict("rollout authority expired")
        valid = [
            a
            for a in self._rows(db, "approval")
            if a["rollout"] == roll["id"]
            and a["scope"] == self._scope(roll)
            and action in a["actions"]
            and not a["revoked"]
            and a["expires"] > self.now()
            and (not automatic or a["auto_rollback"])
        ]
        current = {
            r["actor"]
            for r in db.execute(
                "SELECT actor FROM members WHERE tenant::text=current_setting('rf.tenant') AND role IN ('owner','approver')"
            )
        }
        valid = [a for a in valid if a["actor"] in current]
        if not valid:
            raise Forbidden("current exact-target approval required")
        return valid[-1]

    def revoke_approval(self, actor, tenant, approval):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "approver"})
            row = self._get(db, "approval", approval)
            row["revoked"] = True
            self._save(db, "approval", row)
            self._audit(db, actor, "approval_revoked", {"id": approval})

    def control(self, actor, tenant, rollout, action, revision, key, *, automatic=False):
        if action not in {"canary", "promote", "rollback"}:
            raise ValueError("invalid action")
        with self.db(tenant) as db:
            if not automatic:
                self._role(db, actor, {"owner", "operator"})
            roll = self._get(db, "rollout", rollout)
            payload = {"rollout": rollout, "action": action, "revision": revision}
            prior = self._intent(db, "control:" + actor, key, payload)
            if prior is not None:
                return prior
            if roll["revision"] != revision:
                raise Conflict("routing/rollout revision changed")
            authority = self._authority(db, roll, action, automatic=automatic)
            if action != "rollback" and self._hard_failure(db, roll):
                raise Conflict("critical candidate failure forbids expansion")
            env = self._get(db, "environment", roll["application"] + ":" + roll["environment"])
            if env["active_rollout"] != rollout or env["paused"]:
                raise Conflict("environment authority unavailable")
            if any(
                self._get(db, "command", id)["state"]
                not in ({"verified", "reconciled"} if action == "rollback" else {"verified"})
                for id in roll["commands"]
            ):
                raise Conflict("reconcile previous commands first")
            if action == "canary":
                if not (
                    roll["state"] == "ready"
                    or roll["state"] == "promotion_pending"
                    and roll["stage"] == 5
                ):
                    raise Conflict("canary analysis required")
                weight = 5 if roll["stage"] == 0 else 25
            elif action == "promote":
                if roll["state"] != "promotion_pending" or roll["stage"] != 25:
                    raise Conflict("final canary analysis required")
                weight = 100
            else:
                if roll["state"] in {"rollback_verified", "promoted", "cancelled", "ready"}:
                    raise Conflict("not an active reversible rollout")
                weight = 0
            env["epoch"] += 1
            self._save(db, "environment", env)
            commands = []
            for id in roll["enrollments"]:
                row = self._get(db, "enrollment", id)
                if row["revoked"] or row["expires"] <= self.now() or row["mode"] != "controlled":
                    raise Forbidden("connector authority revoked")
                if action != "rollback":
                    proof = row["attestation"]
                    if (
                        not proof
                        or self.now() - row["last_seen"] > 60
                        or not {roll["stable"], roll["candidate"]}
                        <= set(proof["available_bundles"])
                        or proof["probe_kind"] != "http_bundle"
                        or not proof["probe_receipt"]
                    ):
                        raise Conflict("fresh compatible runtime inventory required")
                    if roll["stage"] == 0 and (
                        proof["probe_release"] != roll["stable"] or proof["weight"] != 0
                    ):
                        raise Conflict("healthy stable baseline required")
                cid = secrets.token_hex(16)
                cmd = Command(
                    id=cid,
                    enrollment=id,
                    application=roll["application"],
                    environment=roll["environment"],
                    rollout=rollout,
                    epoch=env["epoch"],
                    expected_revision=row["observed_revision"],
                    expires=min(authority["expires"], self.now() + 120),
                    action=action,
                    stable=roll["stable"],
                    candidate=roll["candidate"],
                    weight=weight,
                    seed=roll["seed"],
                    authority=authority["id"],
                )
                self._insert(
                    db,
                    "command",
                    cid,
                    {
                        "rollout": rollout,
                        "enrollment": id,
                        "envelope": signed(cmd, self.key),
                        "state": "pending",
                        "proof": None,
                    },
                )
                commands.append(cid)
            roll.update(
                state="verifying",
                stage=weight,
                commands=commands,
                started=None,
                decision=None,
                issues=[],
            )
            self._save(db, "rollout", roll)
            self._remember(db, "control:" + actor, key, payload, commands)
            self._audit(
                db,
                actor,
                "control_requested",
                {"rollout": rollout, "action": action, "commands": commands},
            )
            return commands

    def heartbeat(self, auth, envelope):
        with self.db(auth["tenant"]) as db:
            row = self._get(db, "enrollment", auth["enrollment"])
            proof = Attestation.model_validate(verify(envelope, row["public_key"]))
            if (
                row["revoked"]
                or proof.enrollment != row["id"]
                or abs(proof.at - self.now()) > 60
                or proof.revision < row["observed_revision"]
                or proof.revision == row["observed_revision"]
                and row["attestation"]
                and any(
                    getattr(proof, k) != row["attestation"][k]
                    for k in ("stable", "candidate", "weight", "epoch")
                )
            ):
                raise Conflict("stale or invalid runtime attestation")
            row.update(
                attestation=proof.model_dump(mode="json"),
                attestation_envelope=envelope,
                last_seen=min(proof.at, self.now()),
                observed_revision=proof.revision,
            )
            if proof.window_start is not None:
                row["window_attestation"] = proof.model_dump(mode="json")
                row["window_attestation_envelope"] = envelope
            self._save(db, "enrollment", row)
            return proof.model_dump(mode="json")

    def poll(self, auth):
        with self.db(auth["tenant"]) as db:
            row = self._get(db, "enrollment", auth["enrollment"])
            if row["revoked"]:
                raise Forbidden("revoked")
            return [
                r["envelope"]
                for r in self._rows(db, "command")
                if r["enrollment"] == auth["enrollment"] and r["state"] in {"pending", "partial"}
            ][:10]

    def counter_window(self, auth):
        with self.db(auth["tenant"]) as db:
            for roll in self._rows(db, "rollout"):
                if auth["enrollment"] in roll["enrollments"] and roll["state"] == "canary_running":
                    return [roll["started"], roll["started"] + roll["policy"]["stage_seconds"]]
        return None

    def authorize_command(self, auth, command):
        with self.db(auth["tenant"]) as db:
            row = self._get(db, "command", command)
            cmd = Command.model_validate(row["envelope"]["body"])
            if row["enrollment"] != auth["enrollment"] or cmd.expires <= self.now():
                raise Forbidden("command scope or expiry")
            roll = self._get(db, "rollout", row["rollout"])
            if (
                row["state"] not in {"pending", "partial"}
                or command not in roll["commands"]
                or self.now() >= roll["expires"]
            ):
                raise Forbidden("command is no longer current")
            approval = self._get(db, "approval", cmd.authority)
            self._role(db, approval["actor"], {"owner", "approver"})
            enrolled = self._get(db, "enrollment", auth["enrollment"])
            if (
                enrolled["revoked"]
                or enrolled["mode"] != "controlled"
                or approval["revoked"]
                or approval["expires"] <= self.now()
                or approval["scope"] != self._scope(roll)
            ):
                raise Forbidden("authority revoked")
            return True

    def attest(self, auth, envelope):
        # Command read-back may reconcile a past executed action after authority expired;
        # accepting evidence is not permission to execute an expired action again.
        with self.db(auth["tenant"]) as db:
            enrolled = self._get(db, "enrollment", auth["enrollment"])
            proof = Attestation.model_validate(verify(envelope, enrolled["public_key"]))
            row = self._get(db, "command", proof.command)
            cmd = Command.model_validate(row["envelope"]["body"])
            roll = self._get(db, "rollout", cmd.rollout)
            expected_arm = assignment(
                f"{auth['enrollment']}:{cmd.application}:{cmd.environment}",
                proof.probe_session,
                cmd.seed,
                cmd.weight,
            )
            if (
                enrolled["revoked"]
                or row["enrollment"] != auth["enrollment"]
                or proof.enrollment != auth["enrollment"]
                or abs(proof.at - self.now()) > 60
                or proof.revision < enrolled["observed_revision"]
                or cmd.id not in roll["commands"]
                or proof.revision != cmd.expected_revision + 1
                or proof.epoch != cmd.epoch
                or proof.weight != cmd.weight
                or proof.stable != cmd.stable
                or proof.candidate != cmd.candidate
                or proof.probe_release != getattr(cmd, expected_arm)
                or not ({cmd.stable} if cmd.action == "rollback" else {cmd.stable, cmd.candidate})
                <= set(proof.available_bundles)
                or proof.probe_kind != "http_bundle"
                or not proof.probe_receipt
            ):
                raise Conflict("runtime verification failed")
            if row["state"] == "verified":
                return True
            row.update(
                state="partial"
                if cmd.action == "rollback" and proof.active_candidate
                else "verified",
                proof=proof.model_dump(mode="json"),
                proof_envelope=envelope,
            )
            self._save(db, "command", row)
            enrolled.update(
                attestation=proof.model_dump(mode="json"),
                attestation_envelope=envelope,
                last_seen=min(proof.at, self.now()),
                observed_revision=proof.revision,
            )
            self._save(db, "enrollment", enrolled)
            roll = self._get(db, "rollout", cmd.rollout)
            if all(self._get(db, "command", id)["state"] == "verified" for id in roll["commands"]):
                roll.update(
                    state="rollback_verified"
                    if cmd.action == "rollback"
                    else "promoted"
                    if cmd.action == "promote"
                    else "canary_running",
                    started=self.now(),
                    counter_baseline={
                        id: self._get(db, "enrollment", id)["attestation"]["counters"]
                        for id in roll["enrollments"]
                    },
                )
                self._save(db, "rollout", roll)
                if cmd.action in {"promote", "rollback"}:
                    env = self._get(db, "environment", cmd.application + ":" + cmd.environment)
                    env["active_rollout"] = None
                    if cmd.action == "promote":
                        env["stable"] = cmd.candidate
                    self._save(db, "environment", env)
            self._audit(
                db,
                "connector:" + auth["enrollment"],
                "runtime_verified",
                {
                    "command": cmd.id,
                    "rollout": cmd.rollout,
                    "state": row["state"],
                    "proof_hash": digest(proof),
                    "proof_envelope_hash": digest(envelope),
                },
            )
            return row["state"] == "verified"

    def analyze_rollout(self, actor, tenant, rollout):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "operator"})
            roll = self._get(db, "rollout", rollout)
            if roll["decision"]:
                return self._get(db, "decision", roll["decision"])
            if roll["state"] != "canary_running" or roll["stage"] not in {5, 25}:
                raise Conflict("canary is not running")
            policy = Policy.model_validate(roll["policy"])
            end = roll["started"] + policy.stage_seconds
            if self.now() < end + policy.lateness_seconds:
                return {"decision": "inconclusive", "reasons": ["window_not_closed"]}
            all_events = [
                r
                for r in self._rows(db, "event", 50001)
                if r["application"] == roll["application"]
                and r["environment"] == roll["environment"]
                and r["enrollment"] in roll["enrollments"]
            ]
            starts = {
                (r["enrollment"], r["event"]["task"])
                for r in all_events
                if r["event"]["kind"] == "accepted" and roll["started"] <= r["event"]["at"] < end
            }
            selected = [
                r
                for r in all_events
                if (r["enrollment"], r["event"]["task"]) in starts
                and r["event"]["at"] <= end + policy.lateness_seconds
            ]
            # Runtime-local task/session/attempt IDs are namespaced across enrollments.
            events = scoped_events(selected)
            values = [
                metrics([e for e in events if e.release == rel])
                for rel in (roll["stable"], roll["candidate"])
            ]
            coverage = min(v["coverage"] or 0 for v in values)
            from .backends import trace_gate

            backends = self._rows(db, "backend")
            backlog = {}
            for backend in backends:
                backlog[backend["kind"]] = db.execute(
                    """SELECT count(*) n FROM records s WHERE s.kind='span'
                  AND s.body->>'application'=%s AND s.body->>'environment'=%s
                  AND s.body->>'enrollment'=ANY(%s)
                  AND s.body->'span'->>'release' IN (%s,%s)
                  AND (s.body->'span'->>'started_ns')::numeric>=%s
                  AND (s.body->'span'->>'started_ns')::numeric<%s
                  AND NOT EXISTS(SELECT 1 FROM records e WHERE e.kind='trace_export'
                    AND e.id=%s||':'||s.id AND e.body->>'state'='verified')""",
                    (
                        roll["application"],
                        roll["environment"],
                        roll["enrollments"],
                        roll["stable"],
                        roll["candidate"],
                        int(roll["started"] * 10**9),
                        int(end * 10**9),
                        backend["id"],
                    ),
                ).fetchone()["n"]
            issues = trace_gate(
                backends,
                roll["application"] + ":" + roll["environment"],
                roll["stable"],
                roll["candidate"],
                roll["started"],
                end,
                self.now(),
                backlog=backlog,
                profile=policy.trace_profile,
            )
            for id in roll["enrollments"]:
                row = self._get(db, "enrollment", id)
                if row["last_seen"] is None or self.now() - row["last_seen"] > 60:
                    issues.append("stale_runtime")
                proof = row.get("window_attestation")
                if (
                    not proof
                    or proof["window_start"] != roll["started"]
                    or proof["window_end"] != end
                    or proof["at"] < end + policy.lateness_seconds
                ):
                    issues.append("missing_closed_window_counters")
                    continue
                after = {c["release"]: c["accepted"] for c in proof["counters"]}
                expected = sum(after.get(rel, 0) for rel in (roll["stable"], roll["candidate"]))
                received = sum(
                    r["event"]["kind"] == "accepted" for r in selected if r["enrollment"] == id
                )
                if expected != received:
                    issues.append("lifecycle_counter_mismatch")
            result = analyze(
                values[0]["observations"], values[1]["observations"], policy, coverage=coverage
            )
            if self._hard_failure(db, roll):
                result.update(decision="fail", reasons=["critical_candidate_failure"])
            elif issues or any(
                v["latency_missing"] or v["unknown_calls"] or v["orphan_events"] for v in values
            ):
                result.update(
                    decision="inconclusive",
                    reasons=issues or ["incomplete_usage_latency_or_orphans"],
                )
            wid = secrets.token_hex(16)
            did = secrets.token_hex(16)
            self._insert(
                db,
                "window",
                wid,
                {
                    "rollout": rollout,
                    "stage": roll["stage"],
                    "from": roll["started"],
                    "to": end,
                    "event_hash": digest([e.model_dump(mode="json") for e in events]),
                    "metrics": [
                        {k: v for k, v in x.items() if k != "observations"} for x in values
                    ],
                    "policy_hash": digest(policy),
                },
            )
            self._insert(db, "decision", did, {**result, "rollout": rollout, "window": wid})
            roll.update(
                decision=did,
                state="promotion_pending"
                if result["decision"] == "pass"
                else "failed_canary"
                if result["decision"] == "fail"
                else "paused_inconclusive",
            )
            self._save(db, "rollout", roll)
            self._audit(
                db,
                actor,
                "canary_decision",
                {"rollout": rollout, "decision": did, "window": wid, "result": result["decision"]},
            )
            return {**result, "id": did, "window": wid}
