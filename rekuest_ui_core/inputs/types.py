from typing import Optional, Annotated
import strawberry
from strawberry.experimental import pydantic
from strawberry import LazyType
from rekuest_ui_core.inputs import models
from rekuest_ui_core import enums


@pydantic.input(models.UIChildInputModel)
class UIChildInput:
    kind: enums.UIChildKind
    hidden: bool | None = False
    state: str | None = None
    children: list[Annotated["UIChildInput", strawberry.lazy(__name__)]] | None
    left: Optional[Annotated["UIChildInput", strawberry.lazy(__name__)]]
    right: Optional[Annotated["UIChildInput", strawberry.lazy(__name__)]]


@pydantic.input(models.UITreeInputModel)
class UITreeInput:
    child: UIChildInput
