"""Cooperative cross-platform single-provider process lock."""

import json
import os
import signal
import subprocess
import threading
import time
from contextlib import contextmanager

from agent_core.codex_local import LocalCodexProvider


def parse_receipt(events, exit_code):
    allowed_items = {"agent_message", "reasoning", "todo_list", "plan", "error"}
    allowed_events = {
        "thread.started",
        "turn.started",
        "turn.completed",
        "item.started",
        "item.updated",
        "item.completed",
    }
    completed = []
    audited = exit_code == 0
    unsafe = False
    for line in events.splitlines():
        try:
            event = json.loads(line)
            if not isinstance(event, dict) or event.get("type") not in allowed_events:
                audited = False
                continue
            if "item" in event:
                item = event["item"]
                if not isinstance(item, dict) or item.get("type") not in allowed_items:
                    audited = False
                    unsafe = True
            if event.get("type") == "turn.completed":
                completed.append(event.get("usage"))
        except ValueError:
            audited = False
    usage = completed[0] if len(completed) == 1 and isinstance(completed[0], dict) else {}
    valid = all(
        type(usage.get(key)) is int and 0 <= usage[key] <= 10**9
        for key in ("input_tokens", "output_tokens")
    )
    cached = usage.get("cached_input_tokens", 0)
    valid = valid and type(cached) is int and 0 <= cached <= usage.get("input_tokens", -1)
    return {
        "audited": audited and valid,
        "unsafe_tool_event": unsafe,
        "input_tokens": usage["input_tokens"] if valid else None,
        "output_tokens": usage["output_tokens"] if valid else None,
        "cached_input_tokens": cached if valid else None,
    }


class CodexProvider(LocalCodexProvider):
    """Isolated CLI context with bounded pipes, cancellation and conservative receipts."""

    def __init__(self, command="codex", timeout_seconds=90):
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
            "unified_exec",
        )
        allowed_env = {
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
        super().__init__(
            command=command,
            timeout_seconds=min(timeout_seconds, 90),
            isolated=True,
            max_output_bytes=100 * 1024,
            config_overrides=tuple(f"features.{name}=false" for name in disabled)
            + ('web_search="disabled"', "mcp_servers={}", "features.code_mode.enabled=false"),
            environment={
                key: value for key, value in os.environ.items() if key.upper() in allowed_env
            },
        )
        self.last_receipt = None
        self.cancel_check = lambda: False
        self._events = ""
        self._exit_code = None

    def generate(self, *, prompt, schema):
        self._events, self._exit_code, self.last_receipt = "", None, None
        try:
            generation = super().generate(prompt=prompt, schema=schema)
            receipt = parse_receipt(self._events, self._exit_code)
            if generation.exit_code or not receipt["audited"]:
                raise RuntimeError("restricted provider unavailable")
            return generation
        finally:
            self.last_receipt = parse_receipt(self._events, self._exit_code)
            self._events = ""  # Never persist raw reasoning, messages, stderr or tool payloads.

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
        out, err = bytearray(), bytearray()
        overflow = threading.Event()
        started = time.monotonic()

        def collect(stream, buffer, limit):
            try:
                while chunk := stream.read(65536):
                    remaining = max(0, limit - len(buffer))
                    buffer.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        overflow.set()
            except OSError:
                pass

        def send():
            try:
                process.stdin.write(prompt.encode())
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        threads = [
            threading.Thread(target=collect, args=(process.stdout, out, 1048576), daemon=True),
            threading.Thread(target=collect, args=(process.stderr, err, 65536), daemon=True),
            threading.Thread(target=send, daemon=True),
        ]
        for thread in threads:
            thread.start()
        try:
            while process.poll() is None:
                if overflow.is_set() or self.cancel_check():
                    raise RuntimeError("restricted provider stopped")
                if time.monotonic() - started >= self.timeout_seconds:
                    raise subprocess.TimeoutExpired(args, self.timeout_seconds)
                time.sleep(0.05)
            for thread in threads:
                thread.join(timeout=1)
            if overflow.is_set() or any(t.is_alive() for t in threads):
                raise RuntimeError("restricted provider stream incomplete")
            self._exit_code = process.returncode
            return subprocess.CompletedProcess(
                args, process.returncode, out.decode(errors="strict"), ""
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
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()


@contextmanager
def runtime_lock(root):
    with (root / "runtime.lock").open("a+b") as file:
        file.seek(0)
        if file.read(1) == b"":
            file.write(b"0")
            file.flush()
        file.seek(0)
        acquired = False
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            pass
        try:
            yield acquired
        finally:
            if acquired:
                file.seek(0)
                if os.name == "nt":
                    msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(file.fileno(), fcntl.LOCK_UN)
