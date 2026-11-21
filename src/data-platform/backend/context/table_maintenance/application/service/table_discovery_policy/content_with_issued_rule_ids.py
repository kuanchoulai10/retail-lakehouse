"""Define the content_with_issued_rule_ids function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


def content_with_issued_rule_ids(
    content: dict[str, Any], new_id: Callable[[], str]
) -> tuple[dict[str, Any], frozenset[str]]:
    """Return a copy of the content where each rule sent without an id holds a new one, and the ids it issued.

    A rule's ``id`` that is absent or ``None`` gets ``new_id()``; any other id is kept for the policy
    to check. ``"id": ""`` raises ``ValueError``: it is neither a ``dr-`` id nor absent. A rule that is
    not an object is passed through for the content to refuse.
    """
    rules = content.get("rules")
    if not isinstance(rules, list):
        return dict(content), frozenset()
    issued: list[str] = []
    filled: list[Any] = []
    for rule in rules:
        if isinstance(rule, dict) and rule.get("id") == "":
            raise ValueError("a rule id is a dr- id or absent")
        if isinstance(rule, dict) and rule.get("id") is None:
            rule_id = new_id()
            issued.append(rule_id)
            filled.append({**rule, "id": rule_id})
        else:
            filled.append(rule)
    return {**content, "rules": filled}, frozenset(issued)
