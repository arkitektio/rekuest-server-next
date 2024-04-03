import strawberry_django
from facade import models, scalars, enums, filters
import strawberry
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from strawberry.experimental import pydantic
from typing import Any
from typing import ForwardRef
from strawberry import LazyType
from typing import Literal, Union
from authentikate.strawberry.types import App, User
import datetime
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes
from rekuest_core import scalars as rscalars
from rekuest_core import enums as renums

@strawberry_django.type(models.Registry)
class Registry:
    id: strawberry.ID
    app: App
    user: User
    agents: list["Agent"]


@strawberry_django.type(models.Collection)
class Collection:
    id: strawberry.ID
    name: str
    nodes: list["Node"]


@strawberry_django.type(models.Protocol, filters=filters.ProtocolFilter, pagination=True, order=filters.ProtocolOrder)
class Protocol:
    id: strawberry.ID
    name: str
    nodes: list["Node"]


@strawberry_django.type(
    models.Node, filters=filters.NodeFilter, pagination=True, order=filters.NodeOrder
)
class Node:
    id: strawberry.ID
    hash: scalars.NodeHash
    name: str
    kind: renums.NodeKind
    description: str | None
    collections: list["Collection"]
    templates: list["Template"]
    scope: enums.NodeScope
    is_test_for: list["Node"]
    tests: list["Node"]
    protocols: list["Protocol"]
    defined_at: datetime.datetime

    @strawberry_django.field()
    def args(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.args]

    @strawberry_django.field()
    def returns(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.returns]
    
    @strawberry_django.field()
    def port_groups(self) -> list[rtypes.PortGroup]:
        return [rmodels.PortGroupModel(**i) for i in self.port_groups]


@strawberry_django.type(
    models.Template, filters=filters.TemplateFilter, pagination=True
)
class Template:
    id: strawberry.ID
    name: str | None
    interface: str
    agent: "Agent"
    node: "Node"
    params: rscalars.AnyDefault


@strawberry_django.type(models.Agent, filters=filters.AgentFilter, pagination=True)
class Agent:
    id: strawberry.ID
    instance_id: scalars.InstanceID
    registry: "Registry"


@strawberry_django.type(models.Waiter, filters=filters.WaiterFilter, pagination=True)
class Waiter:
    id: strawberry.ID
    instance_id: scalars.InstanceID
    registry: "Registry"


@strawberry_django.type(
    models.Provision, filters=filters.ProvisionFilter, pagination=True
)
class Provision:
    id: strawberry.ID
    name: str
    agent: "Agent"
    template: "Template"
    status: enums.ProvisionStatus


@strawberry_django.type(
    models.ProvisionEvent, filters=filters.ProvisionEventFilter, pagination=True
)
class ProvisionEvent:
    id: strawberry.ID
    provision: "Provision"
    kind: enums.ProvisionEventKind
    level: enums.LogLevel
    created_at: strawberry.auto


@strawberry_django.type(
    models.Reservation, filters=filters.ReservationFilter, pagination=True
)
class Reservation:
    id: strawberry.ID
    name: str
    waiter: "Waiter"
    title: str | None
    node: "Node"
    status: enums.ReservationStatus
    updated_at: datetime.datetime
    reference: str
    provisions: list["Provision"]
    binds: rtypes.Binds | None


@strawberry_django.type(
    models.ReservationEvent, filters=filters.ReservationEventFilter, pagination=True
)
class ReservationEvent:
    id: strawberry.ID
    reservation: "Reservation"
    kind: enums.ReservationEventKind
    level: enums.LogLevel
    created_at: strawberry.auto


@strawberry_django.type(
    models.Assignation, filters=filters.AssignationFilter, pagination=True
)
class Assignation:
    id: strawberry.ID
    name: str
    reference: str | None
    args: rscalars.AnyDefault
    parent: "Assignation"
    status: enums.AssignationStatus
    status_message: str | None
    waiter: "Waiter"
    node: "Node"
    events: list["AssignationEvent"]
    created_at: datetime.datetime
    updated_at: datetime.datetime


@strawberry_django.type(
    models.AssignationEvent, filters=filters.AssignationEventFilter, pagination=True
)
class AssignationEvent:
    id: strawberry.ID
    name: str
    returns: rscalars.AnyDefault
    assignation: "Assignation"
    kind: enums.AssignationEventKind
    level: enums.LogLevel
    created_at: strawberry.auto


@strawberry_django.type(
    models.TestCase, filters=filters.TestCaseFilter, pagination=True
)
class TestCase:
    id: strawberry.ID
    key: str
    node: "Node"
    is_benchmark: bool
    description: str
    name: str
    results: list["TestResult"]


@strawberry_django.type(
    models.TestResult, filters=filters.TestResultFilter, pagination=True
)
class TestResult:
    id: strawberry.ID
    template: "Template"
    case: "TestCase"
    passed: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
