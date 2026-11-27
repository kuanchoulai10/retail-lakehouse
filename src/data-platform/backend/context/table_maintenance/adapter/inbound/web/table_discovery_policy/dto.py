"""Define the discovery policy API DTOs.

A policy is a ``description`` and its ordered ``rules``; every policy response carries them flat beside
the server's fields. Each rule includes or excludes the tables whose name matches its pattern, and the
last rule that matches a table decides it; a table no rule matches is not managed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_FORBID_EXTRA = ConfigDict(extra="forbid")
_RULES = (
    "The rules, at least one, read top to bottom; the last whose pattern matches a table decides it, "
    "and a table no rule matches is not managed."
)
_ACTION = "`include` brings the matching tables under management; `exclude` leaves them out."
_TABLE_NAME_PATTERN = (
    "A case-sensitive glob on the table name alone (`*`, `?`, `[...]`), never on its namespace or catalog."
)

_Action = Literal["include", "exclude"]


class DiscoveryRuleApiRequest(BaseModel):
    """Carry one rule: include or exclude the tables whose name matches the pattern."""

    model_config = _FORBID_EXTRA

    action: _Action = Field(description=_ACTION)
    table_name_pattern: str = Field(description=_TABLE_NAME_PATTERN)


class CreateTableDiscoveryPolicyApiRequest(BaseModel):
    """Carry a new discovery policy's name, description and rules."""

    model_config = _FORBID_EXTRA

    name: str
    description: str = ""
    rules: list[DiscoveryRuleApiRequest] = Field(min_length=1, description=_RULES)


class UpdateTableDiscoveryPolicyApiRequest(BaseModel):
    """Carry a discovery policy's new description and rules and the version it was edited from."""

    model_config = _FORBID_EXTRA

    version: int
    description: str
    rules: list[DiscoveryRuleApiRequest] = Field(min_length=1, description=_RULES)


class DiscoveryRuleApiResponse(BaseModel):
    """Describe one rule of a policy; its place in the list is its position, counted from 1."""

    action: _Action = Field(description=_ACTION)
    table_name_pattern: str = Field(description=_TABLE_NAME_PATTERN)


class TableDiscoveryPolicyApiResponse(BaseModel):
    """Describe a discovery policy at its current version."""

    id: str
    name: str
    version: int
    created_at: datetime
    updated_at: datetime
    description: str
    rules: list[DiscoveryRuleApiResponse] = Field(description=_RULES)


class ListedTableDiscoveryPolicyApiResponse(BaseModel):
    """Describe a listed discovery policy at its current version with how many targets it is attached to."""

    id: str
    name: str
    version: int
    created_at: datetime
    updated_at: datetime
    description: str
    rules: list[DiscoveryRuleApiResponse] = Field(description=_RULES)
    attachment_count: int


class TableDiscoveryPoliciesApiResponse(BaseModel):
    """List every discovery policy by name."""

    policies: list[ListedTableDiscoveryPolicyApiResponse]


class TableDiscoveryPolicyVersionApiResponse(BaseModel):
    """Describe one stored version of a discovery policy; ``created_at`` is when that version was written."""

    id: str
    name: str
    version: int
    created_at: datetime
    description: str
    rules: list[DiscoveryRuleApiResponse] = Field(description=_RULES)
