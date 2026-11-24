"""Maintenance requests the platform refuses before it looks anything up, and records it does not have."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx

pytestmark = pytest.mark.critical

TABLE = "00000000-0000-4000-8000-000000000000"
RECONCILIATION = "rc-01jd0000000000000000000000"


def test_an_unknown_priority_is_refused(api: httpx.Client):
    """P0 to P3 are the priorities; P4 for a table and P9 for a manual run are 422, whatever the table."""
    table = api.put(f"/v1/tables/{TABLE}/priority", json={"priority": "P4"})
    assert table.status_code == 422, table.text
    run = api.post(f"/v1/tables/{TABLE}/maintenance", json={"operations": ["rewrite_data_files"], "priority": "P9"})
    assert run.status_code == 422, run.text


def test_an_unknown_reconciliation_is_not_found(api: httpx.Client):
    """A well-formed reconciliation id nobody recorded is the handler's 404, not the router's."""
    reply = api.get(f"/v1/table-reconciliations/{RECONCILIATION}")
    assert reply.status_code == 404, reply.text
    assert reply.json() != {"detail": "Not Found"}, "no route answered, not the handler"
