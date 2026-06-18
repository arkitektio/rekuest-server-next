"""Human-vs-service classification for the root-is-always-a-human invariant.

The auth token has no built-in human/service flag, so classification is a
configurable predicate over roles. We read roles from two sources depending on
what is available at mint time:

- the **live auth token** (``JWTToken.roles``) for the principal making the
  current request, and
- the persisted **``Membership.roles``** (the roles a user holds within an
  organization, captured from the token at login) when we only have a stored
  ``Caller`` — e.g. classifying the root of a sub-assignment tree.

If no ``human_roles`` are configured the predicate returns ``True`` (lenient):
the invariant is opt-in so dispatch keeps working until an operator declares
which role marks a human.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from django.conf import settings

logger = logging.getLogger(__name__)


def _human_roles() -> list[str]:
    return settings.PROVENANCE["HUMAN_ROLES"]


def is_human_by_roles(roles: Iterable[str] | None) -> bool:
    """True if ``roles`` mark an accountable human (or enforcement is disabled)."""
    human_roles = _human_roles()
    if not human_roles:
        return True
    if not roles:
        return False
    return bool(set(roles) & set(human_roles))


def roles_for_caller(caller: Any) -> list[str]:
    """Resolve the persisted roles a caller's user holds within its organization."""
    from authentikate import models as auth_models

    if caller is None or caller.user_id is None:
        return []

    qs = auth_models.Membership.objects.filter(user_id=caller.user_id)
    if caller.organization_id is not None:
        qs = qs.filter(organization_id=caller.organization_id)

    roles: list[str] = []
    for membership in qs:
        roles.extend(membership.roles or [])
    return roles


def is_human_caller(caller: Any) -> bool:
    """Classify a persisted ``Caller`` as a human principal."""
    # Short-circuit before any DB lookup when enforcement is disabled.
    if not _human_roles():
        return True
    return is_human_by_roles(roles_for_caller(caller))
