from kante.types import Info
from facade import types, models, inputs, enums, managers
import uuid
import strawberry


def materialize_blok(info: Info, input: inputs.MaterializeBlokInput) -> types.MaterializedBlok:

    dashboard = models.Dashboard.objects.get(id=input.dashboard) if input.dashboard else models.Dashboard.objects.create(name="Untitled Dashboard")

    mblok, _ = models.MaterializedBlok.objects.update_or_create(
        blok_id=input.blok,
        dashboard=dashboard,
    )

    mapped_deps = {}

    if input.agent_mappings:
        for dep in input.agent_mappings:
            mapped_deps[dep.key] = dep.agent

    not_met = False

    for dep in models.BlokDependency.objects.filter(blok_id=input.blok):
        if dep.key in mapped_deps:
            models.BlokAgentMapping.objects.update_or_create(
                materialized_blok=mblok,
                dependency=dep,
                defaults=dict(
                    agent=mapped_deps[dep.key],
                ),
            )
        else:
            not_met = True

    if not_met:
        mblok.delete()
        raise ValueError("Not all dependencies were met with the provided agent mappings. Materialization failed.")

    return mblok
