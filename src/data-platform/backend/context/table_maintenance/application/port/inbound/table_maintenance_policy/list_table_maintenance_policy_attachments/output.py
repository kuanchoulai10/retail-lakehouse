"""Define the ListTableMaintenancePolicyAttachmentsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListTableMaintenancePolicyAttachmentsUseCaseOutput(UseCaseOutput):
    """Carry the places one maintenance policy is attached to, by type and then path."""

    class Placement(UseCaseOutput):
        """One place; ``orphaned`` when it no longer exists in the catalog.

        A place in a catalog the platform's credential cannot read is not known to be gone, so it is
        not orphaned.
        """

        type: str
        path: tuple[str, ...]
        table_uuid: str | None
        policy_id: str
        policy_name: str
        orphaned: bool

    items: tuple[Placement, ...]
