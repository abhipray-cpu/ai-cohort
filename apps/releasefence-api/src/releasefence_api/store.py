"""PostgreSQL tenant store. Migration authority is separate from the runtime role."""

import hashlib
import hmac
import secrets
import time
import uuid
from contextlib import contextmanager

import psycopg
from contracts.releasefence import Event, Release
from cryptography.fernet import Fernet
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .core import digest, metrics, scoped_events
from .crypto import public_key
from .errors import Conflict, Forbidden
from .integrations import Integrations
from .service import Operations

EVENT_CAPACITY = 50000
SPAN_CAPACITY = 50000


class Store(Operations, Integrations):
    def __init__(self, dsn, encryption_key, signing_key, *, schema="releasefence", now=time.time):
        self.dsn = dsn
        self.schema = schema
        self.box = Fernet(encryption_key)
        self.key = signing_key
        self.now = now
        with self.db() as db:
            role = db.execute(
                "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
            ).fetchone()
            if role["rolsuper"] or role["rolbypassrls"]:
                raise ValueError("non-bypass application role required")
            if db.execute("SELECT version FROM meta").fetchone()["version"] != 1:
                raise ValueError("migration required")

    @staticmethod
    def install(admin_dsn, schema, role, password):
        if not schema.startswith("rf_") and schema != "releasefence":
            raise ValueError("owned schema required")
        with psycopg.connect(admin_dsn) as db:
            db.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
            db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            db.execute(sql.SQL("SET LOCAL search_path TO {},public").format(sql.Identifier(schema)))
            db.execute("""CREATE TABLE meta(version integer NOT NULL); INSERT INTO meta VALUES(1);
              CREATE TABLE worker_status(id text PRIMARY KEY,heartbeat double precision NOT NULL);
              CREATE TABLE users(name text PRIMARY KEY,password text NOT NULL);
              CREATE TABLE sessions(hash text PRIMARY KEY,actor text REFERENCES users(name),csrf text NOT NULL,expires double precision NOT NULL);
              CREATE TABLE organizations(id uuid PRIMARY KEY,name text NOT NULL);
              CREATE TABLE members(tenant uuid REFERENCES organizations(id),actor text REFERENCES users(name),role text NOT NULL,PRIMARY KEY(tenant,actor));
              CREATE TABLE tokens(hash text PRIMARY KEY,tenant uuid REFERENCES organizations(id),enrollment text NOT NULL,expires double precision NOT NULL);
              CREATE TABLE records(tenant uuid REFERENCES organizations(id),kind text NOT NULL,id text NOT NULL,body jsonb NOT NULL,revision bigint NOT NULL DEFAULT 0,created double precision NOT NULL,PRIMARY KEY(tenant,kind,id),CHECK(octet_length(body::text)<=65536));
              CREATE INDEX record_kind ON records(tenant,kind,created);
              ALTER TABLE records ENABLE ROW LEVEL SECURITY; ALTER TABLE records FORCE ROW LEVEL SECURITY;
              CREATE POLICY tenant_records ON records USING(tenant::text=current_setting('rf.tenant',true)) WITH CHECK(tenant::text=current_setting('rf.tenant',true));
              ALTER TABLE members ENABLE ROW LEVEL SECURITY; ALTER TABLE members FORCE ROW LEVEL SECURITY;
              CREATE POLICY tenant_members ON members USING(tenant::text=current_setting('rf.tenant',true) OR actor=current_setting('rf.actor',true)) WITH CHECK(tenant::text=current_setting('rf.tenant',true));
              CREATE FUNCTION protect_evidence() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                IF OLD.kind IN ('audit','release','event','span','window','decision') THEN RAISE EXCEPTION 'immutable evidence'; END IF; RETURN NEW; END $$;
              CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON records FOR EACH ROW EXECUTE FUNCTION protect_evidence();
            """)
            db.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(role)
                )
            )
            db.execute(
                sql.SQL(
                    "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}"
                ).format(sql.Identifier(schema), sql.Identifier(role))
            )
            db.execute(
                sql.SQL("REVOKE INSERT,UPDATE,DELETE ON meta FROM {}").format(sql.Identifier(role))
            )

    @contextmanager
    def db(self, tenant=None, actor=""):
        if tenant:
            tenant = str(uuid.UUID(str(tenant)))
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5) as db:
            db.execute(
                sql.SQL("SET LOCAL search_path TO {},public").format(sql.Identifier(self.schema))
            )
            db.execute("SET LOCAL statement_timeout='15s'")
            db.execute(
                "SELECT set_config('rf.tenant',%s,true),set_config('rf.actor',%s,true)",
                (tenant or "", actor),
            )
            if tenant:
                db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (tenant,))
            yield db

    def _role(self, db, actor, roles=None):
        member = db.execute(
            "SELECT role FROM members WHERE tenant::text=current_setting('rf.tenant') AND actor=%s",
            (actor,),
        ).fetchone()
        if not member or roles and member["role"] not in roles:
            raise Forbidden("object unavailable or action forbidden")
        return member["role"]

    def _get(self, db, kind, id):
        row = db.execute(
            "SELECT id,body,revision,created FROM records WHERE kind=%s AND id=%s", (kind, id)
        ).fetchone()
        if not row:
            raise Forbidden("object unavailable or action forbidden")
        return {
            **row["body"],
            "id": row["id"],
            "revision": row["revision"],
            "created": row["created"],
        }

    def _insert(self, db, kind, id, body):
        db.execute(
            "INSERT INTO records(tenant,kind,id,body,created) VALUES(current_setting('rf.tenant')::uuid,%s,%s,%s,%s)",
            (kind, id, Jsonb(body), self.now()),
        )
        return id

    def _save(self, db, kind, row, expected=None):
        body = {k: v for k, v in row.items() if k not in {"id", "revision", "created"}}
        changed = db.execute(
            "UPDATE records SET body=%s,revision=revision+1 WHERE kind=%s AND id=%s AND revision=%s RETURNING revision",
            (Jsonb(body), kind, row["id"], row["revision"] if expected is None else expected),
        ).fetchone()
        if not changed:
            raise Conflict("revision conflict")
        row["revision"] = changed["revision"]

    def _rows(self, db, kind, limit=10000):
        rows = [
            {**r["body"], "id": r["id"], "revision": r["revision"], "created": r["created"]}
            for r in db.execute(
                "SELECT id,body,revision,created FROM records WHERE kind=%s ORDER BY created,id LIMIT %s",
                (kind, limit + 1),
            )
        ]
        if len(rows) > limit:
            raise Conflict("resource capacity exceeded; refusing incomplete automation input")
        return rows

    def _audit(self, db, actor, event, body):
        prior = db.execute(
            "SELECT body FROM records WHERE kind='audit' ORDER BY (body->>'sequence')::bigint DESC LIMIT 1"
        ).fetchone()
        last = prior["body"] if prior else None
        entry = {
            "sequence": last["sequence"] + 1 if last else 1,
            "previous": digest(last) if last else None,
            "actor": actor,
            "event": event,
            "at": self.now(),
            "detail": body,
        }
        self._insert(db, "audit", secrets.token_hex(16), entry)

    def _intent(self, db, operation, key, payload):
        if not 1 <= len(key) <= 128:
            raise ValueError("bounded idempotency key required")
        id = digest([operation, key])
        row = db.execute("SELECT body FROM records WHERE kind='intent' AND id=%s", (id,)).fetchone()
        if row:
            if row["body"]["hash"] != digest(payload):
                raise Conflict("idempotency content conflict")
            return row["body"]["result"]
        return None

    def _remember(self, db, operation, key, payload, result):
        self._insert(
            db, "intent", digest([operation, key]), {"hash": digest(payload), "result": result}
        )

    def create_user(self, actor, password):
        if not 1 <= len(actor) <= 100 or len(password) < 12 or len(password) > 512:
            raise ValueError("explicit strong credentials required")
        salt = secrets.token_bytes(16)
        encoded = (
            salt.hex() + ":" + hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000).hex()
        )
        with self.db() as db:
            if db.execute("SELECT 1 FROM users WHERE name=%s", (actor,)).fetchone():
                raise Conflict("user exists")
            db.execute("INSERT INTO users VALUES(%s,%s)", (actor, encoded))

    def login(self, actor, password):
        with self.db() as db:
            row = db.execute("SELECT password FROM users WHERE name=%s", (actor,)).fetchone()
            salt, expected = (row["password"] if row else "00" * 16 + ":" + "00" * 32).split(":")
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt), 600000
            ).hex()
            if not row or not hmac.compare_digest(expected, actual):
                raise Forbidden("invalid credentials")
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(24)
            db.execute(
                "INSERT INTO sessions VALUES(%s,%s,%s,%s)",
                (digest(token.encode()), actor, csrf, self.now() + 28800),
            )
            return token, csrf

    def session(self, token):
        with self.db() as db:
            row = db.execute(
                "SELECT actor,csrf,expires FROM sessions WHERE hash=%s AND expires>%s",
                (digest(token.encode()), self.now()),
            ).fetchone()
            if not row:
                raise Forbidden("session required")
            return row

    def logout(self, token):
        with self.db() as db:
            db.execute("DELETE FROM sessions WHERE hash=%s", (digest(token.encode()),))

    def create_org(self, actor, name):
        if not name.strip() or len(name) > 150:
            raise ValueError("bounded name required")
        tenant = str(uuid.uuid4())
        with self.db(tenant, actor) as db:
            db.execute("INSERT INTO organizations VALUES(%s,%s)", (tenant, name))
            db.execute("INSERT INTO members VALUES(%s,%s,'owner')", (tenant, actor))
            self._audit(db, actor, "organization_created", {})
        return tenant

    def organizations(self, actor):
        with self.db(actor=actor) as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT o.id::text,o.name,m.role FROM organizations o JOIN members m ON m.tenant=o.id WHERE m.actor=%s",
                    (actor,),
                )
            ]

    def member(self, actor, tenant, user, role):
        if role not in {"owner", "operator", "approver", "observer"}:
            raise ValueError("invalid role")
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            old = db.execute(
                "SELECT role FROM members WHERE tenant=%s AND actor=%s", (tenant, user)
            ).fetchone()
            if (
                old
                and old["role"] == "owner"
                and role != "owner"
                and db.execute(
                    "SELECT count(*) n FROM members WHERE tenant=%s AND role='owner'", (tenant,)
                ).fetchone()["n"]
                <= 1
            ):
                raise Conflict("last owner")
            db.execute(
                "INSERT INTO members VALUES(%s,%s,%s) ON CONFLICT(tenant,actor) DO UPDATE SET role=excluded.role",
                (tenant, user, role),
            )
            self._audit(db, actor, "membership_changed", {"user": user, "role": role})

    def list(self, actor, tenant, kind, limit=100, offset=0):
        if kind not in {
            "release",
            "environment",
            "enrollment",
            "rollout",
            "approval",
            "command",
            "event",
            "span",
            "incident",
            "notification",
            "window",
            "decision",
            "audit",
            "destination",
            "health",
            "backend",
            "trace_export",
            "registration",
        }:
            raise ValueError("unknown resource")
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("bounded page required")
        with self.db(tenant) as db:
            self._role(db, actor)
            rows = db.execute(
                "SELECT id,body,revision,created FROM records WHERE kind=%s ORDER BY created DESC,id LIMIT %s OFFSET %s",
                (kind, limit, offset),
            )
            return [
                {
                    **{
                        k: v
                        for k, v in r["body"].items()
                        if k not in {"secret", "secret_box", "url_box", "export_box", "read_box"}
                    },
                    "id": r["id"],
                    "revision": r["revision"],
                    "created": r["created"],
                }
                for r in rows
            ]

    def release(self, actor, tenant, value):
        value = Release.model_validate(value)
        id = digest(value)
        with self.db(tenant) as db:
            self._role(db, actor, {"owner", "operator"})
            if not db.execute(
                "SELECT 1 FROM records WHERE kind='release' AND id=%s", (id,)
            ).fetchone():
                self._insert(db, "release", id, value.model_dump(mode="json"))
                self._audit(db, actor, "release_registered", {"digest": id})
        return id

    def environment(self, actor, tenant, application, environment, stable):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            release = self._get(db, "release", stable)
            if release["application"] != application:
                raise Conflict("application mismatch")
            id = application + ":" + environment
            if db.execute(
                "SELECT 1 FROM records WHERE kind='environment' AND id=%s", (id,)
            ).fetchone():
                raise Conflict("environment exists")
            self._insert(
                db,
                "environment",
                id,
                {
                    "application": application,
                    "environment": environment,
                    "stable": stable,
                    "epoch": 0,
                    "active_rollout": None,
                    "paused": False,
                },
            )
            self._audit(db, actor, "environment_registered", {"id": id, "stable": stable})
            return id

    def enroll(self, actor, tenant, application, environment, public, mode):
        import base64

        if (
            mode not in {"observe", "controlled"}
            or len(base64.b64decode(public, validate=True)) != 32
        ):
            raise ValueError("invalid enrollment")
        id = secrets.token_hex(16)
        token = secrets.token_urlsafe(32)
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            env = self._get(db, "environment", application + ":" + environment)
            self._insert(
                db,
                "enrollment",
                id,
                {
                    "application": application,
                    "environment": environment,
                    "public_key": public,
                    "mode": mode,
                    "revoked": False,
                    "expires": self.now() + 2592000,
                    "observed_revision": 0,
                    "last_seen": None,
                    "attestation": None,
                    "initial_stable": env["stable"],
                },
            )
            db.execute(
                "INSERT INTO tokens VALUES(%s,%s,%s,%s)",
                (digest(token.encode()), tenant, id, self.now() + 2592000),
            )
            self._audit(db, actor, "connector_enrolled", {"id": id, "mode": mode})
        return {"id": id, "token": token, "server_public_key": public_key(self.key)}

    def machine(self, token):
        with self.db() as db:
            row = db.execute(
                "SELECT tenant::text,enrollment FROM tokens WHERE hash=%s AND expires>%s",
                (digest(token.encode()), self.now()),
            ).fetchone()
        if not row:
            raise Forbidden("invalid machine credential")
        with self.db(row["tenant"]) as db:
            enrolled = self._get(db, "enrollment", row["enrollment"])
            if enrolled["revoked"] or enrolled["expires"] <= self.now():
                raise Forbidden("revoked enrollment")
            return {
                "tenant": row["tenant"],
                "enrollment": row["enrollment"],
                "application": enrolled["application"],
                "environment": enrolled["environment"],
            }

    def registration_token(self, actor, tenant, application, environment, expires):
        if not self.now() < expires <= self.now() + 3600:
            raise ValueError("one-hour registration scope maximum")
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            self._get(db, "environment", application + ":" + environment)
            if (
                sum(
                    not r["revoked"] and r["expires"] > self.now()
                    for r in self._rows(db, "registration")
                )
                >= 20
            ):
                raise Conflict("active CI credential quota")
            id = "ci:" + secrets.token_hex(16)
            token = secrets.token_urlsafe(32)
            self._insert(
                db,
                "registration",
                id,
                {
                    "actor": actor,
                    "application": application,
                    "environment": environment,
                    "expires": expires,
                    "revoked": False,
                },
            )
            db.execute(
                "INSERT INTO tokens VALUES(%s,%s,%s,%s)",
                (digest(token.encode()), tenant, id, expires),
            )
            self._audit(
                db,
                actor,
                "registration_credential_issued",
                {
                    "id": id,
                    "application": application,
                    "environment": environment,
                    "expires": expires,
                },
            )
            return {"id": id, "token": token, "expires": expires}

    def ci_release(self, token, value):
        value = Release.model_validate(value)
        with self.db() as db:
            row = db.execute(
                "SELECT tenant::text,enrollment FROM tokens WHERE hash=%s AND expires>%s",
                (digest(token.encode()), self.now()),
            ).fetchone()
        if not row or not row["enrollment"].startswith("ci:"):
            raise Forbidden("registration credential required")
        with self.db(row["tenant"]) as db:
            grant = self._get(db, "registration", row["enrollment"])
            self._role(db, grant["actor"], {"owner"})
            if (
                grant["revoked"]
                or grant["expires"] <= self.now()
                or grant["application"] != value.application
            ):
                raise Forbidden("registration scope")
            id = digest(value)
            if not db.execute(
                "SELECT 1 FROM records WHERE kind='release' AND id=%s", (id,)
            ).fetchone():
                self._insert(db, "release", id, value.model_dump(mode="json"))
                self._audit(
                    db,
                    row["enrollment"],
                    "release_registered",
                    {"digest": id, "environment": grant["environment"]},
                )
            return id

    def revoke_registration(self, actor, tenant, id):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            row = self._get(db, "registration", id)
            row["revoked"] = True
            self._save(db, "registration", row)
            db.execute("DELETE FROM tokens WHERE tenant=%s AND enrollment=%s", (tenant, id))
            self._audit(db, actor, "registration_credential_revoked", {"id": id})

    def revoke(self, actor, tenant, enrollment):
        with self.db(tenant) as db:
            self._role(db, actor, {"owner"})
            row = self._get(db, "enrollment", enrollment)
            row["revoked"] = True
            self._save(db, "enrollment", row)
            db.execute("DELETE FROM tokens WHERE tenant=%s AND enrollment=%s", (tenant, enrollment))
            self._audit(db, actor, "connector_revoked", {"enrollment": enrollment})

    def ingest(self, auth, events):
        if len(events) > 100:
            raise ValueError("event batch too large")
        events = [Event.model_validate(e) for e in events]
        count = 0
        with self.db(auth["tenant"]) as db:
            enrolled = self._get(db, "enrollment", auth["enrollment"])
            if enrolled["revoked"] or enrolled["expires"] <= self.now():
                raise Forbidden("revoked enrollment")
            retained = db.execute("SELECT count(*) n FROM records WHERE kind='event'").fetchone()[
                "n"
            ]
            for event in events:
                release = self._get(db, "release", event.release)
                if (
                    release["application"] != auth["application"]
                    or event.at > self.now() + 60
                    or event.at < self.now() - 604800
                ):
                    raise Conflict("event scope/time invalid")
                id = digest([auth["enrollment"], event.id])
                body = {
                    "application": auth["application"],
                    "environment": auth["environment"],
                    "enrollment": auth["enrollment"],
                    "event": event.model_dump(mode="json"),
                }
                prior = db.execute(
                    "SELECT body FROM records WHERE kind='event' AND id=%s", (id,)
                ).fetchone()
                if prior:
                    if prior["body"] != body:
                        raise Conflict("event ID conflict")
                    continue
                if retained + count >= EVENT_CAPACITY:
                    raise Conflict("event retention capacity reached")
                self._insert(db, "event", id, body)
                count += 1
            scoped = [
                Event.model_validate(r["event"])
                for r in self._rows(db, "event", 50001)
                if r["enrollment"] == auth["enrollment"]
            ]
            try:
                metrics(scoped)
            except ValueError as exc:
                raise Conflict("ambiguous lifecycle or usage") from exc
        return count

    def metric_view(self, actor, tenant, application, environment):
        with self.db(tenant) as db:
            self._role(db, actor)
            rows = [
                r
                for r in self._rows(db, "event", 50001)
                if r["application"] == application and r["environment"] == environment
            ]
            rows = scoped_events(rows)
            by = {}
            for release in {e.release for e in rows}:
                cohort = [e for e in rows if e.release == release]
                by[release] = {k: v for k, v in metrics(cohort).items() if k != "observations"}
                by[release].update(
                    as_of=self.now(),
                    window_from=min(e.at for e in cohort),
                    last_event_at=max(e.at for e in cohort),
                    window="retained_application_environment_events",
                )
            return by

    def ingest_spans(self, auth, spans):
        count = 0
        with self.db(auth["tenant"]) as db:
            if self._get(db, "enrollment", auth["enrollment"])["revoked"]:
                raise Forbidden("revoked")
            retained = db.execute("SELECT count(*) n FROM records WHERE kind='span'").fetchone()[
                "n"
            ]
            for span in spans:
                if self._get(db, "release", span.release)["application"] != auth["application"]:
                    raise Forbidden("span scope")
                id = digest([auth["enrollment"], span.trace_id, span.span_id])
                body = {
                    "enrollment": auth["enrollment"],
                    "application": auth["application"],
                    "environment": auth["environment"],
                    "span": span.model_dump(mode="json"),
                }
                old = db.execute(
                    "SELECT body FROM records WHERE kind='span' AND id=%s", (id,)
                ).fetchone()
                if old:
                    if old["body"] != body:
                        raise Conflict("span identity conflict")
                    continue
                if retained + count >= SPAN_CAPACITY:
                    raise Conflict("span capacity reached")
                self._insert(db, "span", id, body)
                count += 1
        return count

    def evidence(self, actor, tenant, rollout):
        with self.db(tenant) as db:
            self._role(db, actor)
            roll = self._get(db, "rollout", rollout)
            evidence = {
                "schema": "releasefence-evidence-v1",
                "rollout": roll,
                "generated_at": self.now(),
                "production_accepted": False,
            }
            for kind in (
                "release",
                "approval",
                "command",
                "window",
                "decision",
                "incident",
                "audit",
                "enrollment",
            ):
                evidence[kind] = [
                    r
                    for r in self._rows(db, kind)
                    if kind in {"audit", "enrollment"}
                    or r.get("rollout") == rollout
                    or r["id"] in {roll["stable"], roll["candidate"]}
                ]
            evidence["hash"] = digest(evidence)
            return evidence
