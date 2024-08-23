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


class UIBreakpointModel(BaseModel):
    lg: int  = 12
    md: int = 8
    sm: int = 4
    xs: int = 2
    xxs: int = 24

    
class UIGridModel(UIChildModel):
    kind: Literal["GRID"] = "GRID"
    rows: int 
    columns: int
    children: list["UIChildModelUnion"]

class UISplitModel(UIChildModel):
    kind: Literal["SPLIT"] = "SPLIT"
    left: "UIChildModelUnion"
    right: "UIChildModelUnion"

class UIStateModel(UIChildModel):
    kind: Literal["STATE"] = "STATE"
    state: str


UIChildModelUnion = UIGridModel | UISplitModel | UIStateModel

class UITreeModel(BaseModel):
    label: str | None = None
    child: UIChildModelUnion


UIGridModel.update_forward_refs()
UISplitModel.update_forward_refs()
UIStateModel.update_forward_refs()
UITreeModel.update_forward_refs()
