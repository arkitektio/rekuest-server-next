"""Agent, waiter, hardware record and agent event types."""

from __future__ import annotations

import datetime
from typing import Optional

import strawberry
import strawberry_django
from django.conf import settings
from django.utils import timezone
from kante.types import Info

from facade import enums, filters, models, scalars
from facade.types.base import build_prescoped_queryset


@strawberry_django.type(models.HardwareRecord, filters=filters.HardwareRecordFilter, pagination=True, description="Represents a record of an agent's hardware configuration.")
class HardwareRecord:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the hardware record.")
    cpu_count: int = strawberry_django.field(description="Number of CPU cores available.")
    cpu_vendor_name: str = strawberry_django.field(description="Vendor of the CPU.")
    cpu_frequency: float = strawberry_django.field(description="Clock speed of the CPU in GHz.")
    created_at: datetime.datetime = strawberry_django.field(description="Timestamp when this record was created.")
    agent: "Agent" = strawberry_django.field(description="The agent to which this hardware belongs.")


@strawberry_django.type(models.Agent, filters=filters.AgentFilter, ordering=filters.AgentOrder, pagination=True, description="Represents a compute agent that can execute implementations.")
class Agent:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the agent.")
    hash: str = strawberry_django.field(description="Hash representing the agent's definition for change detection.")
    instance_id: scalars.InstanceId = strawberry_django.field(description="Unique instance identifier on the agent.")
    registry: "Registry" = strawberry_django.field(description="Registry entry this agent belongs to.")
    hardware_records: list[HardwareRecord] = strawberry_django.field(description="Historical records of agent's hardware.")
    device: Device = strawberry_django.field(description="Device associated with the agent.")
    user: User = strawberry_django.field(description="User associated with the agent.")
    implementations: list["Implementation"] = strawberry_django.field(description="Implementations the agent can run.")
    memory_shelve: Optional["MemoryShelve"] = strawberry_django.field(description="Agent's associated memory shelve.")
    file_system_shelves: list["FilesystemShelve"] = strawberry_django.field(description="Filesystem shelves available on the agent.")
    last_seen: datetime.datetime | None = strawberry_django.field(description="Last timestamp this agent was seen.")
    connected: bool = strawberry_django.field(description="Is the agent currently connected.")
    extensions: list[str] = strawberry_django.field(description="List of installed agent extensions.")
    name: str = strawberry_django.field(description="Agent name.")
    states: list["State"] = strawberry_django.field(description="Current and historical states associated with the agent.")
    kind: enums.AgentKind = strawberry_django.field(description="Kind of the agent.")
    hook_url: str | None = strawberry_django.field(description="Webhook URL for this Agent (only if webhook)", default=None)
    hook_url_secret: str | None = strawberry_django.field(description="Webhook URL secret for this Agent (only if webhook)", default=None)
    assignations: list["Assignation"] = strawberry_django.field(description="Assignations executed by this agent.")
    app: App = strawberry_django.field(description="The app this agent belongs to.")
    release: Release = strawberry_django.field(description="The release this agent belongs to.")
    placements: list["Placement"] = strawberry_django.field(description="Placements associated with this agent.")
    sessions: list["Session"] = strawberry_django.field(description="Sessions associated with this agent.")
    agent_mappings: list["BlokAgentMapping"] = strawberry_django.field(description="Blok mappings associated with this agent.")

    @strawberry_django.field(description="Fetch a specific implementation by interface.")
    def implementation(self, interface: str) -> Implementation | None:
        return self.implementations.filter(interface=interface).first()

    @strawberry_django.field(description="Determine if the agent is currently active based on last seen timestamp.")
    def active(self) -> bool:
        return self.connected and self.last_seen > timezone.now() - datetime.timedelta(seconds=settings.AGENT_DISCONNECTED_TIMEOUT)

    @strawberry_django.field(description="Retrieve the latest hardware record for this agent.")
    def latest_hardware_record(self) -> HardwareRecord | None:
        return self.hardware_records.order_by("-created_at").first()

    @strawberry_django.field(description="Check if this agent is pinned by the current user.")
    def pinned(self, info: Info) -> bool:
        user = info.context.request.user
        return self.pinned_by.filter(id=user.id).exists()

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return build_prescoped_queryset(info, queryset, field="registry__organization")

    @strawberry_django.field(description="Get the count of implementations available on this agent.")
    def blocked(self) -> bool:
        return self.blocked


@strawberry_django.type(models.Waiter, filters=filters.WaiterFilter, pagination=True, description="Entity that waits for the completion of assignations.")
class Waiter:
    id: strawberry.ID = strawberry_django.field(description="Unique ID of the waiter.")
    instance_id: scalars.InstanceId = strawberry_django.field(description="Instance ID associated with the waiter.")
    registry: "Registry" = strawberry_django.field(description="Registry the waiter belongs to.")


@strawberry_django.type(models.AgentEvent, filters=filters.AssignationEventFilter, pagination=True, description="Event representing agent status or lifecycle change.")
class AgentEvent:
    id: strawberry.ID = strawberry_django.field(description="ID of the agent event.")
    status: enums.AgentStatus = strawberry_django.field(description="Status of the agent during this event.")

    @strawberry_django.field(description="Default log level for agent events.")
    def level(self) -> enums.LogLevel:
        return enums.LogLevel.INFO

    @strawberry_django.field(description="Reference back to the assignation.")
    def reference(self) -> str:
        return self.assignation.reference
