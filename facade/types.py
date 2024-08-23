import datetime
from enum import Enum
from typing import Any, ForwardRef, Literal, Optional, Union

import redis
import strawberry
import strawberry_django
from authentikate.models import App
from authentikate.strawberry.types import User
from dep_graph.functions import (
    build_node_graph,
    build_reservation_graph,
    build_template_graph,
)
from dep_graph.types import DependencyGraph
from django.conf import settings
from django.utils import timezone
from facade import enums, filters, models, scalars
from facade.connection import redis_pool
from pydantic import BaseModel, Field
from rekuest_core import enums as renums
from rekuest_core import scalars as rscalars
from rekuest_core.objects import models as rmodels
from rekuest_core.objects import types as rtypes
from strawberry import LazyType
from strawberry.experimental import pydantic
from kante.types import Info
from rekuest_ui_core.objects import models as uimodels
from rekuest_ui_core.objects import types as uitypes


@strawberry_django.type(
    App, filters=filters.AppFilter, pagination=True, order=filters.AppOrder
)
class App:
    id: strawberry.ID
    name: str
    client_id: str


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


@strawberry_django.type(
    models.Protocol,
    filters=filters.ProtocolFilter,
    pagination=True,
    order=filters.ProtocolOrder,
)
class Protocol:
    id: strawberry.ID
    name: str
    nodes: list["Node"]


@strawberry_django.type(
    models.Node, filters=filters.NodeFilter, pagination=True, order=filters.NodeOrder
)
class Node:
    id: strawberry.ID
    hash: rscalars.NodeHash
    name: str
    kind: renums.NodeKind
    description: str | None
    collections: list["Collection"]
    templates: list["Template"]
    scope: enums.NodeScope
    is_test_for: list["Node"]
    is_dev: bool
    tests: list["Node"]
    protocols: list["Protocol"]
    defined_at: datetime.datetime
    reservations: list[LazyType["Reservation", __name__]] | None
    test_cases: list[LazyType["TestCase", __name__]] | None

    @strawberry_django.field()
    def dependency_graph(self) -> DependencyGraph:
        return build_node_graph(self)

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
    models.Dependency, filters=filters.DependencyFilter, pagination=True
)
class Dependency:
    id: strawberry.ID
    template: "Template"
    node: Node | None
    hash: rscalars.NodeHash
    initial_hash: rscalars.NodeHash
    reference: str | None
    optional: bool = False

    @strawberry_django.field()
    def binds(self) -> rtypes.Binds | None:
        return rmodels.BindsModel(**self.binds) if self.binds else None

    @strawberry_django.field()
    def resolvable(self, info: Info) -> bool:
        provisions = models.Provision.objects.filter(
            template__node__hash=self.initial_hash,
            provided=True,
        )

        provisions

        return provisions.exists()


@strawberry_django.type(
    models.Template, filters=filters.TemplateFilter, pagination=True
)
class Template:
    id: strawberry.ID
    name: str | None
    interface: str
    extension: str
    agent: "Agent"
    node: "Node"
    params: rscalars.AnyDefault
    dependencies: list["Dependency"]
    provisions: list["Provision"]

    @strawberry_django.field()
    def dependency_graph(self) -> DependencyGraph:
        return build_template_graph(self)


@strawberry_django.type(
    models.HardwareRecord, filters=filters.HardwareRecordFilter, pagination=True
)
class HardwareRecord:
    id: strawberry.ID
    cpu_count: int
    cpu_vendor_name: str
    cpu_frequency: float
    created_at: datetime.datetime
    agent: "Agent"


@strawberry_django.type(
    models.Agent, filters=filters.AgentFilter, order=filters.AgentOrder, pagination=True
)
class Agent:
    id: strawberry.ID
    instance_id: scalars.InstanceID
    registry: "Registry"
    status: enums.AgentStatus
    hardware_records: list[HardwareRecord]
    templates: list["Template"]
    provisions: list["Provision"]
    last_seen: datetime.datetime | None
    connected: bool
    extensions: list[str]
    name: str
    state_schemas: list["StateSchema"]

    @strawberry_django.field()
    def template(self, interface: str) -> Template | None:
        return self.templates.filter(interface=interface).first()

    @strawberry_django.field()
    def active(self) -> bool:
        return self.connected and self.last_seen > timezone.now() - datetime.timedelta(
            seconds=settings.AGENT_DISCONNECTED_TIMEOUT
        )

    @strawberry_django.field()
    def latest_hardware_record(self) -> HardwareRecord | None:
        return self.hardware_records.order_by("-created_at").first()
    
    @strawberry_django.field()
    def latest_states(self) -> list["State"]:
        states = []
        for i in self.state_schemas.all():
            first = i.states.first()
            if first:
                states.append(first)


        return states


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
    status: enums.ProvisionEventKind
    caused_reservations: list["Reservation"]
    provided: bool
    active: bool

    @strawberry_django.field()
    def dependencies_met(self) -> bool:
        return self.dependencies_met


@strawberry_django.type(
    models.ProvisionEvent, filters=filters.ProvisionEventFilter, pagination=True
)
class ProvisionEvent:
    id: strawberry.ID
    provision: "Provision"
    kind: enums.ProvisionEventKind
    level: enums.LogLevel | None
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
    status: enums.ReservationEventKind
    updated_at: datetime.datetime
    reference: str
    provisions: list["Provision"]
    binds: rtypes.Binds | None
    causing_dependency: Dependency | None
    causing_provision: Provision | None
    strategy: enums.ReservationStrategy
    viable: bool
    happy: bool
    template: Optional["Template"]

    @strawberry_django.field()
    def dependency_graph(self) -> DependencyGraph:
        return build_reservation_graph(self)

    @strawberry_django.field()
    def events(self) -> list["ReservationEvent"]:
        return self.events.order_by("created_at")[:10]


@strawberry_django.type(
    models.ReservationEvent, filters=filters.ReservationEventFilter, pagination=True
)
class ReservationEvent:
    id: strawberry.ID
    reservation: "Reservation"
    kind: enums.ReservationEventKind
    level: enums.LogLevel | None
    created_at: strawberry.auto


@strawberry_django.type(
    models.Assignation, filters=filters.AssignationFilter, pagination=True
)
class Assignation:
    id: strawberry.ID
    name: str
    reference: str | None
    args: rscalars.AnyDefault
    parent: Optional["Assignation"]
    reservation: Optional["Reservation"]
    node: "Node"
    template: Optional["Template"]
    status: enums.AssignationEventKind
    status_message: str | None
    waiter: "Waiter"
    node: "Node"
    created_at: datetime.datetime
    updated_at: datetime.datetime
    provision: Optional["Provision"]

    @strawberry_django.field()
    def events(self) -> list["AssignationEvent"]:
        return self.events.order_by("created_at")[:10]


@strawberry_django.type(
    models.AssignationEvent, filters=filters.AssignationEventFilter, pagination=True
)
class AssignationEvent:
    id: strawberry.ID
    name: str
    returns: rscalars.AnyDefault | None
    assignation: "Assignation"
    kind: enums.AssignationEventKind
    message: str | None
    level: enums.LogLevel | None
    progress: int | None

    created_at: strawberry.auto

    @strawberry_django.field()
    def level(self) -> enums.LogLevel:
        return enums.LogLevel.INFO

    @strawberry_django.field()
    def reference(self) -> str:
        return self.assignation.reference


@strawberry_django.type(
    models.TestCase, filters=filters.TestCaseFilter, pagination=True
)
class TestCase:
    id: strawberry.ID
    tester: "Node"
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
    tester: "Template"
    case: "TestCase"
    passed: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

@strawberry_django.type(
    models.Structure
)
class Structure:
    identifier: strawberry.ID
    object: strawberry.ID


@strawberry_django.type(
    models.Dashboard
)
class Dashboard:
    id: strawberry.ID
    name: str | None 
    panels: list["Panel"] | None

    @strawberry_django.field()
    def ui_tree(self) -> uitypes.UITree | None:


        model = uimodels.UITreeModel(**self.ui_tree) if self.ui_tree else None
        print(model)
        return model

@strawberry_django.type(
    models.Panel
)
class Panel:
    id: strawberry.ID
    kind: enums.PanelKind
    reservation: Reservation | None 
    state: Optional["State"]
    accessors: list[str] | None




@strawberry_django.type(
    models.StateSchema
)
class StateSchema:
    id: strawberry.ID
    agent: Agent
    name: str
   
    @strawberry_django.field()
    def ports(self) -> list[rtypes.Port]:
        return [rmodels.PortModel(**i) for i in self.ports]
    

@strawberry_django.type(
    models.State
)
class State:
    id: strawberry.ID
    state_schema: StateSchema
    value: scalars.Args
    created_at: datetime.datetime
    updated_at: datetime.datetime
    historical_states: list["HistoricalState"]

@strawberry_django.type(
    models.HistoricalState
)
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
