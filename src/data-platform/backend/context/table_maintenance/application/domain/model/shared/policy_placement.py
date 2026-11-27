"""Define the PolicyPlacement value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.policy_target import PolicyTarget


class PolicyPlacement(ValueObject):
    """One place a policy is attached: the catalog, namespace or table holding it.

    It is read from the places themselves, which each hold at most one policy of a kind, so a
    policy is placed once per place it is attached to.
    """

    target: PolicyTarget
