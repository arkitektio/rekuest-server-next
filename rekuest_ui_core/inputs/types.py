from typing import Optional
from strawberry.experimental import pydantic
from strawberry import LazyType
from rekuest_ui_core.inputs import models
from rekuest_ui_core import enums


@pydantic.input(models.UIChildInputModel)
class UIChildInput:
    kind: enums.UIChildKind
    hidden: bool | None = False
    state: str | None = None
    children: list[LazyType("UIChildInput", __name__)] | None
    left: Optional[LazyType("UIChildInput", __name__)]
    right: Optional[LazyType("UIChildInput", __name__)]


@pydantic.input(models.UITreeInputModel)
class UITreeInput:
    child: UIChildInput
