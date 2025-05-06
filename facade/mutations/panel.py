from kante.types import Info
from facade import types, models, inputs, enums
import uuid


def create_panel(info: Info, input: inputs.CreatePanelInput) -> types.Panel:
    state = None
    accesors = None
    reservation = None

    if input.kind == enums.PanelKind.STATE:
        if input.state:
            state = models.State.objects.get(state_schema_id=input.state)
            accesors = input.state_accessors

        elif input.state_key:
            registry = models.Registry.objects.get(
                app=info.context.request.app,
                user=info.context.request.user,
            )

            agent = models.Agent.objects.get(
                registry=registry,
                instance_id=input.instance_id or "default",
            )

            state_key, accesor = tuple(input.state_key.split(":"))
            accesors = accesor.split(".")

            state_schema = models.StateSchema.objects.get(name=state_key, agent=agent)

            state = state_schema.states.first()

        else:
            state = None
            accesors = None

    elif input.kind == enums.PanelKind.ASSIGN:
        if input.interface:
            registry = models.Registry.objects.get(
                app=info.context.request.app,
                user=info.context.request.user,
            )

            agent = models.Agent.objects.get(
                registry=registry,
                instance_id=input.instance_id or "default",
            )

            implementation = models.Implementation.objects.get(
                interface=input.interface, agent=agent
            )

            reservation, created = models.Reservation.objects.update_or_create(
                reference=uuid.uuid4(),
                action=implementation.action,
                implementation=implementation,
                strategy=(
                    enums.ReservationStrategy.DIRECT
                    if implementation
                    else enums.ReservationStrategy.ROUND_ROBIN
                ),
                waiter=None,
                saved_args=input.args if input.args else {},
            )

    else:
        raise Exception("Invalid kind")

    x, _ = models.Panel.objects.update_or_create(
        kind=input.kind,
        name=input.name,
        defaults=dict(
            state=state,
            accessors=accesors,
            reservation=reservation,
            submit_on_change=(
                input.submit_on_change if input.submit_on_change is not None else False
            ),
            submit_on_load=(
                input.submit_on_load if input.submit_on_load is not None else False
            ),
        ),
    )

    return x
