"""Provide OwnedNames, the names the e2e gives what it creates and how a later run recognizes them."""

from __future__ import annotations

import re

_SUFFIX = "[0-9a-f]{8}"
_SCENARIO = "[a-z][a-z_]*"
_SCENARIO_WORD = re.compile(rf"^{_SCENARIO}$")


def _word(scenario: str) -> str:
    if not _SCENARIO_WORD.match(scenario):
        raise ValueError(f"scenario word {scenario!r} is not {_SCENARIO}, so the sweep would never match its names")
    return scenario


class OwnedNames:
    """Build each name from the run's suffix and a scenario word; match the names an earlier run gave.

    A run that is cut short (pod deadline, eviction, delete) cannot undo what it made, so the next
    run removes whatever matches these patterns. Only the e2e gives names of these shapes.
    """

    CATALOGS_BUCKET = "tm-e2e-catalogs"
    NAMESPACE = re.compile(rf"^e2e_{_SUFFIX}_{_SCENARIO}$")
    MAINTENANCE_POLICY = re.compile(rf"^tm-e2e-{_SCENARIO}-{_SUFFIX}$")
    DISCOVERY_POLICY = re.compile(rf"^tm-e2e-{_SUFFIX}-{_SCENARIO}$")
    CATALOG = re.compile(rf"^tm_e2e_catalog_{_SUFFIX}_{_SCENARIO}$")
    QUEUE_HOLDER = re.compile(rf"^tm-e2e-holder-{_SUFFIX}-[a-z][a-z-]*$")

    @staticmethod
    def namespace(suffix: str, scenario: str) -> str:
        """Return the scenario's namespace in the platform's catalog."""
        return f"e2e_{suffix}_{_word(scenario)}"

    @staticmethod
    def maintenance_policy(suffix: str, scenario: str) -> str:
        """Return the scenario's maintenance policy."""
        return f"tm-e2e-{_word(scenario)}-{suffix}"

    @staticmethod
    def discovery_policy(suffix: str, scenario: str) -> str:
        """Return the discovery policy that manages the scenario's namespace."""
        return f"tm-e2e-{suffix}-{_word(scenario)}"

    @staticmethod
    def catalog(suffix: str, scenario: str) -> str:
        """Return a catalog the scenario creates, stored under ``CATALOGS_BUCKET``."""
        return f"tm_e2e_catalog_{suffix}_{_word(scenario)}"

    @staticmethod
    def queue_holder(suffix: str, scenario: str) -> str:
        """Return the scenario's queue holder, a Kubernetes name, so its underscores become hyphens."""
        return f"tm-e2e-holder-{suffix}-{_word(scenario).replace('_', '-')}"
