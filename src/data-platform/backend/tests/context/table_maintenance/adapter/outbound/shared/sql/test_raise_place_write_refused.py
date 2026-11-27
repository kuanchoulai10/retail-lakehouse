"""Test the application error a refused write of a catalog, namespace or table becomes, with no database text."""

from __future__ import annotations

import psycopg.errors
import pytest
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.shared.sql import raise_place_write_refused
from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId, TableMaintenancePolicyId
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError


def _refusal(orig: BaseException) -> IntegrityError:
    return IntegrityError("INSERT INTO catalogs ...", {}, orig)


def test_a_duplicate_key_is_a_concurrent_update():
    """Another writer stored the place first: the caller reads it again and retries."""
    refusal = _refusal(psycopg.errors.UniqueViolation('duplicate key value violates unique constraint "catalogs_pkey"'))
    with pytest.raises(ConcurrentUpdateError) as raised:
        raise_place_write_refused(refusal, "catalog iceberg", discovery_policy_id=None, maintenance_policy_id=None)
    assert str(raised.value) == "catalog iceberg was changed by someone else"
    assert not isinstance(raised.value, ConflictError)
    assert raised.value.__cause__ is refusal


DP = TableDiscoveryPolicyId("dp-00000000000000000000000001")
MP = TableMaintenancePolicyId("mp-00000000000000000000000001")


@pytest.mark.parametrize(
    ("discovery", "maintenance", "message"),
    [
        (DP, None, f"discovery policy {DP.value} held by catalog iceberg no longer exists"),
        (None, MP, f"maintenance policy {MP.value} held by catalog iceberg no longer exists"),
        (
            DP,
            MP,
            f"discovery policy {DP.value} or maintenance policy {MP.value} held by catalog iceberg no longer exists",
        ),
        (None, None, "a policy held by catalog iceberg no longer exists"),
    ],
)
def test_a_missing_policy_is_a_conflict_in_plain_words(discovery, maintenance, message):
    """A policy deleted since the place was read names the policies the place holds, not the constraint."""
    refusal = _refusal(psycopg.errors.ForeignKeyViolation('insert violates foreign key constraint "catalogs_fkey"'))
    with pytest.raises(ConflictError) as raised:
        raise_place_write_refused(
            refusal, "catalog iceberg", discovery_policy_id=discovery, maintenance_policy_id=maintenance
        )
    assert str(raised.value) == message
    assert raised.value.__cause__ is refusal


def test_any_other_refusal_is_raised_as_it_is():
    """A refusal no aggregate can cause (a null in a required column) is a server bug, never a 409."""
    refusal = _refusal(psycopg.errors.NotNullViolation("null value in column"))
    with pytest.raises(IntegrityError) as raised:
        raise_place_write_refused(refusal, "catalog iceberg", discovery_policy_id=None, maintenance_policy_id=None)
    assert raised.value is refusal
