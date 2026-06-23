from datetime import datetime, timedelta, timezone
import uuid
from random import choice
from typing import Dict, List, Any

from django.db.models import Q

from facade import enums, inputs, models, types, messages
from facade.caller_context import CallerContext
from facade.consumers.async_consumer import AgentConsumer
from facade.higher_order import build_lower_args, build_lower_dependencies
from facade.provenance import mint_token_for_assignation
from kante.types import Info
import logging


def agent_available_q(prefix: str = "agent") -> Q:
    """Q matching an agent that can receive work: a live WEBSOCKET, OR any WEBHOOK HookAgent.

    HookAgents never set ``connected``/``last_seen`` (no socket), so they would otherwise be
    invisible to action/dependency resolution — this predicate makes them selectable.
    """
    recent = datetime.now(timezone.utc) - timedelta(minutes=1)
    p = f"{prefix}__" if prefix else ""
    return Q(**{f"{p}kind": enums.AgentKind.WEBHOOK.value}) | Q(**{f"{p}connected": True, f"{p}last_seen__gt": recent})


def agent_is_available(agent: models.Agent) -> bool:
    """Whether a concrete agent can receive work (a live websocket or a webhook agent)."""
    if agent.kind == enums.AgentKind.WEBHOOK.value:
        return True
    return bool(agent.connected and agent.last_seen and agent.last_seen > datetime.now(timezone.utc) - timedelta(minutes=1))


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


def build_dependency_dict(implementation: models.Implementation, ctx: CallerContext, dependency_overwrites: List[inputs.ResolvedDependencyInputModel]) -> Dict[str, str]:
    dependencies = models.Dependency.objects.filter(implementation=implementation).all()

    dep_kwargs = {}

    for dep in dependencies:
        provided = dep.key in [overwrite.key for overwrite in dependency_overwrites]
        if provided:
            overwrite = next(overwrite for overwrite in dependency_overwrites if overwrite.key == dep.key)

            if overwrite.auto_resolve:
                if not dep.auto_resolvable:
                    raise ValueError(f"Dependency {dep.key} is not auto resolvable, but was provided with an overwrite that has auto_resolve set to true. Please either set auto_resolve to false for this dependency overwrite, or make the dependency auto resolvable in the system.")

                agents = models.Agent.objects.filter(app__identifier=dep.app_filter, organization=ctx.organization).filter(agent_available_q("")).all()
                if dep.max_viable_instances is not None:
                    agents = agents[: dep.max_viable_instances]
                if dep.min_viable_instances is not None and len(agents) < dep.min_viable_instances:
                    raise ValueError(f"Not enough agents found for dependency {dep.key}. Required at least {dep.min_viable_instances} but found only {len(agents)}. Please ensure that there are enough agents available to resolve this dependency.")

            else:
                agents = models.Agent.objects.filter(pk__in=[agent_id.agent for agent_id in overwrite.mapped_agents]).filter(agent_available_q("")).all()
                if dep.max_viable_instances is not None:
                    agents = agents[: dep.max_viable_instances]
                if dep.min_viable_instances is not None and len(agents) < dep.min_viable_instances:
                    raise ValueError(f"Not enough agents found for dependency {dep.key}. Required at least {dep.min_viable_instances} but found only {len(agents)}. Please ensure that there are enough agents available to resolve this dependency.")

            dep_kwargs[dep.key] = [build_agent_dependency_dict(agent, dep) for agent in agents]
            continue
        else:
            if dep.auto_resolvable:
                agents = models.Agent.objects.filter(app__identifier=dep.app_filter, organization=ctx.organization).filter(agent_available_q("")).all()
                if dep.max_viable_instances is not None:
                    agents = agents[: dep.max_viable_instances]
                if dep.min_viable_instances is not None and len(agents) < dep.min_viable_instances:
                    raise ValueError(f"Not enough agents found for dependency {dep.key}. Required at least {dep.min_viable_instances} but found only {len(agents)}. Please ensure that there are enough agents available to resolve this dependency.")
                dep_kwargs[dep.key] = [build_agent_dependency_dict(agent, dep) for agent in agents]
            else:
                raise ValueError(f"Dependency {dep.key} was not provided with an overwrite, and is not auto resolvable. Please provide a dependency overwrite for this dependency to ensure it can be resolved properly.")

    return dep_kwargs


def get_caller_for_context(ctx: CallerContext) -> models.Caller:
    caller, _ = models.Caller.objects.get_or_create(client=ctx.client, user=ctx.user, organization=ctx.organization)
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


class RedisControllBackend:
    """The postman backend: resolves + persists assignations, then notifies via transport."""

    def create_message_id(self) -> str:
        return str(uuid.uuid4())

    def _request_control(
        self,
        assignation_id,
        *,
        instruct_kind,
        inging_kind,
        to_agent_factory,
        propagate_children: bool = False,
    ) -> models.Assignation:
        """The shared request phase of a two-phase lifecycle op.

        Sets ``latest_instruct_kind``, persists the ``-ING`` event (which fans out the matching
        ``Caller*ing`` mirror to the caller), and broadcasts the ToAgent control message — for
        the target, and (when ``propagate_children``) for every still-running descendant. The
        op resolves only when the executing agent sends the matching confirmation event. Raises
        if the assignation is already terminal.
        """
        ass = models.Assignation.objects.select_related("agent").get(id=assignation_id)
        if ass.is_done:
            raise ValueError("Assignation is already terminal")

        targets = [ass]
        if propagate_children:
            targets += list(models.Assignation.objects.filter(root_id=ass.id, is_done=False))

        for target in targets:
            target.latest_instruct_kind = instruct_kind
            target.save(update_fields=["latest_instruct_kind"])
            models.AssignationEvent.objects.create(assignation=target, kind=inging_kind)
            AgentConsumer.broadcast(target.agent_id, to_agent_factory(str(target.pk)))

        return ass

    def cancel(self, input: inputs.CancelInputModel) -> models.Assignation:
        # Two-phase: CANCELING now; CANCELLED + is_done only when the agent confirms with
        # CancelledEvent. Sent to the mother only (the actor winds down its own children).
        return self._request_control(
            input.assignation,
            instruct_kind=enums.AssignationInstructKind.CANCEL,
            inging_kind=enums.AssignationEventKind.CANCELING,
            to_agent_factory=lambda a: messages.Cancel(assignation=a),
        )

    def interrupt(self, input: inputs.InterruptInputModel) -> models.Assignation:
        # Forceful: propagates Interrupt to all still-running descendants. Still two-phase —
        # each reaches INTERUPTED only on its agent's InterruptedEvent.
        return self._request_control(
            input.assignation,
            instruct_kind=enums.AssignationInstructKind.INTERRUPT,
            inging_kind=enums.AssignationEventKind.INTERUPTING,
            to_agent_factory=lambda a: messages.Interrupt(assignation=a),
            propagate_children=True,
        )

    def pause(self, input: inputs.PauseInputModel) -> models.Assignation:
        return self._request_control(
            input.assignation,
            instruct_kind=enums.AssignationInstructKind.PAUSE,
            inging_kind=enums.AssignationEventKind.PAUSING,
            to_agent_factory=lambda a: messages.Pause(assignation=a),
        )

    def assign(self, principal: "CallerContext | Any", input: inputs.AssignInputModel) -> models.Assignation:
        ctx = CallerContext.coerce(principal)
        # TODO: Check if function is cached and was

        action = None
        implementation = None
        resolution = None
        agent = None
        dependency_dict = None

        caller = get_caller_for_context(ctx)

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

        elif input.action:
            action = models.Action.objects.get(id=input.action)
            implementation = models.Implementation.objects.filter(action=action).filter(agent_available_q("agent")).first()
            if not implementation:
                raise ValueError(f"No active implementation found for action {action.name}")

            agent = implementation.agent

        elif input.implementation:
            implementation = models.Implementation.objects.get(id=input.implementation)
            action = implementation.action
            agent = implementation.agent
            # A higher-order wrapper is virtual; its agent (== the lower implementation's
            # agent, by the co-location rule) is connectivity-checked in ``_assign_higher_order``,
            # which raises a ValueError. Skip the assert here so that path owns the check.
            if implementation.higher_order_for_id is None:
                assert agent_is_available(agent), "Agent is not available (not connected, and not a webhook agent)"

        elif input.action_hash:
            action = models.Action.objects.get(hash=input.action_hash, organization=ctx.organization)
            implementation = models.Implementation.objects.filter(action=action).filter(agent_available_q("agent")).first()
            if not implementation:
                raise ValueError(f"No active implementation found for action {action.name}")
            agent = implementation.agent

        elif input.implementation:
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
            return self._assign_higher_order(ctx, input, implementation, caller)

        acted_on = acted_on_from_args(input.args, action)

        reference = input.reference or self.create_message_id()
        if dependency_dict is None:
            dependency_dict = build_dependency_dict(implementation, ctx, input.dependencies or [])

        # TODO: if ephemeral is set, we should not store the assignation in the database
        assignation = models.Assignation.objects.create(
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

        token = mint_token_for_assignation(assignation, ctx)

        AgentConsumer.broadcast(
            assignation.agent.pk,
            message=messages.Assign(
                assignation=str(assignation.pk),
                args=input.args,
                user=str(ctx.user.sub),
                app=str(ctx.client.client_id),
                org=str(ctx.organization.slug) if ctx.organization else None,
                reference=reference,
                capture=input.capture if input.capture is not None else False,
                resolution=str(resolution.pk) if resolution else None,
                interface=implementation.interface,
                action=str(implementation.action.hash),
                token=token,
            ),
        )
        if input.hooks:
            for hook in input.hooks:
                if hook.kind == enums.HookKind.INIT:
                    # recursive assign
                    self.assign(
                        ctx,
                        inputs.AssignInputModel(
                            action_hash=hook.hash,
                            parent=assignation.pk,
                            args={"assignation": assignation.pk},
                            reference="init_hook_0",
                        ),
                    )

        return assignation

    def _assign_higher_order(self, ctx: CallerContext, input: inputs.AssignInputModel, higher: models.Implementation, caller: models.Caller) -> models.Assignation:
        """Orchestrate a higher-order assignation: remap args/deps, run a child on the lower agent.

        The wrapper (``higher``) assignation is virtual — it is never broadcast to an agent.
        A child assignation runs the resolved lower implementation; its yields/done are unfolded
        back onto the wrapper in ``persist_backend`` (see the higher-order return path).
        """
        config = higher.higher_order_config or {}

        # A higher-order implementation is bound to the agent that owns its lower
        # implementation (enforced at link time in ``set_higher_order``), so the wrapped
        # impl and its agent are deterministic — no cross-agent resolution needed.
        lower_impl = higher.higher_order_for
        lower_action = lower_impl.action
        lower_agent = lower_impl.agent

        # The wrapper's agent IS the executing agent — it must be available (live socket or webhook).
        if not agent_is_available(lower_agent):
            raise ValueError(f"Agent for lower implementation {lower_impl.interface} is not available")

        # Resolve the wrapper's declared dependencies from the caller, then project both the
        # args and the dependencies onto the lower implementation.
        higher_dependencies = build_dependency_dict(higher, ctx, input.dependencies or [])
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

        token = mint_token_for_assignation(lower_assignation, ctx)

        AgentConsumer.broadcast(
            lower_agent.pk,
            message=messages.Assign(
                assignation=str(lower_assignation.pk),
                args=lower_args,
                user=str(ctx.user.sub),
                app=str(ctx.client.client_id),
                org=str(ctx.organization.slug) if ctx.organization else None,
                reference=lower_assignation.reference,
                capture=False,
                resolution=None,
                interface=lower_impl.interface,
                action=str(lower_action.hash),
                token=token,
            ),
        )

        return higher_assignation

    def resume(self, input: inputs.ResumeInputModel) -> models.Assignation:
        return self._request_control(
            input.assignation,
            instruct_kind=enums.AssignationInstructKind.RESUME,
            inging_kind=enums.AssignationEventKind.RESUMING,
            to_agent_factory=lambda a: messages.Resume(assignation=a, step=input.step),
        )

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


controll_backend = RedisControllBackend()
