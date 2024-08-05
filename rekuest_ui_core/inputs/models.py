from typing import Any, Optional
from rekuest_ui_core import enums
from pydantic import BaseModel, Field, root_validator
from typing_extensions import Self



class UIChildInputModel(BaseModel):
    kind: enums.UIChildKind
    hidden: bool
    children: Optional[list["UIChildInputModel"]]
    left: Optional["UIChildInputModel"]
    right: Optional["UIChildInputModel"]



class UITreeInputModel(BaseModel):
    """A definition for a template"""

    description: str = "No description provided"
    child: UIChildInputModel





