"""GraphQL object types for the facade app, split into domain submodules.

This ``__init__`` re-exports every public type so the established
``from facade import types`` / ``types.X`` access keeps working.

Because the types densely cross-reference each other (e.g. ``Action`` references
``Reservation``, ``Agent`` references ``Assignation``), the submodules use
``from __future__ import annotations`` so no annotation is evaluated at import
time (avoiding import cycles). At the bottom of this module every public type is
injected into each submodule's globals, so that the string forward references
resolve against the defining module's namespace when Strawberry builds the schema.
"""

from . import (
    action,
    agent,
    assignation,
    auth,
    base,
    blok,
    dashboard,
    demand,
    dependency,
    implementation,
    reservation,
    session,
    shelve,
    state,
    structure,
    testcase,
    threed,
    toolbox,
)
from .action import Action, ActionStats, ActionStatsResolver
from .agent import Agent, AgentEvent, HardwareRecord
from .assignation import (
    Assignation,
    AssignationEvent,
    AssignationInstruct,
    AssignationStats,
    AssignationStatsResolver,
)
from .auth import App, Client, Device, Organization, Registry, Release, User
from .base import build_prescoped_queryset, build_prescoper
from .blok import Blok, BlokAgentMapping, BlokDependency, MaterializedBlok
from .dashboard import Dashboard, DashboardPlacement, UICatalog
from .demand import (
    ActionDemand,
    ActionDemandModel,
    DynamicValueModel,
    StateDemand,
    StateDemandModel,
)
from .dependency import (
    AgentMapping,
    Dependency,
    DependencyMatch,
    ImplementationMapping,
    MethodMatch,
    ResolvedAgentDependency,
    ResolvedDependency,
    Resolution,
)
from .implementation import Implementation
from .reservation import Reservation
from .session import Session, SessionBoundary, TaskBoundary
from .shelve import FileDrawer, FilesystemShelve, MemoryDrawer, MemoryShelve
from .state import (
    HistoricalState,
    JSONPatch,
    Patch,
    Snapshot,
    State,
    StateDefinition,
    StateUpdateEvent,
)
from .structure import (
    InputInterfaceUsage,
    InputStructureUsage,
    Interface,
    OutputInterfaceUsage,
    OutputStructureUsage,
    Structure,
    StructurePackage,
)
from .testcase import TestCase, TestResult
from .threed import Placement, Space, ThreeDModel
from .toolbox import Collection, Protocol, Shortcut, Toolbox

__all__ = [
    "build_prescoped_queryset",
    "build_prescoper",
    "Action",
    "ActionStats",
    "ActionStatsResolver",
    "ActionDemand",
    "ActionDemandModel",
    "StateDemand",
    "StateDemandModel",
    "DynamicValueModel",
    "User",
    "Device",
    "App",
    "Release",
    "Client",
    "Organization",
    "Registry",
    "Collection",
    "Protocol",
    "Toolbox",
    "Shortcut",
    "Dependency",
    "ResolvedDependency",
    "MethodMatch",
    "DependencyMatch",
    "Resolution",
    "ImplementationMapping",
    "AgentMapping",
    "ResolvedAgentDependency",
    "Implementation",
    "HardwareRecord",
    "Agent",
    "AgentEvent",
    "MemoryShelve",
    "FilesystemShelve",
    "FileDrawer",
    "MemoryDrawer",
    "Reservation",
    "Assignation",
    "AssignationStats",
    "AssignationStatsResolver",
    "AssignationEvent",
    "AssignationInstruct",
    "TestCase",
    "TestResult",
    "Dashboard",
    "UICatalog",
    "DashboardPlacement",
    "Blok",
    "BlokDependency",
    "MaterializedBlok",
    "BlokAgentMapping",
    "StateDefinition",
    "State",
    "HistoricalState",
    "JSONPatch",
    "StateUpdateEvent",
    "Patch",
    "Snapshot",
    "StructurePackage",
    "Interface",
    "Structure",
    "InputStructureUsage",
    "OutputStructureUsage",
    "InputInterfaceUsage",
    "OutputInterfaceUsage",
    "TaskBoundary",
    "SessionBoundary",
    "Session",
    "ThreeDModel",
    "Space",
    "Placement",
]

# --- Forward-reference resolution -------------------------------------------------
# Inject every public type into each submodule's namespace so that the string
# forward references in their annotations resolve when Strawberry builds the schema.
_SUBMODULES = (
    action,
    agent,
    assignation,
    auth,
    blok,
    dashboard,
    demand,
    dependency,
    implementation,
    reservation,
    session,
    shelve,
    state,
    structure,
    testcase,
    threed,
    toolbox,
)
_EXPORTED = {name: globals()[name] for name in __all__}
for _submodule in _SUBMODULES:
    for _name, _obj in _EXPORTED.items():
        setattr(_submodule, _name, _obj)
