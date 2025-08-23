from kante.types import Info
import strawberry
from facade.persist_backend import persist_backend




@strawberry.input(description="Input parameters for reinitializing an agent or assignation")
class ReInitInput:
    agent: strawberry.ID | None = strawberry.field(
        default=None, description="Optional agent ID to reinitialize. If not provided, reinitializes all systems."
    )


async def reinit(info: Info, input: ReInitInput) -> str:
    await persist_backend.on_reinit(agent_id=input.agent)

    return "ok"
