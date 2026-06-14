from kante.types import Info
from facade import types, models, inputs, unique
import logging
import jsonpatch
import strawberry


logger = logging.getLogger(__name__)


def log_patches(info: Info, input: inputs.LogPatchesInput) -> strawberry.ID:
    model = input.to_pydantic()

    registry, _ = models.Registry.objects.get_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
        organization=info.context.request.organization,
    )

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        defaults=dict(
            name=f"{str(registry.pk)}",
        ),
    )

    gotten_states = {}
    gotten_assignations = {}

    for patch in model.patches:
        if patch.state_name not in gotten_states:
            state = models.State.objects.get(interface=patch.state_name, agent=agent, state_schema__name=patch.state_name)
            gotten_states[patch.state_name] = state

        if patch.correlation_id and patch.correlation_id not in gotten_assignations:
            assignation = models.Assignation.objects.get(id=patch.correlation_id)
            gotten_assignations[patch.correlation_id] = assignation

        state = gotten_states[patch.state_name]

        if patch.correlation_id:
            assignation = gotten_assignations[patch.correlation_id]
        else:
            assignation = None

        models.Patch.objects.create(
            state=state,
            path=patch.path,
            global_current_revision=patch.global_current_rev,
            global_future_revision=patch.global_future_rev,
            current_revision=patch.current_rev,
            future_revision=patch.future_rev,
            session_id=patch.session_id,
            assignation=assignation,
        )


def log_snapshot(info: Info, input: inputs.LogSnapshotInput) -> strawberry.ID:
    model = input.to_pydantic()

    registry, _ = models.Registry.objects.get_or_create(
        client=info.context.request.client,
        user=info.context.request.user,
        organization=info.context.request.organization,
    )

    agent, _ = models.Agent.objects.get_or_create(
        registry=registry,
        defaults=dict(
            name=f"{str(registry.pk)}",
        ),
    )

    gotten_states = {}
    gotten_assignations = {}

    for patch in model.patches:
        if patch.state_name not in gotten_states:
            state = models.State.objects.get(interface=patch.state_name, agent=agent, state_schema__name=patch.state_name)
            gotten_states[patch.state_name] = state

        if patch.correlation_id and patch.correlation_id not in gotten_assignations:
            assignation = models.Assignation.objects.get(id=patch.correlation_id)
            gotten_assignations[patch.correlation_id] = assignation

        state = gotten_states[patch.state_name]

        if patch.correlation_id:
            assignation = gotten_assignations[patch.correlation_id]
        else:
            assignation = None

        models.Patch.objects.create(
            state=state,
            patch=patch.path,
            global_current_revision=patch.global_current_rev,
            global_future_revision=patch.global_future_rev,
            current_revision=patch.current_rev,
            future_revision=patch.future_rev,
            session_id=patch.session_id,
            assignation=assignation,
        )
