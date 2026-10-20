"""Installed Codex port with conservative telemetry and cooperative process cancellation."""

import json
import os
import re
import signal
import subprocess
import threading
import time

from agent_core.codex_local import LocalCodexProvider

DIAGNOSTIC_CATEGORIES = {
    "ok",
    "provider_exit",
    "rate_limit",
    "authentication",
    "network",
    "schema",
    "unsafe_tool",
    "timeout",
    "cancelled",
    "stream_limit",
    "runtime_error",
    "unknown",
}


def safe_diagnostic(value):
    """Persist fixed labels/counts only, never stderr, messages or provider keys."""
    value = value if isinstance(value, dict) else {}
    code, count = value.get("exit_code"), value.get("error_events", 0)
    category = value.get("category")
    return {
        "category": category
        if isinstance(category, str) and category in DIAGNOSTIC_CATEGORIES
        else "unknown",
        "exit_code": code if type(code) is int and -65536 <= code <= 65536 else None,
        "error_events": min(count, 1000) if type(count) is int and count >= 0 else 0,
        "unsafe_tool_event": value.get("unsafe_tool_event") is True,
        "message_retained": False,
    }


def failure_diagnostic(events, exit_code, stderr="", transport_error=None):
    allowed = {"agent_message", "reasoning", "todo_list", "plan", "error"}
    codes, errors, unsafe = [], 0, False
    hints = [stderr]
    for line in events.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") not in allowed:
            unsafe = True
        if event.get("type") in {"error", "turn.failed"}:
            errors += 1
            detail = event.get("error")
            code = event.get("code") or (detail.get("code") if isinstance(detail, dict) else None)
            if isinstance(code, str):
                codes.append(code)
            message = event.get("message") or (
                detail.get("message") if isinstance(detail, dict) else None
            )
            if isinstance(message, str):
                hints.append(message[:2048])
    category = (
        "ok"
        if exit_code == 0 and not transport_error
        else "provider_exit"
        if exit_code
        else "runtime_error"
    )
    for names, label in (
        ({"rate_limit_exceeded", "usage_limit_reached", "insufficient_quota"}, "rate_limit"),
        ({"unauthorized", "authentication_error", "invalid_api_key"}, "authentication"),
        ({"connection_error", "network_error"}, "network"),
        ({"invalid_json_schema", "invalid_schema"}, "schema"),
    ):
        if set(codes) & names:
            category = label
            break
    # These fixed labels are hints, not evidence of zero usage or account health.
    if category == "provider_exit" and re.search(
        r"(?i)\b429\b|rate limit exceeded|usage limit", "\n".join(hints)
    ):
        category = "rate_limit"
    elif category == "provider_exit" and re.search(
        r"(?i)401 unauthorized|authentication failed", "\n".join(hints)
    ):
        category = "authentication"
    elif category == "provider_exit" and re.search(
        r"(?i)stream disconnected|connection (?:refused|reset)|error sending request",
        "\n".join(hints),
    ):
        category = "network"
    if transport_error in {"timeout", "cancelled", "stream_limit"}:
        category = transport_error
    if unsafe:
        category = "unsafe_tool"
    return safe_diagnostic(
        {
            "category": category,
            "exit_code": exit_code,
            "error_events": errors,
            "unsafe_tool_event": unsafe,
        }
    )


def receipt_from_events(stdout, elapsed_ms, audited, status):
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    completed = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict) and event.get("type") == "turn.completed":
                completed.append(event.get("usage"))
        except ValueError:
            continue
    usage = None
    if len(completed) == 1 and isinstance(completed[0], dict):
        raw = completed[0]
        if all(
            type(raw.get(k)) is int and 0 <= raw[k] <= 10**9
            for k in ("input_tokens", "output_tokens")
        ):
            cached = raw.get("cached_input_tokens", 0)
            if type(cached) is int and 0 <= cached <= raw["input_tokens"]:
                usage = {k: raw[k] for k in ("input_tokens", "output_tokens")}
                usage["cached_input_tokens"] = cached
    return {"usage": usage, "elapsed_ms": elapsed_ms, "tools_audited": audited, "status": status}


class AuditedProvider(LocalCodexProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_receipt = None
        self.cancel_check = lambda: False
        self._events = ""
        self._stderr = ""
        self._exit_code = None
        self._transport_error = None

    def _run(self, args, prompt):
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            env=self.environment,
        )
        started = time.monotonic()
        out = bytearray()
        err = bytearray()
        overflow = threading.Event()

        def collect(stream, buffer, limit):
            while chunk := stream.read(65536):
                remaining = max(0, limit - len(buffer))
                buffer.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()

        def send():
            try:
                process.stdin.write(prompt.encode())
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        threads = [
            threading.Thread(target=collect, args=(process.stdout, out, 1024 * 1024), daemon=True),
            threading.Thread(target=collect, args=(process.stderr, err, 65536), daemon=True),
            threading.Thread(target=send, daemon=True),
        ]
        for thread in threads:
            thread.start()
        try:
            while process.poll() is None:
                if overflow.is_set():
                    self._transport_error = "stream_limit"
                    raise RuntimeError("CaseCouncil provider stream limit")
                if self.cancel_check():
                    self._transport_error = "cancelled"
                    raise RuntimeError("CaseCouncil call cancelled")
                if time.monotonic() - started >= self.timeout_seconds:
                    self._transport_error = "timeout"
                    raise subprocess.TimeoutExpired(args, self.timeout_seconds)
                time.sleep(0.1)
            for thread in threads:
                thread.join(timeout=1)
            if overflow.is_set():
                self._transport_error = "stream_limit"
                raise RuntimeError("CaseCouncil provider stream limit")
            return subprocess.CompletedProcess(
                args, process.returncode, out.decode(errors="replace"), err.decode(errors="replace")
            )
        finally:
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
            for thread in threads:
                thread.join(timeout=1)
            self._events = out.decode(errors="replace")
            self._stderr = err.decode(errors="replace")
            self._exit_code = process.returncode
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream and not stream.closed:
                    stream.close()

    def generate(self, *, prompt, schema):
        self._events = ""
        self._stderr = ""
        self._exit_code = None
        self._transport_error = None
        self.last_receipt = None
        started = time.monotonic()
        audited = False
        status = "interrupted_unknown"
        try:
            result = super().generate(prompt=prompt, schema=schema)
            audited = result.tools_audited
            status = "returned" if not result.exit_code else "provider_exit"
            return result
        finally:
            self.last_receipt = receipt_from_events(
                self._events, int((time.monotonic() - started) * 1000), audited, status
            )
            self.last_receipt["diagnostic"] = failure_diagnostic(
                self._events, self._exit_code, self._stderr, self._transport_error
            )
            if not audited and self.last_receipt["diagnostic"]["category"] == "ok":
                self.last_receipt["diagnostic"]["category"] = "runtime_error"
            self._events = ""
            self._stderr = ""


def provider_from_env():
    disabled = (
        "shell_tool",
        "apps",
        "multi_agent",
        "hooks",
        "memories",
        "plugins",
        "browser_use",
        "computer_use",
        "image_generation",
        "in_app_browser",
        "in_app_local_automation",
        "goals",
        "view_image",
    )
    overrides = tuple(f"features.{name}=false" for name in disabled) + (
        "features.code_mode.enabled=false",
        'web_search="disabled"',
        "mcp_servers={}",
    )
    allowed = {
        "PATH",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "TMPDIR",
        "CODEX_HOME",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
    }
    return AuditedProvider(
        command=os.environ.get("CASECOUNCIL_CODEX_COMMAND", "codex"),
        timeout_seconds=90,
        max_output_bytes=100 * 1024,
        isolated=True,
        config_overrides=overrides,
        environment={k: v for k, v in os.environ.items() if k.upper() in allowed},
    )
