from kante.types import Info
from facade import types, models, inputs, enums, managers
import uuid
import strawberry


def materialize_blok(info: Info, input: inputs.MaterializeBlokInput) -> types.MaterializedBlok:
    mblok, _ = models.MaterializedBlok.objects.update_or_create(
        blok_id=input.blok,
    )

    mapped_deps = {}

    if input.dashboard:
        dashboard = models.Dashboard.objects.get(id=input.dashboard)
        models.DashboardPlacement.objects.create(dashboard=dashboard, blok=mblok)

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


def delete_materialized_blok(info: Info, input: inputs.DeleteMaterializedBlokInput) -> bool:
    try:
        mblok = models.MaterializedBlok.objects.get(id=input.id)
        mblok.delete()
        return True
    except models.MaterializedBlok.DoesNotExist:
        return False


def update_materialized_blok(info: Info, input: inputs.UpdateMaterializedBlokInput) -> types.MaterializedBlok:
    try:
        mblok = models.MaterializedBlok.objects.get(id=input.id)
    except models.MaterializedBlok.DoesNotExist:
        raise ValueError(f"MaterializedBlok with id {input.id} does not exist.")

    if input.agent_mappings is not None:
        mapped_deps = {}
        for dep in input.agent_mappings:
            mapped_deps[dep.key] = dep.agent

        for dep in models.BlokDependency.objects.filter(blok_id=mblok.blok_id):
            if dep.key in mapped_deps:
                models.BlokAgentMapping.objects.update_or_create(
                    materialized_blok=mblok,
                    dependency=dep,
                    defaults=dict(
                        agent=mapped_deps[dep.key],
                    ),
                )
            else:
                raise ValueError("Not all dependencies were met with the provided agent mappings. Update failed.")

    mblok.save()
    return mblok
