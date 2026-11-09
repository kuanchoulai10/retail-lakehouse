"""Test the table commits route with a stub use case."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    ListTableCommitsUseCaseInput,
    ListTableCommitsUseCaseOutput,
    ListTableCommitsUseCaseOutputItem,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)


def _output() -> ListTableCommitsUseCaseOutput:
    item = ListTableCommitsUseCaseOutputItem(
        snapshot_id=7,
        parent_id=None,
        committed_at=NOW,
        operation="append",
        writer="unknown",
        added_records=10,
        deleted_records=None,
        added_data_files=2,
        deleted_data_files=None,
        added_delete_files=None,
        removed_delete_files=None,
        summary={"added-records": "10"},
    )
    return ListTableCommitsUseCaseOutput(items=[item], truncated=True)


def test_commits_returns_200() -> None:
    """The commits route returns the commits and whether the list was truncated."""
    stub = StubUseCase(_output())
    client = build_client(list_table_commits=stub)

    response = client.get("/v1/tables/u-1/commits")

    body = response.json()
    assert response.status_code == 200
    assert body["truncated"] is True
    assert body["items"][0]["snapshot_id"] == "7"
    assert body["items"][0]["parent_id"] is None
    assert body["items"][0]["added_records"] == 10
    assert body["items"][0]["committed_at"].startswith("2026-10-24T12:00:00")
    assert stub.requests == [ListTableCommitsUseCaseInput(uuid="u-1")]


def test_commits_return_large_snapshot_ids_as_exact_strings() -> None:
    """Snapshot ids too large for a JSON number are returned as exact strings."""
    output = _output()
    item = dataclasses.replace(output.items[0], snapshot_id=3051729675574597004, parent_id=3051729675574597003)
    stub = StubUseCase(dataclasses.replace(output, items=[item]))
    client = build_client(list_table_commits=stub)

    body = client.get("/v1/tables/u-1/commits").json()

    assert body["items"][0]["snapshot_id"] == "3051729675574597004"
    assert body["items"][0]["parent_id"] == "3051729675574597003"


def test_commits_limit_over_1000_is_422() -> None:
    """A commits limit of zero or above 1000 is rejected with 422."""
    client = build_client(list_table_commits=StubUseCase(_output()))

    assert client.get("/v1/tables/u-1/commits?limit=1001").status_code == 422
    assert client.get("/v1/tables/u-1/commits?limit=0").status_code == 422


def test_commits_since_is_forwarded() -> None:
    """The since and limit query parameters are forwarded to the use case."""
    stub = StubUseCase(_output())
    client = build_client(list_table_commits=stub)

    response = client.get("/v1/tables/u-1/commits", params={"limit": 5, "since": "2026-10-24T12:00:00Z"})

    assert response.status_code == 200
    assert stub.requests[0].limit == 5
    assert stub.requests[0].since == NOW


def test_commits_bad_since_is_422() -> None:
    """A since value that is not a timestamp is rejected with 422."""
    client = build_client(list_table_commits=StubUseCase(_output()))

    assert client.get("/v1/tables/u-1/commits?since=yesterday").status_code == 422


def test_commits_404_detail() -> None:
    """A not found error from the use case becomes a 404 carrying its message."""
    message = "table iceberg.sales.orders is not in the catalog"
    client = build_client(list_table_commits=StubUseCase(error=NotFoundError(message)))

    response = client.get("/v1/tables/u-1/commits")

    assert response.status_code == 404
    assert response.json()["detail"] == message


def test_commits_forward_the_time_window_and_writer() -> None:
    """The since, before and writer query parameters reach the use case."""
    stub = StubUseCase(_output())
    client = build_client(list_table_commits=stub)

    response = client.get(
        "/v1/tables/u-1/commits",
        params={"since": "2026-10-01T00:00:00Z", "before": "2026-10-08T00:00:00Z", "writer": "spark"},
    )

    assert response.status_code == 200
    assert stub.requests == [
        ListTableCommitsUseCaseInput(
            uuid="u-1",
            since=datetime(2026, 10, 1, tzinfo=UTC),
            before=datetime(2026, 10, 8, tzinfo=UTC),
            writer="spark",
        )
    ]


def test_commits_reject_an_unknown_writer() -> None:
    """A writer other than the known ones is a validation error."""
    client = build_client(list_table_commits=StubUseCase(_output()))

    response = client.get("/v1/tables/u-1/commits", params={"writer": "flink"})

    assert response.status_code == 422
