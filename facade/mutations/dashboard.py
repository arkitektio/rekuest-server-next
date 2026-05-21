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
