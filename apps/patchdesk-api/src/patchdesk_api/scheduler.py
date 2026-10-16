"""Bounded dependency-aware async scheduling; checkpoint successful siblings independently."""

import asyncio


class Scheduler:
    def __init__(self, limit=4, per_provider=2):
        if not 1 <= limit <= 4 or not 1 <= per_provider <= 2:
            raise ValueError("Unsafe concurrency configuration")
        self.limit, self.per_provider = limit, per_provider

    async def run(self, nodes, execute, save, check=lambda: None, completed=None):
        mapping = {node["id"]: node for node in nodes}
        if len(mapping) != len(nodes) or len(nodes) > 128:
            raise ValueError("Duplicate nodes or task limit")
        pending = set(mapping)
        visited = set()
        while pending:
            ready = {
                key
                for key in pending
                if set(mapping[key].get("dependencies", [])).issubset(visited)
            }
            if not ready:
                raise ValueError("Task cycle or missing dependency")
            visited |= ready
            pending -= ready
        results = dict(completed or {})
        pending = set(mapping) - results.keys()
        active = {}
        provider_counts = {}

        async def perform(node):
            try:
                return await execute(node)
            except (OSError, TimeoutError, ValueError, RuntimeError, PermissionError) as error:
                return {
                    "outcome": "denied" if isinstance(error, PermissionError) else "unavailable",
                    "completeness": "unknown",
                    "error": type(error).__name__,
                }

        try:
            while pending or active:
                check()
                for key in sorted(pending):
                    node = mapping[key]
                    deps = node.get("dependencies", [])
                    if not set(deps).issubset(results):
                        continue
                    if any(
                        results[d].get("outcome") not in ("success", "no_matches") for d in deps
                    ):
                        value = {
                            "outcome": "unsupported",
                            "completeness": "unknown",
                            "error": "Prerequisite incomplete",
                        }
                        results[key] = value
                        save(key, value)
                        pending.remove(key)
                        continue
                    provider = node.get("provider", "local")
                    if (
                        len(active) >= self.limit
                        or provider_counts.get(provider, 0) >= self.per_provider
                    ):
                        continue
                    check()
                    provider_counts[provider] = provider_counts.get(provider, 0) + 1
                    active[asyncio.create_task(perform(node))] = key
                    pending.remove(key)
                if not active:
                    if pending:
                        raise ValueError("Task graph cannot progress")
                    break
                finished, _ = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
                for task in sorted(finished, key=lambda item: active[item]):
                    key = active.pop(task)
                    provider = mapping[key].get("provider", "local")
                    provider_counts[provider] -= 1
                    results[key] = task.result()
                    save(key, results[key])
            return dict(sorted(results.items()))
        finally:
            for task in active:
                task.cancel()
            if active:
                await asyncio.gather(*active, return_exceptions=True)
