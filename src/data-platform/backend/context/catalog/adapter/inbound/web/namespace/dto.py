"""Define the namespace API DTOs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreateNamespaceApiRequest(BaseModel):
    """Carry the create namespace form: the parts of the new namespace and its properties."""

    model_config = ConfigDict(extra="forbid")

    namespace: list[str]
    properties: dict[str, str] = Field(default_factory=dict)


class UpdateNamespacePropertiesApiRequest(BaseModel):
    """Carry the properties to set and the property keys to remove."""

    model_config = ConfigDict(extra="forbid")

    updates: dict[str, str] = Field(default_factory=dict)
    removals: list[str] = Field(default_factory=list)


class NamespaceApiResponse(BaseModel):
    """Describe a namespace: its catalog, its parts and its properties."""

    model_config = ConfigDict(from_attributes=True)

    catalog: str
    namespace: list[str]
    properties: dict[str, str]


class NamespaceSummaryApiResponse(BaseModel):
    """Name a namespace in a listing, which carries no properties."""

    model_config = ConfigDict(from_attributes=True)

    catalog: str
    namespace: list[str]
