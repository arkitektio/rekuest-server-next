from sys import implementation
from kante.types import Info
from facade import types, models, inputs, enums, logic
import uuid
import strawberry


def auto_resolve(info: Info, input: inputs.AutoResolveInput) -> types.Resolution:
    implementation = models.Implementation.objects.get(id=input.implementation)
    resolution = models.Resolution.objects.create(
        name=f"Auto-resolve for {implementation.name}",
        creator=info.context.request.user,
        organization=info.context.request.organization,
        implementation=implementation,
    )

    logic.auto_resolve(info, implementation, resolution)
    return resolution


def create_resolution(info: Info, input: inputs.CreateResolutionInput) -> types.Resolution:
    cimplementation = models.Implementation.objects.get(id=input.implementation)

    resolution = models.Resolution.objects.create(
        name=input.name,
        creator=info.context.request.user,
        organization=info.context.request.organization,
        implementation=implementation,
    )

    if input.resolved_dependencies:
        for rd_input in input.resolved_dependencies:
            models.ResolvedDependency.objects.create(
                resolution=resolution,
                implementation=models.Implementation.objects.get(id=rd_input.implementation),
                key=rd_input.key,
                depedency=models.Dependency.objects.get(key=rd_input.key, implementation=cimplementation),
                resolution_key=rd_input.resolution_key,
            )

    return resolution


def update_resolution(info: Info, input: inputs.UpdateResolutionInput) -> types.Resolution:
    resolution = models.Resolution.objects.get(id=input.id)

    if input.name:
        resolution.name = input.name
        resolution.save()

    if input.resolved_dependencies is not None:
        resolution.resolved_dependencies.all().delete()

        for rd_input in input.resolved_dependencies:
            models.ResolvedDependency.objects.update_or_create(
                resolution=resolution,
                resolution_key=rd_input.resolution_key,
                defaults=dict(
                    dependency=models.Dependency.objects.get(key=rd_input.key, implementation=resolution.implementation),
                    key=rd_input.key,
                    implementation=models.Implementation.objects.get(id=rd_input.implementation),
                    resolution_key=rd_input.resolution_key,
                ),
            )

    return resolution


def delete_resolution(info: Info, input: inputs.DeleteResolutionInput) -> strawberry.ID:
    resolution = models.Resolution.objects.get(id=input.id)
    resolution.delete()

    return input.id
