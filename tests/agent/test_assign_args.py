"""Assignment arguments are validated against the action's ports before a task is created."""

import pytest
from asgiref.sync import sync_to_async

from facade import inputs
from facade.backend import controll_backend
from facade.models import Task
from tests.agent.helpers import open_agent
from tests.factories import build_implementation_for_agent


class _Info:
    def __init__(self, context):
        self.context = context


PORTS = [
    {"key": "n", "kind": "INT", "nullable": False},
    {"key": "label", "kind": "STRING", "nullable": True},
    {"key": "scale", "kind": "FLOAT", "nullable": False, "default": 1.0},
]


@sync_to_async
def _with_ports(implementation):
    implementation.action.args = PORTS
    implementation.action.save(update_fields=["args"])
    return implementation


async def _assign(context, impl_pk, args):
    model = inputs.AssignInputModel(implementation=str(impl_pk), args=args)
    return await sync_to_async(controll_backend.assign)(_Info(context), model)


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAssignArgs:
    async def test_args_that_fit_the_ports_create_a_task(self, agent_ws, authenticated_context) -> None:
        """Args that fit the ports create a task."""
        session = await open_agent(agent_ws, "args-ok")
        impl = await _with_ports(await build_implementation_for_agent(session.agent.pk, "args-ok"))

        task = await _assign(authenticated_context, impl.pk, {"n": 3, "label": None})

        assert await sync_to_async(Task.objects.filter(pk=task.pk).exists)()

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            ({"n": "3"}, "Argument n: expected an INT, got str"),
            ({"label": "x"}, "Argument 'n' is required and has no default"),
            ({"n": 3, "zzz": 1}, "Unknown arguments ['zzz']"),
        ],
    )
    async def test_args_that_do_not_fit_are_rejected_before_any_task_exists(self, agent_ws, authenticated_context, args: dict, message: str) -> None:
        """Args that do not fit are rejected before any task exists."""
        session = await open_agent(agent_ws, "args-bad")
        impl = await _with_ports(await build_implementation_for_agent(session.agent.pk, "args-bad"))

        with pytest.raises(ValueError) as excinfo:
            await _assign(authenticated_context, impl.pk, args)

        assert message in str(excinfo.value)
        assert await sync_to_async(Task.objects.filter(implementation=impl).count)() == 0
