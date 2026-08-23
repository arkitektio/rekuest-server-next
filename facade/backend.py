import uuid
from random import choice
from typing import Dict, List, Any

from django.db.models import Q

from facade import enums, inputs, liveness, models, types, messages
from facade.caller_context import CallerContext
from facade.consumers.async_consumer import AgentConsumer
from facade.higher_order import build_lower_args, build_lower_dependencies
from facade.provenance import mint_token_for_task
from facade.provenance.canonical import args_hash
from kante.types import Info
import logging


def agent_available_q(prefix: str = "agent") -> Q:
    """Q matching an agent that can receive work: a live WEBSOCKET, OR any WEBHOOK HookAgent.

    HookAgents never set ``connected``/``last_seen`` (no socket), so they would otherwise be
    invisible to action/dependency resolution — this predicate makes them selectable. Liveness
    uses the unified ``facade.liveness`` window shared with the reconnect gate and reaper.
    """
    p = f"{prefix}__" if prefix else ""
    return Q(**{f"{p}kind": enums.AgentKind.WEBHOOK.value}) | liveness.live_agent_q(prefix)


def agent_is_available(agent: models.Agent) -> bool:
    """Whether a concrete agent can receive work (a live websocket or a webhook agent)."""
    if agent.kind == enums.AgentKind.WEBHOOK.value:
        return True
    return liveness.agent_is_live(agent.connected, agent.last_seen)


def _resolve_dependency_agents(dep: models.Dependency, ctx: CallerContext, dependency_overwrites: List[inputs.ResolvedDependencyInputModel]) -> List[models.Agent]:
    """The FULL set of available agents matching one dependency (before min/max checks)."""
    overwrite = next((o for o in dependency_overwrites if o.key == dep.key), None)

    if overwrite is not None:
        if overwrite.auto_resolve:
            if not dep.auto_resolvable:
                raise ValueError(f"Dependency {dep.key} is not auto resolvable, but was provided with an overwrite that has auto_resolve set to true. Please either set auto_resolve to false for this dependency overwrite, or make the dependency auto resolvable in the system.")
            return list(models.Agent.objects.filter(app__identifier=dep.app_filter, organization=ctx.organization).filter(agent_available_q("")))
        return list(models.Agent.objects.filter(pk__in=[mapped.agent for mapped in overwrite.mapped_agents]).filter(agent_available_q("")))

    if dep.auto_resolvable:
        return list(models.Agent.objects.filter(app__identifier=dep.app_filter, organization=ctx.organization).filter(agent_available_q("")))

    raise ValueError(f"Dependency {dep.key} was not provided with an overwrite, and is not auto resolvable. Please provide a dependency overwrite for this dependency to ensure it can be resolved properly.")


def _build_dependency_entries(dep: models.Dependency, agents: List[models.Agent]) -> List[Dict[str, Any]]:
    """The per-agent implementation maps for one dependency — batched.

    Only action demands map to callable implementations here; the dependency's state
    demands are agent-SELECTION criteria (enforced in logic.auto_resolve and the agent
    filter) and have no per-call representation. One query resolves every (agent ×
    action-demand) implementation, with a nested-dependency EXISTS annotation — replacing
    the historic 2 queries per pair.
    """
    from django.db.models import Exists, OuterRef

    action_dependencies = dep.get_action_dependencies()
    # The demand's app/key identify the target action; the slot key is only the
    # caller-facing name and doubles as the action key when the demand doesn't pin one.
    action_keys = {(ad.demand.key if ad.demand else None) or ad.key: ad for ad in action_dependencies}

    by_agent_and_key: Dict[tuple, models.Implementation] = {}
    if agents and action_keys:
        implementations = (
            models.Implementation.objects.filter(agent__in=agents, action__key__in=action_keys.keys())
            .select_related("action")
            .annotate(has_nested_dependencies=Exists(models.Dependency.objects.filter(implementation=OuterRef("pk"))))
        )
        for implementation in implementations:
            by_agent_and_key[(implementation.agent_id, implementation.action.key)] = implementation

    entries = []
    for agent in agents:
        implementations_map: Dict[str, Any] = {}
        for action_key, action_dependency in action_keys.items():
            implementation = by_agent_and_key.get((agent.pk, action_key))
            if implementation is None:
                raise ValueError(f"No implementation found for dependency demand {action_dependency} on agent {agent}")
            if implementation.has_nested_dependencies:
                raise NotImplementedError("Nested dependencies are not supported yet, but they are coming soon!")
            implementations_map[action_dependency.key] = {"implementation": str(implementation.pk), "dependencies": {}}
        entries.append({"agent": str(agent.pk), "actions": implementations_map})
    return entries


def build_dependency_dict(implementation: models.Implementation, ctx: CallerContext, dependency_overwrites: List[inputs.ResolvedDependencyInputModel]) -> Dict[str, str]:
    dep_kwargs = {}

    for dep in models.Dependency.objects.filter(implementation=implementation):
        agents = _resolve_dependency_agents(dep, ctx, dependency_overwrites)
        # Count the FULL match set BEFORE truncating to max — the historic order sliced
        # first, so min could never trip past max and was checked against a capped count.
        if dep.min_viable_instances is not None and len(agents) < dep.min_viable_instances:
            raise ValueError(f"Not enough agents found for dependency {dep.key}. Required at least {dep.min_viable_instances} but found only {len(agents)}. Please ensure that there are enough agents available to resolve this dependency.")
        if dep.max_viable_instances is not None:
            agents = agents[: dep.max_viable_instances]
        dep_kwargs[dep.key] = _build_dependency_entries(dep, agents)

    return dep_kwargs


def get_caller_for_context(ctx: CallerContext) -> models.Caller:
    caller, _ = models.Caller.objects.get_or_create(client=ctx.client, user=ctx.user, organization=ctx.organization)
    return caller


def resolve_direct_target(
    *,
    action_id: str | None,
    implementation_id: str | None,
    action_hash: str | None,
    organization,
    agent_id: str | None = None,
    interface: str | None = None,
) -> tuple[models.Action, models.Implementation, models.Agent]:
    """Resolve ``(action, implementation, agent)`` from one of the direct target forms.

    Shared by the Task ``assign`` path and the ephemeral call path (the dependency-slot
    form stays assign-only — it requires a parent task). Precedence mirrors the historic
    assign branches: action → implementation → action_hash → agent+interface.
    """
    if action_id:
        action = models.Action.objects.get(id=action_id)
        implementation = models.Implementation.objects.filter(action=action).filter(agent_available_q("agent")).first()
        if not implementation:
            raise ValueError(f"No active implementation found for action {action.name}")
        return action, implementation, implementation.agent

    if implementation_id:
        implementation = models.Implementation.objects.get(id=implementation_id)
        agent = implementation.agent
        # A higher-order wrapper is virtual; its agent (== the lower implementation's
        # agent, by the co-location rule) is connectivity-checked in ``_assign_higher_order``,
        # which raises a ValueError. Skip the assert here so that path owns the check.
        if implementation.higher_order_for_id is None:
            assert agent_is_available(agent), "Agent is not available (not connected, and not a webhook agent)"
        return implementation.action, implementation, agent

    if action_hash:
        action = models.Action.objects.get(hash=action_hash, organization=organization)
        implementation = models.Implementation.objects.filter(action=action).filter(agent_available_q("agent")).first()
        if not implementation:
            raise ValueError(f"No active implementation found for action {action.name}")
        return action, implementation, implementation.agent

    if agent_id and interface:
        # Direct addressing: the caller knows exactly which peer implementation it wants.
        implementation = models.Implementation.objects.get(agent_id=agent_id, interface=interface)
        agent = implementation.agent
        if implementation.higher_order_for_id is None:
            assert agent_is_available(agent), "Agent is not available (not connected, and not a webhook agent)"
        return implementation.action, implementation, agent

    raise ValueError("You need to provide an action, action_hash, implementation, or agent+interface to create an assignment for an agent")


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
    """The postman backend: resolves + persists tasks, then notifies via transport."""

    def create_message_id(self) -> str:
        return str(uuid.uuid4())

    def _request_control(
        self,
        task_id,
        *,
        instruct_kind,
        inging_kind,
        to_agent_factory,
        propagate_children: bool = False,
        caller: models.Caller | None = None,
    ) -> models.Task:
        """The shared request phase of a two-phase lifecycle op.

        Sets ``latest_instruct_kind``, persists the ``-ING`` event (which fans out the matching
        ``Caller*ing`` mirror to the caller) and a ``TaskInstruct`` audit row (who requested
        the control, when), and broadcasts the ToAgent control message — for the target, and
        (when ``propagate_children``) for every still-running descendant. The op resolves only
        when the executing agent sends the matching confirmation event. Raises if the task is
        already terminal.
        """
        task = models.Task.objects.select_related("agent").get(id=task_id)
        if task.is_done:
            raise ValueError("Task is already terminal")

        targets = [task]
        if propagate_children:
            targets += list(models.Task.objects.filter(root_id=task.id, is_done=False).select_related("agent"))

        for target in targets:
            target.latest_instruct_kind = instruct_kind
            target.save(update_fields=["latest_instruct_kind"])
            models.TaskEvent.objects.create(task=target, kind=inging_kind)
            models.TaskInstruct.objects.create(task=target, kind=instruct_kind, caller=caller)
            AgentConsumer.broadcast(target.agent, to_agent_factory(str(target.pk)))

        return task

    def cancel(self, input: inputs.CancelInputModel, caller: models.Caller | None = None) -> models.Task:
        # Two-phase: CANCELING now; CANCELLED + is_done only when the agent confirms with
        # CancelledEvent. Sent to the mother only (the actor winds down its own children).
        return self._request_control(
            input.task,
            instruct_kind=enums.TaskInstructKind.CANCEL,
            inging_kind=enums.TaskEventKind.CANCELLING,
            to_agent_factory=lambda a: messages.Cancel(task=a),
            caller=caller,
        )

    def interrupt(self, input: inputs.InterruptInputModel, caller: models.Caller | None = None) -> models.Task:
        # Forceful: propagates Interrupt to all still-running descendants. Still two-phase —
        # each reaches INTERRUPTED only on its agent's Interrupted report.
        return self._request_control(
            input.task,
            instruct_kind=enums.TaskInstructKind.INTERRUPT,
            inging_kind=enums.TaskEventKind.INTERRUPTING,
            to_agent_factory=lambda a: messages.Interrupt(task=a),
            propagate_children=True,
            caller=caller,
        )

    def pause(self, input: inputs.PauseInputModel, caller: models.Caller | None = None) -> models.Task:
        return self._request_control(
            input.task,
            instruct_kind=enums.TaskInstructKind.PAUSE,
            inging_kind=enums.TaskEventKind.PAUSING,
            to_agent_factory=lambda a: messages.Pause(task=a),
            caller=caller,
        )

    def assign(self, principal: "CallerContext | Any", input: inputs.AssignInputModel) -> models.Task:
        ctx = CallerContext.coerce(principal)
        # Replay/reuse of prior results is the orchestrator's decision: tasks carry an
        # indexed ``args_hash`` and the ``reusable_task_for`` query surfaces prior completed
        # pure runs — the server never short-circuits an assign itself.

        # ``org`` is a required field on the Assign message — fail loudly here rather than
        # crashing on ``None.slug`` further down (also covers the higher-order path).
        if ctx.organization is None:
            raise ValueError("Cannot assign without an organization")

        action = None
        implementation = None
        # The half-built Resolutions feature: rows are created by auto_resolve/create_resolution;
        # linking one to a task was never wired — do so when the caller passes it.
        resolution = models.Resolution.objects.get(id=input.resolution) if input.resolution else None
        agent = None
        dependency_dict = None

        caller = get_caller_for_context(ctx)

        # Idempotency on the caller-supplied reference: a resend returns the existing task
        # (no re-broadcast, no new events) — mirroring the agent-socket path's dedupe in
        # ``_caller_assign_sync``. Server-generated references are fresh per call, so only a
        # provided reference dedupes. Placed before target resolution: a hit skips it all.
        if input.reference is not None:
            existing = models.Task.objects.filter(caller=caller, reference=input.reference).first()
            if existing is not None:
                return existing

        if input.dependency:
            assert input.method, "Method key must be provided when assigning to a dependency"
            assert input.parent, "Dependency assignments must have a parent task"

            parent = models.Task.objects.get(id=input.parent)
            dependencies = parent.dependencies

            if input.dependency not in dependencies:
                raise ValueError(f"Dependency {input.dependency} not found in parent task dependencies. {parent.dependencies}")

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
            agent = implementation.agent

        else:
            action, implementation, agent = resolve_direct_target(
                action_id=input.action,
                implementation_id=input.implementation,
                action_hash=input.action_hash,
                organization=ctx.organization,
                agent_id=input.agent,
                interface=input.interface,
            )

        if not action:
            raise ValueError("Could not determine action for this task")

        # Root propagation: a child's root is its parent's root (or the parent itself when
        # the parent IS the root). Interrupt's descendant propagation, the root-scoped
        # change feeds and ``my_tasks`` all filter on ``root_id`` — it must be complete.
        root_id = None
        if input.parent:
            parent_root_id, parent_pk = models.Task.objects.values_list("root_id", "id").get(pk=input.parent)
            root_id = parent_root_id or parent_pk

        # Higher-order implementations are orchestrated server-side: the wrapper task
        # is virtual and a child task runs the resolved lower implementation.
        if implementation is not None and implementation.higher_order_for_id is not None:
            return self._assign_higher_order(ctx, input, implementation, caller, root_id=root_id)

        acted_on = acted_on_from_args(input.args, action)

        reference = input.reference or self.create_message_id()
        if dependency_dict is None:
            dependency_dict = build_dependency_dict(implementation, ctx, input.dependencies or [])

        task = models.Task.objects.create(
            action=action,
            args=input.args,
            args_hash=args_hash(input.args or {}),
            reference=reference,
            parent_id=input.parent,
            root_id=root_id,
            agent=agent,
            acted_on=acted_on,
            capture=input.capture if input.capture is not None else False,
            implementation=implementation,
            dependency=input.dependency,
            dependency_method=input.method,
            resolution=resolution,
            is_done=False,
            # QUEUED until the agent confirms with Started — creation is not execution.
            latest_event_kind=enums.TaskEventKind.QUEUED,
            latest_instruct_kind=enums.TaskInstructKind.ASSIGN,
            hooks=[h.model_dump() for h in (input.hooks or [])],
            dependencies=dependency_dict,
            caller=caller,
        )

        action = implementation.action

        token = mint_token_for_task(task, ctx)

        AgentConsumer.broadcast(
            agent,
            message=messages.Assign(
                task=str(task.pk),
                args=input.args,
                user=str(ctx.user.sub),
                org=str(ctx.organization.slug),
                parent=str(input.parent) if input.parent else None,
                root=str(root_id) if root_id else None,
                step=input.step,
                reference=reference,
                capture=input.capture if input.capture is not None else False,
                resolution=str(resolution.pk) if resolution else None,
                interface=implementation.interface,
                action=str(implementation.action.hash),
                implementation=str(implementation.pk),
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
                            parent=str(task.pk),
                            args={"task": str(task.pk)},
                            # Scoped to the parent: a constant reference would now dedupe
                            # (caller, reference)-wise across unrelated tasks' hooks.
                            reference=f"init_hook_0_{task.pk}",
                        ),
                    )

        return task

    def _assign_higher_order(self, ctx: CallerContext, input: inputs.AssignInputModel, higher: models.Implementation, caller: models.Caller, root_id: int | None = None) -> models.Task:
        """Orchestrate a higher-order task: remap args/deps, run a child on the lower agent.

        The wrapper (``higher``) task is virtual — it is never broadcast to an agent.
        A child task runs the resolved lower implementation; its yields/done are unfolded
        back onto the wrapper in ``persist_backend`` (see the higher-order return path).
        """
        # Reached only via ``assign``, which already guarded that an organization exists.
        assert ctx.organization is not None, "Cannot assign without an organization"

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

        # The user-facing wrapper task — created but NOT broadcast.
        higher_task = models.Task.objects.create(
            action=higher.action,
            args=input.args,
            args_hash=args_hash(input.args or {}),
            reference=reference,
            parent_id=input.parent,
            root_id=root_id,
            agent=higher.agent,
            acted_on=acted_on_from_args(input.args, higher.action),
            capture=input.capture if input.capture is not None else False,
            implementation=higher,
            is_done=False,
            latest_event_kind=enums.TaskEventKind.QUEUED,
            latest_instruct_kind=enums.TaskInstructKind.ASSIGN,
            hooks=[h.model_dump() for h in (input.hooks or [])],
            dependencies=higher_dependencies,
            caller=caller,
        )

        # The child task that actually runs on the resolved lower agent.
        lower_task = models.Task.objects.create(
            action=lower_action,
            args=lower_args,
            args_hash=args_hash(lower_args or {}),
            reference=self.create_message_id(),
            parent=higher_task,
            root=higher_task.root or higher_task,
            is_higher_order_child=True,
            agent=lower_agent,
            acted_on=acted_on_from_args(lower_args, lower_action),
            capture=False,
            implementation=lower_impl,
            is_done=False,
            latest_event_kind=enums.TaskEventKind.QUEUED,
            latest_instruct_kind=enums.TaskInstructKind.ASSIGN,
            dependencies=lower_dependencies,
            caller=caller,
        )

        token = mint_token_for_task(lower_task, ctx)

        AgentConsumer.broadcast(
            lower_agent,
            message=messages.Assign(
                task=str(lower_task.pk),
                args=lower_args,
                user=str(ctx.user.sub),
                org=str(ctx.organization.slug),
                parent=str(higher_task.pk),
                root=str(lower_task.root_id) if lower_task.root_id else None,
                step=input.step,
                reference=lower_task.reference,
                capture=False,
                resolution=None,
                interface=lower_impl.interface,
                action=str(lower_action.hash),
                implementation=str(lower_impl.pk),
                token=token,
            ),
        )

        return higher_task

    def resume(self, input: inputs.ResumeInputModel, caller: models.Caller | None = None) -> models.Task:
        return self._request_control(
            input.task,
            instruct_kind=enums.TaskInstructKind.RESUME,
            inging_kind=enums.TaskEventKind.RESUMING,
            to_agent_factory=lambda a: messages.Resume(task=a, step=input.step),
            caller=caller,
        )

    def bounce(self, info: Info, input: inputs.BounceInputModel) -> models.Agent:
        agent = models.Agent.objects.get(id=input.agent)

        AgentConsumer.broadcast(
            agent,
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
            agent,
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
            agent,
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
                agent,
                message=messages.Collect(
                    drawers=list(drawers),
                ),
            )

        return input.drawers


controll_backend = RedisControllBackend()
