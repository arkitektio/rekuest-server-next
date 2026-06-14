"""Websocket protocol helpers shared by the full-stack agent tests.

The unit-only fakes (``FakeAgent`` / ``FakeBackend`` / ``make_protocol``) live in
``test_protocol_unit.py`` since only that module uses them.
"""

from facade import messages

from tests.factories import TEST_TOKEN, seed_agent

RECEIVE_TIMEOUT = 5


async def register(communicator, instance_id="test-agent", token=TEST_TOKEN, force=False):
    """Send a ``Register`` and return the parsed ``Init`` response payload.

    ``instance_id`` is kept only as a convenience label for seeding helpers; it is
    no longer part of the protocol (agents are identified solely by their registry).
    """
    await communicator.send_to(text_data=messages.Register(token=token, force=force).model_dump_json())
    return await communicator.receive_json_from(timeout=RECEIVE_TIMEOUT)


async def send_message(communicator, message):
    """Serialize a pydantic message and send it over the socket."""
    await communicator.send_to(text_data=message.model_dump_json())


async def connect_and_register(agent_ws, instance_id, **seed_kwargs):
    """Seed the agent, connect, register, and return ``(communicator, init)``."""
    await seed_agent(instance_id, **seed_kwargs)
    communicator = await agent_ws()
    init = await register(communicator, instance_id=instance_id)
    return communicator, init
