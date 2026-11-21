"""Define the SyncDiscoverySchedulesGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncDiscoverySchedulesGatewayInput:
    """Name the catalogs that keep a discovery schedule and the catalogs whose schedule is deleted.

    ``removed`` lists only catalogs that stopped being scanned and have had their final scan started;
    a catalog is never in both.
    """

    catalogs: tuple[str, ...]
    removed: tuple[str, ...]

    def __post_init__(self) -> None:
        """Refuse a catalog that is both kept and removed."""
        both = sorted(set(self.catalogs) & set(self.removed))
        if both:
            msg = f"catalogs both kept and removed: {both}"
            raise ValueError(msg)
