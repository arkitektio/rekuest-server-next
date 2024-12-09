from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Tuple
from pydantic import BaseModel
from facade.enums import LogLevel, ReservationStatus, AssignationStatus, ProvisionStatus

T = TypeVar("T", bound=BaseModel)


class UpdatableModel(BaseModel):
    pass

    def update(self: T, other: BaseModel, in_place=True) -> Optional[T]:
        if in_place:
            for key, value in other.dict().items():
                if key in self.__fields__:
                    if value != None:  # None is not a valid update!
                        setattr(self, key, value)
        else:
            copy = self.copy()
            copy.update(other)
            return copy


class ReserveTactic(str, Enum):
    ALL = "ALL"
    FILTER_OWN = "FILTER_OWN"
    FILTER_ACTIVE = "FILTER_ACTIVE"
    FILTER_AGENTS = "FILTER_AGENTS"
    FILTER_TEMPLATES = "FILTER_TEMPLATES"
    BALANCE = "BALANCE"


class ProvideTactic(str, Enum):
    ALL = "ALL"
    FILTER_OWN = "FILTER_OWN"
    FILTER_ACTIVE = "FILTER_ACTIVE"
    FILTER_AGENTS = "FILTER_AGENTS"
    FILTER_TEMPLATES = "FILTER_TEMPLATES"
    BALANCE = "BALANCE"


class BindParams(BaseModel):
    templates: Tuple[str, ...]
    clients: Tuple[str, ...]

    def hash(self):
        return "binds-" + "t".join(self.templates) + "c".join(self.clients)


class Assignation(UpdatableModel):
    assignation: str
    provision: Optional[str]
    reservation: Optional[str]
    args: Optional[List[Any]]
    returns: Optional[List[Any]]
    persist: Optional[bool]
    progress: Optional[int]
    log: Optional[bool]
    status: Optional[AssignationStatus]
    message: Optional[str]
    user: Optional[str]


class Unassignation(UpdatableModel):
    assignation: str
    provision: Optional[str]


class Provision(UpdatableModel):
    provision: str
    guardian: Optional[str]
    template: Optional[str]
    status: Optional[ProvisionStatus]


class Unprovision(UpdatableModel):
    provision: str
    message: Optional[str]


class Reservation(UpdatableModel):
    reservation: str
    template: Optional[str]
    node: Optional[str]
    status: Optional[ReservationStatus] = None
    message: Optional[str] = ""


class Unreservation(BaseModel):
    reservation: str


class AssignationLog(BaseModel):
    assignation: str
    level: LogLevel
    message: Optional[str]


class ProvisionLog(BaseModel):
    provision: str
    level: LogLevel
    message: Optional[str]
