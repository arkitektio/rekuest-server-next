from kante.types import Info
import strawberry
from facade import types, models, inputs, scalars
from rekuest_core.inputs.types import StructureInput, InterfaceInput
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)


def cleanup_actions(info: Info, action_ids: list[strawberry.ID] | None = None) -> int:
    # TODO: Check that user has permission to delete actions

    if action_ids:
        # Delete specific actions by IDs
        actions_to_check = models.Action.objects.filter(id__in=action_ids, organization=info.context.request.organization)
    else:
        actions_to_check = models.Action.objects

    runreferenced_actions = actions_to_check.annotate(num_implementations=Count("implementations")).filter(num_implementations=0)

    # Delete them in bulk (efficiently)
    deleted_count, _ = runreferenced_actions.delete()

    print(f"Successfully deleted {deleted_count} unreferenced actions.")

    return deleted_count
