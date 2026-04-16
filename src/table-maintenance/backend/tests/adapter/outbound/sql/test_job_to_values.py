from datetime import UTC, datetime

from adapter.outbound.sql.job_to_values import job_to_values
from application.domain.model.job import Job
from application.domain.model.job_id import JobId
from application.domain.model.job_status import JobStatus
from application.domain.model.job_type import JobType


def _make_job() -> Job:
    return Job(
        id=JobId(value="abc1234567"),
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.PENDING,
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        updated_at=datetime(2026, 4, 10, tzinfo=UTC),
        catalog="retail",
        table="inventory.orders",
        job_config={"rewrite_all": True},
        cron="0 2 * * *",
        enabled=True,
    )


def test_values_has_all_columns():
    values = job_to_values(_make_job())
    assert set(values.keys()) == {
        "id",
        "job_type",
        "status",
        "catalog",
        "table",
        "job_config",
        "cron",
        "enabled",
        "created_at",
        "updated_at",
    }


def test_enum_fields_serialized_as_strings():
    values = job_to_values(_make_job())
    assert values["job_type"] == "rewrite_data_files"
    assert values["status"] == "pending"


def test_scalars_passthrough():
    values = job_to_values(_make_job())
    assert values["id"] == "abc1234567"
    assert values["catalog"] == "retail"
    assert values["table"] == "inventory.orders"
    assert values["cron"] == "0 2 * * *"
    assert values["enabled"] is True
    assert values["job_config"] == {"rewrite_all": True}
