"""Derive a provenance audience from an action's ports.

The token's ``aud`` is scoped to the downstream service(s) an implementation
touches. This is resolved **once, at implementation registration time**, by
inspecting the action's arg + return ports for structure identifiers (e.g.
``@mikro/image`` → ``mikro``) and persisted on ``Implementation.provenance_audience``
— so dispatch never has to recompute it. An implementation may instead declare its
audience explicitly at registration, in which case derivation is skipped.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional


def service_from_identifier(identifier: str) -> Optional[str]:
    """Extract the owning service from a structure identifier like ``@mikro/image``."""
    s = (identifier or "").strip()
    if not s:
        return None
    if s.startswith("@"):
        s = s[1:]
    if "/" in s:
        s = s.split("/", 1)[0]
    return s or None


def _collect_identifiers(ports: Iterable[Any], acc: List[str]) -> None:
    """Recursively collect structure identifiers from a port tree."""
    for port in ports or []:
        if not isinstance(port, dict):
            continue
        identifier = port.get("identifier")
        if identifier:
            acc.append(identifier)
        children = port.get("children")
        if children:
            _collect_identifiers(children, acc)


def services_from_ports(*port_lists: Iterable[Any]) -> List[str]:
    """The de-duplicated set of services referenced by the given port lists."""
    identifiers: List[str] = []
    for ports in port_lists:
        _collect_identifiers(ports, identifiers)

    services: List[str] = []
    for identifier in identifiers:
        service = service_from_identifier(identifier)
        if service and service not in services:
            services.append(service)
    return services


def derive_from_action(action: Any) -> List[str]:
    """Derive the audience for an action from its arg + return structure ports."""
    return services_from_ports(action.args or [], action.returns or [])
