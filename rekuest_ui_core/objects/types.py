import datetime
from typing import Optional

import strawberry
import strawberry_django
from pydantic import BaseModel
from strawberry import LazyType
from strawberry.experimental import pydantic

from rekuest_ui_core.objects import models
from rekuest_ui_core import enums, scalars



@pydantic.interface(models.UIChildModel)
class UIChild:
    kind: enums.UIChildKind

@pydantic.type(models.UIGridItemModel)
class UIGridItem:
    x: int
    y: int
    w: int
    h: int
    min_w: int
    max_w: int
    child: UIChild



@pydantic.type(models.UIBreakpointModel)
class UIBreakpoint:
    lg: int = 12
    md: int = 8
    sm: int = 4
    xs: int = 2
    xxs: int = 24


@pydantic.type(models.UIGridModel)
class UIGrid(UIChild):
    row_height:  int
    columns: int
    children: list[UIGridItem]


@pydantic.type(models.UISplitModel)
class UISplit(UIChild):
    left: UIChild
    right: UIChild


@pydantic.type(models.UIStateModel)
class UIState(UIChild):
    state: str

@pydantic.type(models.UITreeModel)
class UITree:
    child: UIChild