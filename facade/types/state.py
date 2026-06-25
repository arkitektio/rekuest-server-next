"""State definitions, states, patches and snapshots."""

from __future__ import annotations

import datetime

import strawberry
import strawberry_django
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes

from facade import enums, models, scalars


@strawberry_django.type(models.StateDefinition)
class StateDefinition:
    id: strawberry.ID
    hash: str
    name: str

    @strawberry_django.field()
    def ports(self) -> list[rtypes.ReturnPort]:
        return [rtypes.ReturnPort.from_pydantic(rmodels.ReturnPortModel(**i)) for i in self.ports]


@strawberry_django.type(models.State)
class State:
    id: strawberry.ID
    definition: StateDefinition = strawberry_django.field(description="The schema definition for this state.")
    agent: Agent = strawberry_django.field(description="The agent to which this state belongs.")
    interface: str = strawberry_django.field(description="The interface this state is associated with.")
    created_at: datetime.datetime = strawberry_django.field(description="Timestamp when this state was created.")
    updated_at: datetime.datetime = strawberry_django.field(description="Timestamp when this state was last updated.")


@strawberry_django.type(models.HistoricalState)
class HistoricalState:
    id: strawberry.ID
    state: State
    value: scalars.Args
    archived_at: datetime.datetime


@strawberry.type
class JSONPatch:
    op: enums.JSONPatchOperation
    path: str
    value: scalars.Args


@strawberry.type
class StateUpdateEvent:
    state_id: str
    patches: list[JSONPatch]


@strawberry_django.type(models.Patch)
class Patch:
    id: strawberry.ID
    op: str
    path: str
    value: scalars.Args
    timestamp: datetime.datetime
    current_revision: int
    future_revision: int
    global_current_revision: int
    global_future_revision: int
    session_id: str
    task: Task | None
    state: State
    interface: str

    @strawberry.field
    def patch(self) -> JSONPatch:
        return JSONPatch(op=self.op, path=self.path, value=self.value)


@strawberry_django.type(models.Snapshot)
class Snapshot:
    id: strawberry.ID
    value: scalars.Args
    timestamp: datetime.datetime
    revision: int
    global_revision: int
    session_id: str
    state: State
