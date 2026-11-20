"""Define the ListTableMetricsUseCaseOutput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseOutput


class ListTableMetricsUseCaseOutput(UseCaseOutput):
    """Carry the metrics of every managed table."""

    class Table(UseCaseOutput):
        """One table's names and newest metrics; ``counts`` is keyed by the metric count field names."""

        table_uuid: str
        catalog: str
        namespace: str
        table: str
        observed_at: datetime
        counts: dict[str, int]

    tables: tuple[Table, ...]
