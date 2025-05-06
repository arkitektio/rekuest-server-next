from typing import Optional
from rekuest_ui_core import enums
from pydantic import BaseModel


class UIChildInputModel(BaseModel):
    kind: enums.UIChildKind
    hidden: bool
    children: Optional[list["UIChildInputModel"]]
    left: Optional["UIChildInputModel"]
    right: Optional["UIChildInputModel"]


class UITreeInputModel(BaseModel):
    """A definition for a implementation"""

    description: str = "No description provided"
    child: UIChildInputModel
