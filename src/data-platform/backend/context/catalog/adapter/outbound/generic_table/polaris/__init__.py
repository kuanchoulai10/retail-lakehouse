"""Polaris adapters of the generic table aggregate: the generic tables repo and its reply mapper."""

from __future__ import annotations

from context.catalog.adapter.outbound.generic_table.polaris.generic_table_from_polaris import (
    generic_table_from_polaris,
)
from context.catalog.adapter.outbound.generic_table.polaris.generic_tables_polaris_repo import (
    GenericTablesPolarisRepo,
)

__all__ = ["GenericTablesPolarisRepo", "generic_table_from_polaris"]
