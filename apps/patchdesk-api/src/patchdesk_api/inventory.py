"""Read recorded npm identities/graphs. Never install or execute project code."""

import posixpath
import re
from urllib.parse import urlsplit

from semantic_version import NpmSpec, Version

from patchdesk_api.common import digest

NAME = re.compile(r"^(?:@[A-Za-z0-9_.~-]+/)?[A-Za-z0-9_.~-]+$")


def matches(version, spec):
    try:
        normalized = re.sub(r"([<>=~^]+)\s+", r"\1", spec.replace(",", " "))
        # semantic_version 2.10 computes the wrong tilde upper bound when the
        # target has a prerelease. Expand exactly this npm form explicitly.
        normalized = re.sub(
            r"~(\d+)\.(\d+)\.(\d+)-([0-9A-Za-z.-]+)(?:\+[0-9A-Za-z.-]+)?",
            lambda m: f">={m[1]}.{m[2]}.{m[3]}-{m[4]} <{m[1]}.{int(m[2]) + 1}.0",
            normalized,
        )
        normalized = " ".join(normalized.split())
        return NpmSpec(normalized).match(Version(version.lstrip("v")))
    except (ValueError, TypeError, AttributeError):
        return None


def osv_match(advisory, name, version):
    if advisory.get("withdrawn"):
        return None
    answers = []
    for affected in advisory.get("affected", []):
        if (
            affected.get("package", {}).get("ecosystem") != "npm"
            or affected["package"].get("name") != name
        ):
            continue
        if version in affected.get("versions", []):
            return True
        for span in affected.get("ranges", []):
            if span.get("type") != "SEMVER":
                answers.append(None)
                continue
            try:
                current = Version(version)
                active = False
                hit = False
                for event in span["events"]:
                    if "introduced" in event:
                        active = event["introduced"] == "0" or current >= Version(
                            event["introduced"]
                        )
                    elif "fixed" in event:
                        hit |= active and current < Version(event["fixed"])
                        active = False
                    elif "last_affected" in event:
                        hit |= active and current <= Version(event["last_affected"])
                        active = False
                    elif "limit" in event:
                        hit |= active and current < Version(event["limit"])
                        active = False
                    else:
                        raise ValueError("Unknown event")
                answers.append(bool(hit or active))
            except (ValueError, TypeError, KeyError):
                answers.append(None)
        if affected.get("versions") and not affected.get("ranges"):
            answers.append(False)
    return True if True in answers else None if not answers or None in answers else False


def parse_inventory(manifest, lock):
    if lock.get("lockfileVersion") not in (2, 3) or not isinstance(lock.get("packages"), dict):
        raise ValueError("Supported input is package-lock v2/v3 with packages")
    entries = lock["packages"]
    if len(entries) > 5000:
        raise ValueError("Inventory location limit is 5000")
    gaps, packages, edges = [], [], []
    linked_names = {
        item.get("resolved"): location.rsplit("node_modules/", 1)[-1]
        for location, item in entries.items()
        if isinstance(item, dict) and item.get("link") and "node_modules/" in location
    }
    root = entries.get("", {})
    for field in ("dependencies", "devDependencies", "optionalDependencies"):
        if manifest.get(field, {}) != root.get(field, {}):
            gaps.append(f"manifest_lock_mismatch:{field}")
    for location, item in sorted(entries.items()):
        if not location:
            continue
        if (
            location.startswith("/")
            or "\\" in location
            or ".." in location.split("/")
            or posixpath.normpath(location) != location
        ):
            raise ValueError("Invalid package location")
        if not isinstance(item, dict):
            raise ValueError("Malformed package entry")  # noqa: TRY004 - invalid input artifact
        if item.get("link"):
            target = item.get("resolved", "")
            if target not in entries or target.startswith("/") or ".." in target.split("/"):
                gaps.append(f"unsupported_link:{location}")
            continue
        tail = location.rsplit("node_modules/", 1)[-1]
        name = item.get("name", linked_names.get(location, tail))
        version = str(item.get("version", ""))
        if not NAME.fullmatch(name):
            gaps.append(f"unsupported_name:{location}")
            continue
        source_type = "registry_unspecified"
        resolved = str(item.get("resolved", ""))
        if resolved:
            parsed = urlsplit(resolved)
            source_type = (
                "public_registry"
                if parsed.scheme == "https"
                and parsed.hostname == "registry.npmjs.org"
                and not parsed.username
                and not parsed.password
                else "private_or_unknown"
            )
        if matches(version, "*") is None:
            source_type = "private_or_unknown"
            gaps.append(f"unsupported_version:{location}")
        if source_type == "private_or_unknown":
            gaps.append(f"private_or_unknown_source:{location}")
        packages.append(
            {
                "id": digest([location, name, version])[:24],
                "name": name,
                "version": version,
                "location": location,
                "source_type": source_type,
                "dev": bool(item.get("dev")),
                "optional": bool(item.get("optional")),
                "peers": item.get("peerDependencies", {}),
                "engines": item.get("engines", {}),
                "declared": manifest.get("dependencies", {}).get(
                    tail, manifest.get("devDependencies", {}).get(tail, "")
                )
                if location == "node_modules/" + tail
                else "",
            }
        )
    known = {p["location"]: p for p in packages}
    links = {
        location: item.get("resolved") for location, item in entries.items() if item.get("link")
    }

    def resolve(path):
        visited = set()
        while path in links and path not in visited:
            visited.add(path)
            path = links[path]
        return path if path in known else None

    for location, item in sorted(entries.items()):
        if item.get("link"):
            continue
        declarations = {**item.get("dependencies", {}), **item.get("optionalDependencies", {})}
        if location == "":
            declarations.update(manifest.get("devDependencies", {}))
        for name, constraint in sorted(declarations.items()):
            parts = location.split("/") if location else []
            candidates = [
                "/".join(parts[:i] + ["node_modules", name]) for i in range(len(parts), -1, -1)
            ]
            target = next((resolve(path) for path in candidates if resolve(path)), None)
            if target:
                edges.append(
                    {"from": location, "to": target, "name": name, "constraint": constraint}
                )
            elif location == "" or location in known:
                gaps.append(f"unresolved_edge:{location}:{name}")
    for edge in edges:
        spec = edge["constraint"]
        if spec.startswith("npm:"):
            spec = spec.rsplit("@", 1)[-1]
        if matches(known[edge["to"]]["version"], spec) is not True:
            gaps.append(f"constraint_unknown_or_mismatch:{edge['from']}:{edge['name']}")
    return {
        "packages": packages,
        "edges": edges,
        "gaps": sorted(set(gaps)),
        "coverage": "partial" if gaps else "complete_for_supported_input",
        "entry_count": len(entries),
        "sha256": digest([manifest, lock]),
        "parser_version": "patchdesk-inventory-3",
    }
