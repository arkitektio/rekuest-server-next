"""Django ORM models for the facade app, split into domain submodules.

This ``__init__`` imports every model so Django's app registry discovers them, and
re-exports them so both ``from facade import models`` / ``models.X`` and the
``from facade.models import X`` direct-symbol imports keep working. Cross-submodule
foreign keys use string references (``"Action"``) which Django resolves via the app
registry, so submodule import order does not matter.
"""

from .action import (
    Action,
    ArgPort,
    BasePort,
    InputInterfaceUsage,
    InputStructureUsage,
    OutputInterfaceUsage,
    OutputStructureUsage,
    ReturnPort,
)
from .agent import (
    Agent,
    FileDrawer,
    FilesystemShelve,
    HardwareRecord,
    Lock,
    MemoryDrawer,
    MemoryShelve,
)
from .task import (
    AgentEvent,
    Task,
    TaskEvent,
    TaskInstruct,
)
from .blok import (
    Blok,
    BlokAgentMapping,
    BlokDependency,
    Dashboard,
    DashboardPlacement,
    MaterializedBlok,
    Widget,
)
from .catalog import (
    Collection,
    Icon,
    IconPack,
    Protocol,
    Shortcut,
    Toolbox,
    UICatalog,
)
from .implementation import (
    Dependency,
    Implementation,
    Resolution,
    ResolvedDependency,
)
from .caller import Caller
from .state import (
    HistoricalState,
    Patch,
    Session,
    Snapshot,
    State,
    StateDefinition,
)
from .structure import Descriptor, Interface, Structure, StructurePackage
from .testcase import TestCase, TestResult
from .threed import Placement, Space, ThreeDModel

__all__ = [
    # caller
    "Caller",
    # catalog
    "Collection",
    "Protocol",
    "UICatalog",
    "IconPack",
    "Toolbox",
    "Shortcut",
    "Icon",
    # structure
    "StructurePackage",
    "Interface",
    "Descriptor",
    "Structure",
    # action
    "Action",
    "BasePort",
    "ArgPort",
    "ReturnPort",
    "InputStructureUsage",
    "InputInterfaceUsage",
    "OutputStructureUsage",
    "OutputInterfaceUsage",
    # agent
    "Lock",
    "Agent",
    "FilesystemShelve",
    "FileDrawer",
    "MemoryShelve",
    "MemoryDrawer",
    "HardwareRecord",
    # implementation
    "Dependency",
    "Resolution",
    "ResolvedDependency",
    "Implementation",
    # task
    "Task",
    "TaskEvent",
    "TaskInstruct",
    "AgentEvent",
    # testcase
    "TestCase",
    "TestResult",
    # state
    "StateDefinition",
    "State",
    "Session",
    "Patch",
    "Snapshot",
    "HistoricalState",
    # blok
    "Widget",
    "Dashboard",
    "Blok",
    "BlokDependency",
    "MaterializedBlok",
    "DashboardPlacement",
    "BlokAgentMapping",
    # threed
    "ThreeDModel",
    "Space",
    "Placement",
    # signals (connected on import)
    "signals",
]

import facade.signals as signals  # noqa: E402,F401
