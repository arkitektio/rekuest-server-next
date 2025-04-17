from kante.types import Info
import strawberry_django
import strawberry
from facade.persist_backend import persist_backend




@strawberry.input
class ReInitInput:
    agent: strawberry.ID | None = None


async def reinit(info: Info, input: ReInitInput) -> str:
    await persist_backend.on_reinit(agent_id=input.agent)

    return "ok"
