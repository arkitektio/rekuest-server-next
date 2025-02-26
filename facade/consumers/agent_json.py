# JSON RPC Messages
from typing import List, Literal, Optional

from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from facade.enums import (
    AssignationStatus,
    ProvisionStatus,
)
from enum import Enum
from .messages import (
    Assignation,
    AssignationLog,
    Provision,
    ProvisionLog,
    Unassignation,
    Unprovision,
)


class AgentMessageTypes(str, Enum):
    HELLO = "HELLO"

    ASSIGN_CHANGED = "ASSIGN_CHANGED"
    PROVIDE_CHANGED = "PROVIDE_CHANGED"

    ASSIGN_LOG = "ASSIGN_LOG"
    PROVIDE_LOG = "PROVIDE_LOG"

    LIST_ASSIGNATIONS = "LIST_ASSIGNATIONS"
    LIST_ASSIGNATIONS_REPLY = "LIST_ASSIGNATIONS_REPLY"
    LIST_ASSIGNATIONS_DENIED = "LIST_ASSIGNATIONS_DENIED"

    INQUIRY = "INQUIRY"

    LIST_PROVISIONS = "LIST_PROVISIONS"
    LIST_PROVISIONS_REPLY = "LIST_PROVISIONS_REPLY"
    LIST_PROVISIONS_DENIED = "LIST_PROVISIONS_DENIED"


class AgentSubMessageTypes(str, Enum):

    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    PROVIDE = "PROVIDE"
    UNPROVIDE = "UNPROVIDE"


class JSONMeta(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JSONMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    meta: JSONMeta = Field(default_factory=JSONMeta)


class AssignationsList(JSONMessage):
    type: Literal[AgentMessageTypes.LIST_ASSIGNATIONS] = (
        AgentMessageTypes.LIST_ASSIGNATIONS
    )
    exclude: Optional[List[AssignationStatus]]


class AssignationsInquiry(JSONMessage):
    type: Literal[AgentMessageTypes.INQUIRY] = AgentMessageTypes.INQUIRY
    assignations: List[Assignation]


class AssignationsListReply(JSONMessage):
    type: Literal[AgentMessageTypes.LIST_ASSIGNATIONS_REPLY] = (
        AgentMessageTypes.LIST_ASSIGNATIONS_REPLY
    )
    assignations: List[Assignation]


class AssignationsListDenied(JSONMessage):
    type: Literal[AgentMessageTypes.LIST_ASSIGNATIONS_DENIED] = (
        AgentMessageTypes.LIST_ASSIGNATIONS_DENIED
    )
    error: str


class ProvisionList(JSONMessage):
    type: Literal[AgentMessageTypes.LIST_PROVISIONS] = AgentMessageTypes.LIST_PROVISIONS
    exclude: Optional[List[AssignationStatus]]


class ProvisionListReply(JSONMessage):
    type: Literal[AgentMessageTypes.LIST_PROVISIONS_REPLY] = (
        AgentMessageTypes.LIST_PROVISIONS_REPLY
    )
    provisions: List[Provision]


class ProvisionListDenied(JSONMessage):
    type: Literal[AgentMessageTypes.LIST_PROVISIONS_DENIED] = (
        AgentMessageTypes.LIST_PROVISIONS_DENIED
    )
    error: str


class ProvisionChangedMessage(JSONMessage):
    type: Literal[AgentMessageTypes.PROVIDE_CHANGED] = AgentMessageTypes.PROVIDE_CHANGED
    provision: str
    status: ProvisionStatus
    message: Optional[str]


class AssignSubMessage(JSONMessage, Assignation):
    type: Literal[AgentSubMessageTypes.ASSIGN] = AgentSubMessageTypes.ASSIGN
    guardian: str


class ProvideSubMessage(JSONMessage, Provision):
    type: Literal[AgentSubMessageTypes.PROVIDE] = AgentSubMessageTypes.PROVIDE
    guardian: str


class UnassignSubMessage(JSONMessage, Unassignation):
    type: Literal[AgentSubMessageTypes.UNASSIGN] = AgentSubMessageTypes.UNASSIGN


class UnprovideSubMessage(JSONMessage, Unprovision):
    type: Literal[AgentSubMessageTypes.UNPROVIDE] = AgentSubMessageTypes.UNPROVIDE


class AssignationChangedMessage(JSONMessage, Assignation):
    type: Literal[AgentMessageTypes.ASSIGN_CHANGED] = AgentMessageTypes.ASSIGN_CHANGED


class AssignationLogMessage(JSONMessage, AssignationLog):
    type: Literal[AgentMessageTypes.ASSIGN_LOG] = AgentMessageTypes.ASSIGN_LOG


class ProvisionLogMessage(JSONMessage, ProvisionLog):
    type: Literal[AgentMessageTypes.PROVIDE_LOG] = AgentMessageTypes.PROVIDE_LOG
