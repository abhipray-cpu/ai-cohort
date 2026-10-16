"""Trusted, versioned capability registry; permissions are checked at routing and dispatch."""

from contracts.patchdesk import ToolDescriptor

from patchdesk_api.common import digest


def denied(request, context):
    if "analyst" not in context.get("roles", []):
        return "Investigation permission required"
    if request.capability == "repository.snapshot.read":
        return None if context.get("policy", {}).get("repository") else "Repository not configured"
    approved = set(context.get("policy", {}).get("public_packages", []))
    identities = request.arguments.get("packages", [])
    if "package" in request.arguments:
        identities = [request.arguments["package"]]
    names = [item if isinstance(item, str) else item.get("name", "") for item in identities]
    if not names or not set(names).issubset(approved):
        return "Explicit public package egress grant required"
    return None


class Registry:
    def __init__(self):
        self.adapters = {}

    def register(self, descriptor):
        descriptor = ToolDescriptor.model_validate(descriptor)
        if descriptor.id in self.adapters:
            raise ValueError("Duplicate trusted adapter ID")
        self.adapters[descriptor.id] = descriptor

    def set_enabled(self, name, enabled):
        if name not in self.adapters:
            raise ValueError("Unknown trusted adapter")
        self.adapters[name] = self.adapters[name].model_copy(update={"enabled": enabled})

    def snapshot(self):
        values = [d.model_dump() for _, d in sorted(self.adapters.items())]
        return {"revision": digest(values), "adapters": values}

    def route(self, request, context, pinned=None, excluded=(), preferred=None):
        reason = denied(request, context)
        if reason:
            raise PermissionError(reason)
        snapshot = pinned or self.snapshot()
        choices, rejected = [], []
        for data in snapshot["adapters"]:
            descriptor = ToolDescriptor.model_validate(data)
            if request.capability not in descriptor.capabilities:
                continue
            identities = request.arguments.get("packages", [])
            if "package" in request.arguments:
                identities = [request.arguments["package"]]
            names = {item if isinstance(item, str) else item.get("name", "") for item in identities}
            if descriptor.packages and (not names or not names.issubset(descriptor.packages)):
                rejected.append(
                    {"adapter": descriptor.id, "reason": "Unsupported package identity"}
                )
                continue
            live = self.adapters.get(descriptor.id)
            if (
                not live
                or not descriptor.enabled
                or not live.enabled
                or live.version != descriptor.version
                or descriptor.id in excluded
            ):
                rejected.append(
                    {
                        "adapter": descriptor.id,
                        "reason": "disabled, excluded or revision unavailable",
                    }
                )
                continue
            choices.append(descriptor)
        if not choices:
            raise PermissionError("No eligible authorized capability provider")
        selected = min(
            choices, key=lambda d: (d.id != preferred if preferred else False, d.priority, d.id)
        )
        return {
            "adapter": selected.id,
            "provider": selected.provider,
            "registry_revision": snapshot["revision"],
            "descriptor_hash": digest(selected.model_dump()),
            "reason": "Compatible enabled provider selected by configured priority and stable ID",
            "rejected": rejected,
        }


def default_registry(disabled=()):
    registry = Registry()
    for name, provider, capabilities, priority in [
        ("osv", "osv", ["advisories.lookup", "advisories.detail"], 10),
        ("github_advisory", "github", ["advisories.detail"], 20),
        ("github_publisher", "github", ["advisories.detail"], 30),
        ("npm", "npm", ["releases.lookup"], 10),
        ("epss", "first", ["threat.epss"], 10),
        ("kev", "cisa", ["threat.kev"], 10),
        ("depsdev", "depsdev", ["dependency.context"], 10),
        ("github_repository", "github", ["repository.snapshot.read"], 10),
    ]:
        registry.register(
            ToolDescriptor(
                id=name,
                provider=provider,
                packages=["axios"] if name == "github_publisher" else [],
                capabilities=capabilities,
                priority=priority,
                permission="repository" if name == "github_repository" else "public",
                enabled=name not in disabled,
            )
        )
    return registry
