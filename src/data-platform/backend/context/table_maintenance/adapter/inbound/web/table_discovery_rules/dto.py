"""Define the discovery rules API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TableDiscoveryRuleApiRequest(BaseModel):
    """Carry one rule of a rule list; a rule without ``id`` is new."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(
        default=None,
        description=(
            "A `dr-` id (prefix, dash, 26 lowercase Crockford base32 characters; ADR 0011), as the rule "
            "list returned it; omit it for a new rule."
        ),
    )
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


class CoveredCatalogsApiResponse(BaseModel):
    """List the catalogs maintenance covers."""

    model_config = ConfigDict(from_attributes=True)

    catalogs: list[str]
