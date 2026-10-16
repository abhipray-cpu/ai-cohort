"""Permission/routing/concurrency invariants before their implementation."""

import asyncio
import time

import pytest
from contracts.patchdesk import CapabilityRequest, ToolDescriptor
from patchdesk_api.registry import Registry, denied
from patchdesk_api.scheduler import Scheduler


def descriptor(name="osv", provider="osv", priority=10):
    return ToolDescriptor(
        id=name, provider=provider, capabilities=["advisories.detail"], priority=priority
    )


def scope():
    return {
        "roles": ["analyst"],
        "policy": {"public_packages": ["axios"], "model_egress": False},
        "repository": "",
    }


def request():
    return CapabilityRequest(
        capability="advisories.detail", arguments={"id": "GHSA-jr5f-v2jv-69x6", "package": "axios"}
    )


def test_dynamic_registry_pinning_disable_and_routing():
    registry = Registry()
    registry.register(descriptor())
    pinned = registry.snapshot()
    registry.register(descriptor("github", "github", 5))
    assert registry.route(request(), scope())["adapter"] == "github"
    assert registry.route(request(), scope(), pinned)["adapter"] == "osv"
    registry.set_enabled("osv", False)
    with pytest.raises(PermissionError):
        registry.route(request(), scope(), pinned)
    with pytest.raises(ValueError):
        registry.register(descriptor())


def test_permission_denial_has_no_fallback():
    registry = Registry()
    registry.register(descriptor())
    registry.register(descriptor("github", "github", 5))
    context = scope()
    context["policy"]["public_packages"] = []
    assert denied(request(), context)
    with pytest.raises(PermissionError):
        registry.route(request(), context)
    context = scope()
    context["roles"] = []
    assert denied(request(), context)


def test_provider_specific_package_support_is_not_a_generic_fallback():
    registry = Registry()
    registry.register(
        ToolDescriptor(
            id="publisher",
            provider="github",
            capabilities=["advisories.detail"],
            packages=["axios"],
        )
    )
    context = scope()
    context["policy"]["public_packages"] = ["lodash"]
    with pytest.raises(PermissionError):
        registry.route(
            CapabilityRequest(
                capability="advisories.detail",
                arguments={"package": "lodash", "id": "GHSA-1111-2222-3333"},
            ),
            context,
        )


def test_scheduler_parallel_bounds_dependencies_failure_survival():
    active, peak = 0, 0
    starts, ends, saved = {}, {}, {}

    async def execute(node):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        starts[node["id"]] = time.monotonic()
        await asyncio.sleep(0.03)
        active -= 1
        ends[node["id"]] = time.monotonic()
        if node["id"] == "bad":
            raise TimeoutError("injected")
        return {"outcome": "success", "id": node["id"]}

    nodes = [
        {"id": "a", "provider": "one", "dependencies": []},
        {"id": "b", "provider": "two", "dependencies": []},
        {"id": "bad", "provider": "two", "dependencies": []},
        {"id": "c", "provider": "one", "dependencies": ["a", "b"]},
    ]
    asyncio.run(
        Scheduler(limit=2, per_provider=1).run(
            nodes, execute, lambda key, value: saved.update({key: value})
        )
    )
    assert peak == 2
    assert starts["b"] < ends["a"]
    assert starts["c"] >= max(ends["a"], ends["b"])
    assert saved["a"]["outcome"] == "success" and saved["bad"]["outcome"] == "unavailable"


def test_scheduler_rejects_cycles_and_stops_cancelled_work():
    scheduler = Scheduler()

    async def execute(_):
        raise AssertionError("should not dispatch")

    nodes = [
        {"id": "a", "provider": "p", "dependencies": ["b"]},
        {"id": "b", "provider": "p", "dependencies": ["a"]},
    ]
    with pytest.raises(ValueError, match="cycle"):
        asyncio.run(scheduler.run(nodes, execute, lambda *_: None))
    with pytest.raises(ValueError, match="cancel"):
        asyncio.run(
            scheduler.run(
                [dict(nodes[0], dependencies=[])],
                execute,
                lambda *_: None,
                check=lambda: (_ for _ in ()).throw(ValueError("cancelled")),
            )
        )
