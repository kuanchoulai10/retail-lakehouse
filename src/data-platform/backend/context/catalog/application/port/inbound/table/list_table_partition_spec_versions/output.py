"""Define the ListTablePartitionSpecVersionsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListTablePartitionSpecVersionsUseCaseOutput(UseCaseOutput):
    """Carry the default spec id and every partition spec version, newest id first."""

    class Version(UseCaseOutput):
        """One partition spec version and what it changed against the version below it.

        ``changes`` counts the fields carrying each kind of change (``added``, ``removed``,
        ``renamed``, ``transform_changed``, zeros included) and is None for the first version.
        ``field_count`` leaves out ``void`` fields.
        """

        spec_id: int
        previous_spec_id: int | None
        default: bool
        field_count: int
        changes: dict[str, int] | None

    default_spec_id: int
    items: tuple[Version, ...]
