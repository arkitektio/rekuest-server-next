from datetime import datetime, timedelta, timezone
import uuid
from random import choice
from typing import Dict, List, Protocol, Any

from facade import enums, inputs, models, types, messages
from facade.consumers.async_consumer import AgentConsumer
from facade.higher_order import build_lower_args, build_lower_dependencies
from kante.types import Info
from authentikate.vars import get_user, get_client
import logging


class ControllBackend(Protocol):
    def create_message_id(self) -> str: ...

    def interrupt(self, info: Info, input: inputs.InterruptInputModel) -> types.Assignation: ...

    def reserve(self, info: Info, input: inputs.ReserveInputModel) -> types.Reservation: ...

    def cancel(self, info: Info, input: inputs.CancelInputModel) -> types.Assignation: ...

    def assign(self, info: Info, input: inputs.AssignInputModel) -> types.Assignation: ...

    def resume(self, info: Info, input: inputs.ResumeInputModel) -> types.Assignation: ...

    def pause(self, info: Info, input: inputs.PauseInputModel) -> types.Assignation: ...


def build_agent_dependency_dict(agent: models.Agent, dep: models.Dependency) -> Dict[str, Any]:
    implementations: Dict[str, str] = {}

    for action in dep.get_action_demands():
        try:
            implementation = models.Implementation.objects.get(action__key=action.key, agent=agent)
        except models.Implementation.DoesNotExist:
            raise ValueError(f"No implementation found for dependency demand {action} on agent {agent}")

        if implementation.dependencies.exists():
            raise NotImplementedError("Nested dependencies are not supported yet, but they are coming soon!")

        implementations[action.key] = {"implementation": str(implementation.pk), "dependencies": {}}

    return {
        "agent": str(agent.pk),
        "actions": implementations,
    }


def build_dependency_dict(implementation: models.Implementation, info: Info, dependency_overwrites: List[inputs.ResolvedDependencyInputModel]) -> Dict[str, str]:
    dependencies = models.Dependency.objects.filter(implementation=implementation).all()

    dep_kwargs = {}

    for dep in dependencies:
        provided = dep.key in [overwrite.key for overwrite in dependency_overwrites]
        if provided:
            overwrite = next(overwrite for overwrite in dependency_overwrites if overwrite.key == dep.key)

            if overwrite.auto_resolve:
                if not dep.auto_resolvable:
                    raise ValueError(f"Dependency {dep.key} is not auto resolvable, but was provided with an overwrite that has auto_resolve set to true. Please either set auto_resolve to false for this dependency overwrite, or make the dependency auto resolvable in the system.")

                agents = models.Agent.objects.filter(app__identifier=dep.app_filter, connected=True, last_seen__gt=datetime.now(timezone.utc) - timedelta(minutes=1), organization=info.context.request.organization).all()
                if dep.max_viable_instances is not None:
                    agents = agents[: dep.max_viable_instances]
                if dep.min_viable_instances is not None and len(agents) < dep.min_viable_instances:
                    raise ValueError(f"Not enough agents found for dependency {dep.key}. Required at least {dep.min_viable_instances} but found only {len(agents)}. Please ensure that there are enough agents available to resolve this dependency.")

            else:
                agents = models.Agent.objects.filter(pk__in=[agent_id.agent for agent_id in overwrite.mapped_agents], connected=True, last_seen__gt=datetime.now(timezone.utc) - timedelta(minutes=1)).all()
                if dep.max_viable_instances is not None:
                    agents = agents[: dep.max_viable_instances]
                if dep.min_viable_instances is not None and len(agents) < dep.min_viable_instances:
                    raise ValueError(f"Not enough agents found for dependency {dep.key}. Required at least {dep.min_viable_instances} but found only {len(agents)}. Please ensure that there are enough agents available to resolve this dependency.")

            dep_kwargs[dep.key] = [build_agent_dependency_dict(agent, dep) for agent in agents]
            continue
        else:
            if dep.auto_resolvable:
                agents = models.Agent.objects.filter(app__identifier=dep.app_filter, connected=True, last_seen__gt=datetime.now(timezone.utc) - timedelta(minutes=1), organization=info.context.request.organization).all()
                if dep.max_viable_instances is not None:
                    agents = agents[: dep.max_viable_instances]
                if dep.min_viable_instances is not None and len(agents) < dep.min_viable_instances:
                    raise ValueError(f"Not enough agents found for dependency {dep.key}. Required at least {dep.min_viable_instances} but found only {len(agents)}. Please ensure that there are enough agents available to resolve this dependency.")
                dep_kwargs[dep.key] = [build_agent_dependency_dict(agent, dep) for agent in agents]
            else:
                raise ValueError(f"Dependency {dep.key} was not provided with an overwrite, and is not auto resolvable. Please provide a dependency overwrite for this dependency to ensure it can be resolved properly.")

    return dep_kwargs


def get_caller_for_context(info: Info) -> models.Caller:
    caller, _ = models.Caller.objects.get_or_create(client=info.context.request.client, user=info.context.request.user, organization=info.context.request.organization)
    return caller


# TODO: Implement this for nested structures and interfaces as well
def acted_on_from_args(args: dict, action: models.Action) -> list[str]:
    acted_on = []
    for port in action.args:
        if port["kind"] == "STRUCTURE":
            identifier = port.get("identifier")
            key = port.get("key")

            if identifier and key in args:
                if isinstance(args[key], dict):
                    acted_on.append(f"{identifier}:{args[key].get('object')}")
                if isinstance(args[key], str):
                    acted_on.append(f"{identifier}:{args[key]}")

    return acted_on


class RedisControllBackend(ControllBackend):
    def create_message_id(self) -> str:
        return str(uuid.uuid4())

    def interrupt(self, input: inputs.InterruptInputModel) -> models.Assignation:
        parent = models.Assignation.objects.get(id=input.assignation)
        parent.latest_instruct_kind = enums.AssignationInstructKind.INTERRUPT
        parent.save()

        AgentConsumer.broadcast(
            parent.implementation.agent.id,
            messages.Interrupt(
                assignation=parent.id,
            ),
        )

        children = models.Assignation.objects.filter(parent_id=input.assignation).all()

        for child in children:
            child.latest_instruct_kind = enums.AssignationInstructKind.INTERRUPT
            child.save()

            AgentConsumer.broadcast(
                child.implementation.agent.id,
                messages.Interrupt(
                    assignation=child.id,
                ),
            )

        return parent

    def reserve(self, info: Info, input: inputs.ReserveInputModel) -> models.Reservation:
        if input.action is None and input.implementation is None:
            raise ValueError("Either action or implementation must be provided")

        if input.implementation:
            # We provided a implementation and are creating a reservation with just that
            # implementation
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            implementations = [implementation]
        if input.action:
            # We provided a action and are creating a reservation with all implementations
            # for that action at this time
            action = models.Action.objects.get(id=input.action)
            implementations = models.Implementation.objects.filter(action=action).all()
            if len(implementations) == 0:
                raise ValueError("No implementations found for this action. Cannot reserve.")

        caller = get_caller_for_context(info)

        res, created = models.Reservation.objects.update_or_create(
            reference=input.reference,
            caller=caller,
            defaults=dict(
                title=input.title,
                binds=input.binds.dict() if input.binds else None,
                causing_assignation_id=input.assignation_id,
                action=action,
                strategy=enums.ReservationStrategy.ROUND_ROBIN,
            ),
        )

        # TODO: Find really the best fitting provision

        res.implementations.set(implementations)

        # TODO: Cache the reservation in the redis cache and make it available for the assignation

        return res

    def cancel(self, input: inputs.CancelInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.latest_event_kind = enums.AssignationStatus.CANCELLED
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=str(assignation.id),
            ),
        )

        # Forward cancellation to child assignations — e.g. the lower assignation a
        # higher-order wrapper delegated to, which runs the real work on another agent.
        for child in models.Assignation.objects.filter(parent_id=assignation.id, is_done=False):
            AgentConsumer.broadcast(
                child.agent.id,
                message=messages.Cancel(
                    assignation=str(child.id),
                ),
            )

        return assignation

    def assign(self, info: Info, input: inputs.AssignInputModel) -> models.Assignation:
        # TODO: Check if function is cached and was

        reservation = None
        action = None
        implementation = None
        resolution = None
        agent = None
        dependency_dict = None

        caller = get_caller_for_context(info)

        if input.dependency:
            assert input.method, "Method key must be provided when assigning to a dependency"
            assert input.parent, "Dependency assignments must have a parent assignation"

            parent = models.Assignation.objects.get(id=input.parent)
            dependencies = parent.dependencies

            if input.dependency not in dependencies:
                raise ValueError(f"Dependency {input.dependency} not found in parent assignation dependencies. {parent.dependencies}")

            agent_dependency = dependencies[input.dependency]

            # Choose random agent
            chosen_agent = choice(agent_dependency)

            if "actions" not in chosen_agent:
                raise ValueError(f"Dependency {input.dependency} does not contain an action")

            if input.method not in chosen_agent["actions"]:
                raise ValueError(f"Method {input.method} not found in dependency {input.dependency} actions")

            implementation_dep = chosen_agent["actions"][input.method]

            implementation_id = implementation_dep["implementation"]
            dependency_dict = implementation_dep["dependencies"]

            implementation = models.Implementation.objects.get(id=implementation_id)
            action = implementation.action
            action = implementation.action
            agent = implementation.agent

        elif input.reservation:
            # TODO: Retrieve the reservation in the redis cache wth the provision keys set
            # this should be done in the redis cache to allow for super fast retrieval,
            # especially when using the ephemeral flag
            reservation = models.Reservation.objects.prefetch_related("provisions").get(id=input.reservation)
            action = reservation.action
            implementation = choice(reservation.implementations.all())
            if not implementation:
                raise ValueError("No implementation matchable for this reservation")
            agent = implementation.agent

        elif input.action:
            reservation = None
            action = models.Action.objects.get(id=input.action)
            implementation = models.Implementation.objects.filter(action=action, agent__connected=True, agent__last_seen__gt=datetime.now(timezone.utc) - timedelta(minutes=1)).first()
            if not implementation:
                raise ValueError(f"No active implementation found for action {action.name}")

            agent = implementation.agent

        elif input.implementation:
            reservation = None
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            agent = implementation.agent
            # A higher-order implementation is virtual — its own agent need not be connected;
            # only the resolved lower agent matters (checked in ``_assign_higher_order``).
            if implementation.higher_order_for_id is None:
                assert agent.connected, "Agent is not connected"
                assert agent.last_seen, "Agent last seen time is not set"
                assert agent.last_seen > datetime.now(timezone.utc) - timedelta(minutes=1), "Agent is not connected"

        elif input.action_hash:
            reservation = None
            action = models.Action.objects.get(hash=input.action_hash, organization=info.context.request.organization)
            implementation = models.Implementation.objects.filter(action=action, agent__connected=True).first()
            if not implementation:
                raise ValueError(f"No active implementation found for action {action.name}")
            agent = implementation.agent

        elif input.implementation:
            reservation = None
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            agent = implementation.agent

        else:
            raise ValueError("You need to provide either, action_hash or action_id, to create an assignment for an agent")

        if not action:
            raise ValueError("Could not determine action for this assignation")

        # Higher-order implementations are orchestrated server-side: the wrapper assignation
        # is virtual and a child assignation runs the resolved lower implementation.
        if implementation is not None and implementation.higher_order_for_id is not None:
            return self._assign_higher_order(info, input, implementation, caller)

        acted_on = acted_on_from_args(input.args, action)

        reference = input.reference or self.create_message_id()
        if dependency_dict is None:
            dependency_dict = build_dependency_dict(implementation, info, input.dependencies or [])

        # TODO: if ephemeral is set, we should not store the assignation in the database
        assignation = models.Assignation.objects.create(
            reservation=reservation,
            action=action,
            args=input.args,
            reference=reference,
            parent_id=input.parent,
            agent=agent,
            acted_on=acted_on,
            capture=input.capture if input.capture is not None else False,
            implementation=implementation,
            dependency=input.dependency,
            dependency_method=input.method,
            resolution=resolution,
            is_done=False,
            latest_event_kind=enums.AssignationEventKind.ASSIGN,
            latest_instruct_kind=enums.AssignationInstructKind.ASSIGN,
            hooks=input.hooks or [],
            dependencies=dependency_dict,
            caller=caller,
            ephemeral=input.ephemeral if input.ephemeral is not None else False,
        )

        action = implementation.action

        AgentConsumer.broadcast(
            assignation.agent.pk,
            message=messages.Assign(
                assignation=str(assignation.pk),
                args=input.args,
                user=str(info.context.request.user.sub),
                app=str(info.context.request.client.client_id),
                org=str(info.context.request.organization.slug) if info.context.request.organization else None,
                reference=reference,
                capture=input.capture if input.capture is not None else False,
                resolution=str(resolution.pk) if resolution else None,
                interface=implementation.interface,
                action=str(implementation.action.hash),
            ),
        )
        if input.hooks:
            for hook in input.hooks:
                if hook.kind == enums.HookKind.INIT:
                    # recursive assign
                    self.assign(
                        info,
                        inputs.AssignInputModel(
                            action_hash=hook.hash,
                            parent=assignation.pk,
                            args={"assignation": assignation.pk},
                            reference="init_hook_0",
                        ),
                    )

        return assignation

    def _assign_higher_order(self, info: Info, input: inputs.AssignInputModel, higher: models.Implementation, caller: models.Caller) -> models.Assignation:
        """Orchestrate a higher-order assignation: remap args/deps, run a child on the lower agent.

        The wrapper (``higher``) assignation is virtual — it is never broadcast to an agent.
        A child assignation runs the resolved lower implementation; its yields/done are unfolded
        back onto the wrapper in ``persist_backend`` (see the higher-order return path).
        """
        config = higher.higher_order_config or {}
        lower = higher.higher_order_for
        lower_action = lower.action

        # MVP: no nesting. A wrapper may not wrap another wrapper.
        if lower.higher_order_for_id is not None:
            raise ValueError("Nested higher-order implementations are not supported yet")

        # Resolve a connected agent implementing the lower action (cross-agent resolution).
        lower_impl = models.Implementation.objects.filter(
            action=lower_action,
            agent__connected=True,
            agent__last_seen__gt=datetime.now(timezone.utc) - timedelta(minutes=1),
        ).first()
        if not lower_impl:
            raise ValueError(f"No active implementation found for lower action {lower_action.name}")
        lower_agent = lower_impl.agent

        # Resolve the wrapper's declared dependencies from the caller, then project both the
        # args and the dependencies onto the lower implementation.
        higher_dependencies = build_dependency_dict(higher, info, input.dependencies or [])
        lower_args = build_lower_args(config, input.args)
        lower_dependencies = build_lower_dependencies(config, higher_dependencies)

        reference = input.reference or self.create_message_id()

        # The user-facing wrapper assignation — created but NOT broadcast.
        higher_assignation = models.Assignation.objects.create(
            action=higher.action,
            args=input.args,
            reference=reference,
            parent_id=input.parent,
            agent=higher.agent,
            acted_on=acted_on_from_args(input.args, higher.action),
            capture=input.capture if input.capture is not None else False,
            implementation=higher,
            is_done=False,
            latest_event_kind=enums.AssignationEventKind.ASSIGN,
            latest_instruct_kind=enums.AssignationInstructKind.ASSIGN,
            hooks=input.hooks or [],
            dependencies=higher_dependencies,
            caller=caller,
            ephemeral=input.ephemeral if input.ephemeral is not None else False,
        )

        # The child assignation that actually runs on the resolved lower agent.
        lower_assignation = models.Assignation.objects.create(
            action=lower_action,
            args=lower_args,
            reference=self.create_message_id(),
            parent=higher_assignation,
            root=higher_assignation.root or higher_assignation,
            agent=lower_agent,
            acted_on=acted_on_from_args(lower_args, lower_action),
            capture=False,
            implementation=lower_impl,
            is_done=False,
            latest_event_kind=enums.AssignationEventKind.ASSIGN,
            latest_instruct_kind=enums.AssignationInstructKind.ASSIGN,
            dependencies=lower_dependencies,
            caller=caller,
        )

        AgentConsumer.broadcast(
            lower_agent.pk,
            message=messages.Assign(
                assignation=str(lower_assignation.pk),
                args=lower_args,
                user=str(info.context.request.user.sub),
                app=str(info.context.request.client.client_id),
                org=str(info.context.request.organization.slug) if info.context.request.organization else None,
                reference=lower_assignation.reference,
                capture=False,
                resolution=None,
                interface=lower_impl.interface,
                action=str(lower_action.hash),
            ),
        )

        return higher_assignation

    def resume(self, info: Info, input: inputs.ResumeInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.latest_instruct_kind = enums.AssignationInstructKind.RESUME
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.id,
            message=messages.Cancel(
                assignation=assignation.id,
            ),
        )
        return assignation

    def bounce(self, info: Info, input: inputs.BounceInputModel) -> models.Agent:
        agent = models.Agent.objects.get(id=input.agent)

        AgentConsumer.broadcast(
            agent.id,
            message=messages.Bounce(
                agent=agent.id,
            ),
        )
        return agent

    def block(self, info: Info, input: inputs.BlockInputModel) -> models.Agent:
        agent = models.Agent.objects.get(id=input.agent)
        agent.blocked = True
        agent.save()

        AgentConsumer.broadcast(
            agent.id,
            message=messages.Kick(
                agent=agent.id,
                reason=input.reason,
            ),
        )
        return agent

    def unblock(self, info: Info, input: inputs.UnblockInputModel) -> models.Agent:
        agent = models.Agent.objects.get(id=input.agent)
        agent.blocked = False
        agent.save()

        return agent

    def kick(self, info: Info, input: inputs.KickInputModel) -> models.Agent:
        agent = models.Agent.objects.get(id=input.agent)

        AgentConsumer.broadcast(
            agent.id,
            message=messages.Kick(
                agent=agent.id,
            ),
        )
        return agent

    def collect(self, info: Info, input: inputs.CollectInputModel) -> list[str]:
        agents = {}

        drawers = models.MemoryDrawer.objects.filter(id__in=input.drawers).prefetch_related("shelve__agent").all()

        for drawer in drawers:
            if drawer.shelve.agent.pk not in agents:
                agents[drawer.shelve.agent.pk] = set()
            agents[drawer.shelve.agent.pk].add(str(drawer.pk))

        for agent_id, drawers in agents.items():
            agent = models.Agent.objects.get(id=agent_id)
            logging.info(f"collecting {drawers} from agent {agent_id}")
            AgentConsumer.broadcast(
                agent.pk,
                message=messages.Collect(
                    drawers=list(drawers),
                ),
            )

        return input.drawers

    def step(self, info: Info, input: inputs.StepInputModel) -> models.Assignation:
        assignation = models.Assignation.objects.get(id=input.assignation)
        assignation.latest_instruct_kind = enums.AssignationInstructKind.STEP
        assignation.save()

        AgentConsumer.broadcast(
            assignation.agent.pk,
            message=messages.Cancel(
                assignation=assignation.pk,
            ),
        )
        return assignation


controll_backend = RedisControllBackend()
