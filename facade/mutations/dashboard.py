from kante.types import Info
import strawberry
from facade import types, models, inputs
import logging

logger = logging.getLogger(__name__)


def create_dashboard(info: Info, input: inputs.CreateDashboardInput) -> types.Dashboard:
    dashboard = models.Dashboard.objects.create(
        name=input.name,
    )

    return dashboard


def delete_dashboard(info: Info, input: inputs.DeleteDashboardInput) -> bool:
    try:
        dashboard = models.Dashboard.objects.get(id=input.id)
        dashboard.delete()
        return True
    except models.Dashboard.DoesNotExist:
        logger.warning(f"Dashboard with id {input.id} does not exist.")
        return False


def update_dashboard(info: Info, input: inputs.UpdateDashboardInput) -> types.Dashboard:
    try:
        dashboard = models.Dashboard.objects.get(id=input.id)
    except models.Dashboard.DoesNotExist:
        logger.warning(f"Dashboard with id {input.id} does not exist.")
        raise ValueError(f"Dashboard with id {input.id} does not exist.")

    if input.name is not None:
        dashboard.name = input.name
    if input.organization is not None:
        dashboard.organization = input.organization
    if input.bloks is not None:
        for placement in dashboard.placements.all():
            placement.delete()

        for blok_id in input.bloks:
            blok = models.MaterializedBlok.objects.get(id=blok_id)
            placement = models.DashboardPlacement.objects.create(dashboard=dashboard, blok=blok)

    dashboard.save()

    return dashboard
