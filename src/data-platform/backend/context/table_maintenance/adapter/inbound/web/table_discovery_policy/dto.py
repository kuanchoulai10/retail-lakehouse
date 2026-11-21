"""Define the discovery policy API DTOs.

A policy's content is its ``description``, its ordered ``rules`` and its ``no_match_outcome``; every
policy response carries it flat beside the server's fields. A rule's conditions are shaped like
Kubernetes ``matchExpressions`` (``attribute``, ``operator``, ``values``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_FORBID_EXTRA = ConfigDict(extra="forbid")
_IS_DEFAULT = "Whether this is the platform default discovery policy, which decides where nothing is attached."
_NO_MATCH_OUTCOME = "What happens to a table that no rule matches: managed or not."
_RULES = "The rules, read top to bottom; the first whose conditions all hold decides."

_Outcome = Literal["manage", "unmanage"]
_Attribute = Literal["namespace", "table_name"]
_Operator = Literal["glob"]


class DiscoveryConditionApiRequest(BaseModel):
    """Carry one condition: the attribute it reads, how it matches and the values it matches.

    The condition holds when any value matches. A ``glob`` is case-sensitive, and on the dot-joined
    namespace ``*`` crosses dots.
    """

    model_config = _FORBID_EXTRA

    attribute: _Attribute
    operator: _Operator
    values: list[str]


class DiscoveryRuleApiRequest(BaseModel):
    """Carry one rule: its outcome for a table that all of its conditions match.

    Leave ``id`` out (or null) for a new rule; send a rule's ``dr-`` id to keep it across versions.
    """

    model_config = _FORBID_EXTRA

    id: str | None = None
    outcome: _Outcome
    conditions: list[DiscoveryConditionApiRequest]


class CreateTableDiscoveryPolicyApiRequest(BaseModel):
    """Carry a new discovery policy's name and its whole content; its rules may not name an id."""

    model_config = _FORBID_EXTRA

    name: str
    description: str = ""
    no_match_outcome: _Outcome = Field(description=_NO_MATCH_OUTCOME)
    rules: list[DiscoveryRuleApiRequest] = Field(description=_RULES)


class UpdateTableDiscoveryPolicyApiRequest(BaseModel):
    """Carry a discovery policy's whole new content and the version it was edited from."""

    model_config = _FORBID_EXTRA

    version: int
    description: str
    no_match_outcome: _Outcome = Field(description=_NO_MATCH_OUTCOME)
    rules: list[DiscoveryRuleApiRequest] = Field(description=_RULES)


class DiscoveryConditionApiResponse(BaseModel):
    """Describe one condition of a rule."""

    attribute: _Attribute
    operator: _Operator
    values: list[str]


class DiscoveryRuleApiResponse(BaseModel):
    """Describe one rule, with the ``dr-`` id that links it across versions."""

    id: str
    outcome: _Outcome
    conditions: list[DiscoveryConditionApiResponse]


class TableDiscoveryPolicyApiResponse(BaseModel):
    """Describe a discovery policy at its current version."""

    id: str
    name: str
    is_default: bool = Field(description=_IS_DEFAULT)
    version: int
    created_at: datetime
    updated_at: datetime
    description: str
    no_match_outcome: _Outcome = Field(description=_NO_MATCH_OUTCOME)
    rules: list[DiscoveryRuleApiResponse] = Field(description=_RULES)


class ListedTableDiscoveryPolicyApiResponse(BaseModel):
    """Describe a listed discovery policy at its current version with how many targets it is attached to."""

    id: str
    name: str
    is_default: bool = Field(description=_IS_DEFAULT)
    version: int
    created_at: datetime
    updated_at: datetime
    description: str
    no_match_outcome: _Outcome = Field(description=_NO_MATCH_OUTCOME)
    rules: list[DiscoveryRuleApiResponse] = Field(description=_RULES)
    attachment_count: int


class TableDiscoveryPoliciesApiResponse(BaseModel):
    """List every discovery policy, the default first, then by name."""

    policies: list[ListedTableDiscoveryPolicyApiResponse]


class TableDiscoveryPolicyVersionApiResponse(BaseModel):
    """Describe one stored version of a discovery policy; ``created_at`` is when that version was written."""

    id: str
    name: str
    is_default: bool = Field(description=_IS_DEFAULT)
    version: int
    created_at: datetime
    description: str
    no_match_outcome: _Outcome = Field(description=_NO_MATCH_OUTCOME)
    rules: list[DiscoveryRuleApiResponse] = Field(description=_RULES)
