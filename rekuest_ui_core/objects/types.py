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
    span: int
    child: UIChild


@pydantic.type(models.UIGridModel)
class UIGrid(UIChild):
    rows: int
    columns: int
    children: list[UIGridItem]



@pydantic.type(models.UISplitModel)
class UISplit(UIChild):
    left: UIChild
    right: UIChild

@pydantic.type(models.UITreeModel)
class UITree:
    child: UIChild