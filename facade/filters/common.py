"""Shared filter input helpers."""

from __future__ import annotations

import strawberry


@strawberry.input(description="A way to filter by scope")
class ScopeFilter:
    public: bool | None = None
    org: bool | None = None
    shared: bool | None = None
    me: bool | None = None


@strawberry.input
class ParamPair:
    key: str
    value: str
