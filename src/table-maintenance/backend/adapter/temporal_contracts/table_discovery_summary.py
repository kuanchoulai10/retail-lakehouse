"""Define the table_discovery_summary helper."""

from __future__ import annotations


def table_discovery_summary(
    catalog: str, namespace: str | None, *, adhoc: bool = False
) -> str:
    """Return the static summary of a discovery run: its scope and, if so, ad hoc."""
    scope = catalog if namespace is None else f"{catalog}.{namespace}"
    return f"{scope} · ad hoc" if adhoc else scope
