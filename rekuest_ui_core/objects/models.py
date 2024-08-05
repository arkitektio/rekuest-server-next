import strawberry
from typing import Optional
from pydantic import BaseModel
from strawberry.experimental import pydantic
from typing import Literal, Union
import datetime
from rekuest_core import enums

class UIChildModel(BaseModel):
    kind: str 


class UIGridItemModel(BaseModel):
    span: int
    child: UIChildModel


class UIGridModel(UIChildModel):
    kind: Literal["UI_GRID"] = "UI_GRID"
    rows: int 
    columns: int
    children: list["UIChildModelUnion"]


class UISplitModel(UIChildModel):
    kind: Literal["UI_SPLIT"] = "UP_SPLIT"
    left: "UIChildModelUnion"
    right: "UIChildModelUnion"


UIChildModelUnion = UIGridModel | UISplitModel

class UITreeModel(BaseModel):
    label: str
    child: UIChildModelUnion
