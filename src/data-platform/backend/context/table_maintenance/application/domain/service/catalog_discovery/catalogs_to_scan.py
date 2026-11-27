"""Define the catalogs_to_scan domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def catalogs_to_scan(with_discovery_policy: Iterable[str], with_managed_tables: Iterable[str]) -> tuple[str, ...]:
    """Return the catalogs discovery scans, sorted and each once (KCL-117).

    A catalog is scanned while a discovery policy is attached in it (to the catalog, a namespace or
    a table), whatever its rules hold: a policy of exclude rules only still decides the tables it
    excludes. A catalog that still holds a managed table is scanned too, even with no policy left,
    so its scan unmanages the tables nothing manages any more and the catalog then drops out.
    """
    return tuple(sorted({*with_discovery_policy, *with_managed_tables}))
