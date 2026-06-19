"""Shared builders for the test suite.

Two groups live here:

* **Sync model builders** (``create_registry_bundle``, ``create_agent_for_registry``,
  ``create_action_for_organization``) used by the model tests.
* **Agent object-graph builders** used by the websocket tests — the async
  ``seed_agent`` (pre-creates the agent the consumer looks up for a token) plus the
  ``build_*`` helpers that assemble Action -> Implementation -> Assignation / State
  graphs. The ``build_*`` names are ``sync_to_async``-wrapped for use from async tests.
"""

from asgiref.sync import sync_to_async

from authentikate.expand import (
    aexpand_client_from_token,
    aexpand_organization_from_token,
    aexpand_user_from_token,
)
from authentikate.models import App, Client, Device, Organization, Release, User
from authentikate.utils import authenticate_token_or_none

from facade import enums
from facade.models import (
    Action,
    Agent,
    Assignation,
    Caller,
    Implementation,
    State,
    StateDefinition,
)

TEST_TOKEN = "test"


# --------------------------------------------------------------------------- #
# Sync model builders (used by the model tests)
# --------------------------------------------------------------------------- #
def create_registry_bundle(prefix: str) -> tuple[User, Client, Organization, Caller]:
    user = User.objects.create(username=f"{prefix}-user", password="testpass")
    client = Client.objects.create(client_id=f"{prefix}-client")
    org = Organization.objects.create(slug=f"{prefix}-org")
    caller = Caller.objects.create(client=client, user=user, organization=org)
    return user, client, org, caller


def create_agent_for_registry(registry: Caller, user: User, organization: Organization, prefix: str, **overrides) -> Agent:
    release = Release.objects.create(app=App.objects.create(identifier=f"{prefix}-app"), version="1.0.0")
    device = Device.objects.create(device_id=f"{prefix}-device")
    registry.client.device = device
    registry.client.save()

    agent_data = {
        "app": release.app,
        "hash": f"{prefix}-hash",
        "release": release,
        "user": user,
        "client": registry.client,
        "organization": organization,
    }
    agent_data.update(overrides)

    return Agent.objects.create(**agent_data)


def create_action_for_organization(organization: Organization, prefix: str, **overrides) -> Action:
    app = App.objects.create(identifier=f"{prefix}-app")
    action_data = {
        "app": app,
        "key": f"{prefix}-key",
        "version": "1.0.0",
        "name": f"{prefix} action",
        "description": f"{prefix} description",
        "hash": f"{prefix}-hash",
        "organization": organization,
    }
    action_data.update(overrides)

    return Action.objects.create(**action_data)


# --------------------------------------------------------------------------- #
# Agent seeding (async) — reproduces ``ensureAgent`` for the websocket tests
# --------------------------------------------------------------------------- #
async def seed_agent(instance_id, token=TEST_TOKEN, blocked=False):
    """Pre-create the agent the consumer will look up for ``token``.

    Uses the same authentikate expansion the consumer uses, so the derived
    (client, user, organization) matches and ``on_register`` finds (rather than creates) the agent.
    ``instance_id`` is only a label used to make seeded rows distinguishable.
    """
    decoded = await authenticate_token_or_none(token)
    user = await aexpand_user_from_token(decoded)
    client = await aexpand_client_from_token(decoded)
    organization = await aexpand_organization_from_token(decoded)

    app, _ = await App.objects.aget_or_create(identifier="ws-test-app")
    release, _ = await Release.objects.aget_or_create(app=app, version="1.0.0")
    device, _ = await Device.objects.aget_or_create(device_id="ws-test-device")
    client.device = device
    await client.asave()

    agent, _ = await Agent.objects.aupdate_or_create(
        client=client,
        user=user,
        organization=organization,
        defaults=dict(
            app=app, release=release,
            hash=f"{instance_id}-hash", blocked=blocked,
        ),
    )
    return agent


# --------------------------------------------------------------------------- #
# Object-graph builders (run synchronously, wrapped via sync_to_async)
# --------------------------------------------------------------------------- #
def _build_assignation(prefix):
    """Create a standalone Action -> Implementation -> Assignation graph.

    The persist backend looks assignations up by id (not by the registered agent),
    so this graph is independent of the agent that streams the events.
    """
    user = User.objects.create(username=f"{prefix}-user", password="x", sub=f"{prefix}-sub")
    device = Device.objects.create(device_id=f"{prefix}-device")
    client = Client.objects.create(client_id=f"{prefix}-client", device=device)
    org = Organization.objects.create(slug=f"{prefix}-org")
    caller = Caller.objects.create(client=client, user=user, organization=org)

    app = App.objects.create(identifier=f"{prefix}-app")
    release = Release.objects.create(app=app, version="1.0.0")
    agent = Agent.objects.create(
        app=app, hash=f"{prefix}-hash", release=release,
        user=user, client=client, organization=org,
    )

    action = Action.objects.create(
        app=app, key=f"{prefix}-key", version="1.0.0", name=f"{prefix} action",
        description=f"{prefix} description", hash=f"{prefix}-action-hash", organization=org,
    )
    implementation = Implementation.objects.create(
        release=release, interface=f"{prefix}-iface", action=action, agent=agent, dynamic=False,
    )

    return Assignation.objects.create(
        caller=caller,
        action=action,
        agent=agent,
        implementation=implementation,
        latest_event_kind=enums.AssignationEventKind.ASSIGN,
        latest_instruct_kind=enums.AssignationInstructChoices.ASSIGN,
    )


def _build_unimplemented_assignation_for_agent(agent_pk, prefix):
    """An unfinished assignation owned directly by ``agent`` with NO implementation.

    Exercises the disconnect path: such rows are found by the direct ``agent`` FK
    but would be missed by an ``implementation__agent`` filter (implementation is
    null). Guards the B1 fix in ``ModelPersistBackend.on_agent_disconnected``.
    """
    agent = Agent.objects.get(pk=agent_pk)
    app = App.objects.create(identifier=f"{prefix}-app")
    action = Action.objects.create(
        app=app, key=f"{prefix}-key", version="1.0.0", name=f"{prefix} action",
        description=f"{prefix} description", hash=f"{prefix}-action-hash", organization=agent.organization,
    )
    return Assignation.objects.create(
        caller=None,
        action=action,
        agent=agent,
        implementation=None,
        latest_event_kind=enums.AssignationEventKind.ASSIGN,
        latest_instruct_kind=enums.AssignationInstructChoices.ASSIGN,
    )


def _build_state_for_agent(agent_pk, interface, prefix):
    """Create a State (and its definition) attached to an existing agent."""
    definition = StateDefinition.objects.create(
        name=f"{prefix} state", hash=f"{prefix}-state-hash", ports=[], description=f"{prefix} state def",
    )
    return State.objects.create(definition=definition, interface=interface, agent_id=agent_pk, value={})


build_assignation = sync_to_async(_build_assignation)
build_unimplemented_assignation_for_agent = sync_to_async(_build_unimplemented_assignation_for_agent)
build_state_for_agent = sync_to_async(_build_state_for_agent)
