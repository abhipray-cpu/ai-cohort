"""Controlled invocation of the Codex executable installed on the service host."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from agent_core.provider import ProviderTimeoutError, StructuredGeneration


def codex_output_schema(schema: dict[str, object]) -> dict[str, object]:
    """Make Pydantic's schema compatible with strict structured-output providers."""

    def normalize(value):
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: normalize(item) for key, item in value.items() if key != "default"}
        properties = result.get("properties")
        if result.get("type") == "object" and isinstance(properties, dict):
            result["additionalProperties"] = False
            result["required"] = list(properties)
        return result

    return normalize(schema)


class LocalCodexProvider:
    def __init__(
        self,
        *,
        command: str = "codex",
        timeout_seconds: int = 180,
        max_output_bytes: int = 1_000_000,
        config_overrides: tuple[str, ...] = (),
        isolated: bool = False,
    ):
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.config_overrides = config_overrides
        self.isolated = isolated

    def _run(self, args, prompt):
        if not self.isolated:
            return subprocess.run(
                args,
                input=prompt,
                capture_output=True,
                text=True,
                shell=False,
                timeout=self.timeout_seconds,
                check=False,
            )
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        try:
            stdout, stderr = process.communicate(input=prompt, timeout=self.timeout_seconds)
            return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
        except BaseException:
            if process.poll() is None:
                try:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            capture_output=True,
                            timeout=5,
                            check=False,
                        )
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
                process.wait(timeout=5)
            raise

    def generate(self, *, prompt: str, schema: dict[str, object]) -> StructuredGeneration:
        with tempfile.TemporaryDirectory(prefix="tenderlens-codex-") as temporary:
            root = Path(temporary)
            schema_path = root / "schema.json"
            answer_path = root / "answer.json"
            schema_path.write_text(json.dumps(codex_output_schema(schema)), encoding="utf-8")
            args = [
                self.command,
                "exec",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--cd",
                str(root),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(answer_path),
                "-",
            ]
            for override in self.config_overrides:
                args[2:2] = ["-c", override]
            if self.isolated:
                args.insert(-1, "--json")
            started = time.monotonic()
            try:
                completed = self._run(args, prompt)
            except subprocess.TimeoutExpired as error:
                raise ProviderTimeoutError("Codex invocation timed out") from error
            except OSError as error:
                raise RuntimeError(f"Codex invocation failed: {type(error).__name__}") from error
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if completed.returncode != 0:
                return StructuredGeneration(
                    text="",
                    exit_code=completed.returncode,
                    elapsed_ms=elapsed_ms,
                    stderr=completed.stderr[-1000:],
                )
            if self.isolated:
                events = []
                for line in completed.stdout.splitlines():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                allowed = {"agent_message", "reasoning", "todo_list", "plan", "error"}
                if any(
                    event.get("item") and event["item"].get("type") not in allowed
                    for event in events
                ):
                    raise RuntimeError("Restricted Codex invocation attempted an internal tool")
                if not any(event.get("type") == "turn.completed" for event in events):
                    raise RuntimeError(
                        "Restricted Codex invocation did not complete its audited turn"
                    )
            if not answer_path.exists():
                raise RuntimeError("Codex produced no final message file")
            if answer_path.stat().st_size > self.max_output_bytes:
                raise RuntimeError("Codex response exceeded output limit")
            return StructuredGeneration(
                text=answer_path.read_text(encoding="utf-8"),
                exit_code=0,
                elapsed_ms=elapsed_ms,
                stderr=completed.stderr[-1000:],
                tools_audited=self.isolated,
            )
