"""The Probe id space.

Task ids are integer AutoField PKs, so a ``p-`` prefixed hex uuid can never collide with
them — everywhere an id crosses the protocol (Assign/event messages, JWT ``tsk`` claims,
GraphQL IDs) a cheap prefix check decides Task vs Probe.
"""

from __future__ import annotations

import uuid

PROBE_ID_PREFIX = "p-"


def new_probe_id() -> str:
    return PROBE_ID_PREFIX + uuid.uuid4().hex


def is_probe_id(value: object) -> bool:
    return isinstance(value, str) and value.startswith(PROBE_ID_PREFIX)
