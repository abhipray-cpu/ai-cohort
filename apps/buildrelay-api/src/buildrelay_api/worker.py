"""One host worker: durable workflow, independent queue ingress, missed-event repair."""

import asyncio
import os
import signal
import threading

from agent_core.codex_local import LocalCodexProvider

from .github import GitHub
from .queue import resilient_listen
from .reconcile import reconcile_all
from .store import Store
from .workflow import Workflow


def provider_from_env():
    names = (
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
    overrides = tuple(f"features.{name}=false" for name in names) + (
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
    return LocalCodexProvider(
        command=os.environ.get("BUILDRELAY_CODEX_COMMAND", "codex"),
        timeout_seconds=90,
        max_output_bytes=100000,
        isolated=True,
        config_overrides=overrides,
        environment={k: v for k, v in os.environ.items() if k.upper() in allowed},
    )


async def serve(stop):
    store = Store(os.environ.get("BUILDRELAY_DATA_DIR", "var/buildrelay"))
    github = GitHub()
    workflow = Workflow(store, github, provider_from_env())
    queue_task = asyncio.create_task(resilient_listen(store, stop))

    async def repair():
        while not stop.is_set():
            try:
                await asyncio.to_thread(reconcile_all, store, github)
            except Exception:  # noqa: BLE001 -- isolate repair faults from ingress/workflow
                store.beat("reconciliation", "failed")
            else:
                store.beat("reconciliation")
            for _ in range(30):
                if stop.is_set():
                    break
                await asyncio.sleep(1)

    repair_task = asyncio.create_task(repair())
    try:
        while not stop.is_set():
            worked = await asyncio.to_thread(workflow.once)
            if not worked:
                await asyncio.sleep(1)
    finally:
        queue_task.cancel()
        repair_task.cancel()
        await asyncio.gather(queue_task, repair_task, return_exceptions=True)
        github.client.close()


def main():
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    asyncio.run(serve(stop))


if __name__ == "__main__":
    main()
