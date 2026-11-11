"""Define the discovery rules API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TableDiscoveryRuleApiRequest(BaseModel):
    """Carry one rule of a rule list; a rule without ``id`` is new."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    priority: int
    action: str
    enabled: bool
    catalogs: list[str]
    namespaces: list[str]
    tables: list[str]


class ReplaceTableDiscoveryRulesApiRequest(BaseModel):
    """Carry the whole new rule list and the version it was edited from."""

    model_config = ConfigDict(extra="forbid")

    version: int
    rules: list[TableDiscoveryRuleApiRequest]


class PreviewTableDiscoveryRulesApiRequest(BaseModel):
    """Carry a whole candidate rule list, unsaved."""

    model_config = ConfigDict(extra="forbid")

    rules: list[TableDiscoveryRuleApiRequest]


class TableDiscoveryRuleApiResponse(BaseModel):
    """Describe one discovery rule."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    priority: int
    action: str
    enabled: bool
    catalogs: list[str]
    namespaces: list[str]
    tables: list[str]
    created_at: datetime
    updated_at: datetime


class TableDiscoveryRulesApiResponse(BaseModel):
    """Describe the discovery rules in priority order with the list's version."""

    model_config = ConfigDict(from_attributes=True)

    version: int
    rules: list[TableDiscoveryRuleApiResponse]


class DiscoveryPreviewTableApiResponse(BaseModel):
    """Describe one table of a preview: the rule that would decide it, or null, and whether it would be managed."""

    model_config = ConfigDict(from_attributes=True)

    catalog: str
    namespace: str
    table: str
    rule_id: str | None
    managed: bool


class PreviewTableDiscoveryRulesApiResponse(BaseModel):
    """Describe every table of the covered catalogs under a candidate rule list, with counts."""

    model_config = ConfigDict(from_attributes=True)

    tables: list[DiscoveryPreviewTableApiResponse]
    managed: int
    unmanaged: int


class CoveredCatalogsApiResponse(BaseModel):
    """List the catalogs maintenance covers."""

    model_config = ConfigDict(from_attributes=True)

    catalogs: list[str]
