"""Strawberry-django filters and orders for the facade app, split by domain.

This ``__init__`` re-exports every public filter/order so the established
``from facade import filters`` / ``filters.X`` access keeps working. Submodules use
``from __future__ import annotations`` and cross-referenced filters are injected into
each submodule's namespace below, so nested filter references resolve at schema-build time.
"""

from . import (
    action,
    agent,
    assignation,
    auth,
    blok,
    common,
    dashboard,
    dependency,
    implementation,
    reservation,
    session,
    shelve,
    structure,
    testcase,
    threed,
    toolbox,
)
from .action import ActionFilter, ActionOrder
from .agent import (
    AgentFilter,
    AgentOrder,
    HardwareRecordFilter,
    ImplementationAgentFilter,
)
from .assignation import (
    AssignationEventFilter,
    AssignationEventOrder,
    AssignationFilter,
    AssignationOrder,
)
from .auth import (
    ClientFilter,
    ClientOrder,
    OrganizationFilter,
    OrganizationOrder,
    UserFilter,
    UserOrder,
)
from .blok import MaterializedBlokFilter, MaterializedBlokOrder
from .common import ParamPair, ScopeFilter
from .dashboard import DashboardPlacementFilter, DashboardPlacementOrder
from .dependency import (
    BlokDependencyFilter,
    DependencyFilter,
    ResolutionFilter,
    ResolvedDependencyFilter,
)
from .implementation import (
    ImplementationActionFilter,
    ImplementationFilter,
    ImplementationOrder,
)
from .reservation import ReservationFilter
from .session import SessionFilter, SessionOrder
from .shelve import (
    FileDrawerFilter,
    FilesystemShelveFilter,
    MemoryDrawerFilter,
    MemoryShelveFilter,
    MemoryShelveOrder,
)
from .structure import (
    InputInterfaceUsageFilter,
    InputStructureUsageFilter,
    InterfaceFilter,
    OutputInterfaceUsageFilter,
    OutputStructureUsageFilter,
    StructureFilter,
    StructurePackageFilter,
)
from .testcase import TestCaseFilter, TestResultFilter
from .threed import (
    PlacementFilter,
    PlacementOrder,
    SpaceFilter,
    SpaceOrder,
    ThreeDModelFilter,
    ThreeDModelOrder,
)
from .toolbox import (
    ProtocolFilter,
    ProtocolOrder,
    ShortcutActionFilter,
    ShortcutFilter,
    ShortcutOrder,
    ToolboxFilter,
    ToolboxOrder,
)

__all__ = [
    "ScopeFilter",
    "ParamPair",
    "UserFilter",
    "UserOrder",
    "OrganizationOrder",
    "OrganizationFilter",
    "ClientOrder",
    "ClientFilter",
    "AgentFilter",
    "AgentOrder",
    "HardwareRecordFilter",
    "ImplementationAgentFilter",
    "FilesystemShelveFilter",
    "MemoryShelveFilter",
    "MemoryShelveOrder",
    "FileDrawerFilter",
    "MemoryDrawerFilter",
    "ReservationFilter",
    "AssignationOrder",
    "AssignationFilter",
    "AssignationEventOrder",
    "AssignationEventFilter",
    "TestCaseFilter",
    "TestResultFilter",
    "ResolutionFilter",
    "ResolvedDependencyFilter",
    "DependencyFilter",
    "BlokDependencyFilter",
    "ProtocolOrder",
    "ShortcutOrder",
    "ToolboxOrder",
    "ProtocolFilter",
    "ToolboxFilter",
    "ShortcutActionFilter",
    "ShortcutFilter",
    "ActionOrder",
    "ActionFilter",
    "ImplementationOrder",
    "ImplementationActionFilter",
    "ImplementationFilter",
    "StructurePackageFilter",
    "StructureFilter",
    "InterfaceFilter",
    "InputInterfaceUsageFilter",
    "OutputInterfaceUsageFilter",
    "InputStructureUsageFilter",
    "OutputStructureUsageFilter",
    "ThreeDModelOrder",
    "ThreeDModelFilter",
    "SpaceOrder",
    "SpaceFilter",
    "PlacementOrder",
    "PlacementFilter",
    "MaterializedBlokOrder",
    "MaterializedBlokFilter",
    "DashboardPlacementFilter",
    "DashboardPlacementOrder",
    "SessionOrder",
    "SessionFilter",
]

# --- Nested-filter reference resolution -------------------------------------------
# Inject every public filter into each submodule so the string forward references in
# nested filter annotations resolve when Strawberry builds the schema.
_SUBMODULES = (
    action,
    agent,
    assignation,
    auth,
    blok,
    common,
    dashboard,
    dependency,
    implementation,
    reservation,
    session,
    shelve,
    structure,
    testcase,
    threed,
    toolbox,
)
_EXPORTED = {name: globals()[name] for name in __all__}
for _submodule in _SUBMODULES:
    for _name, _obj in _EXPORTED.items():
        setattr(_submodule, _name, _obj)
