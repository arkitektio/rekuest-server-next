from pydantic import BaseModel


class AgentTemplateBaseModel(BaseModel):
    implementations: list[str] = []
    manifest: Manifest
