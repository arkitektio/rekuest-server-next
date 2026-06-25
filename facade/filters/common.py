"""Shared filter input helpers."""

from __future__ import annotations

import strawberry


@strawberry.input
class ParamPair:
    key: str
    value: str
