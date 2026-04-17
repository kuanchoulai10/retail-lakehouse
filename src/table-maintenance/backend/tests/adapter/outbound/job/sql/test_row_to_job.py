from datetime import UTC, datetime

from adapter.outbound.job.sql.row_to_job import row_to_job
from application.domain.model.job import JobId, JobType


def test_row_maps_to_job():
    row = {
        "id": "abc1234567",
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "table": "inventory.orders",
        "job_config": {"rewrite_all": True},
        "cron": None,
        "enabled": True,
        "created_at": datetime(2026, 4, 10, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 10, tzinfo=UTC),
    }

    job = row_to_job(row)

    assert job.id == JobId(value="abc1234567")
    assert job.job_type == JobType.REWRITE_DATA_FILES
    assert job.catalog == "retail"
    assert job.table == "inventory.orders"
    assert job.job_config == {"rewrite_all": True}
    assert job.cron is None
    assert job.enabled is True
    assert job.created_at == datetime(2026, 4, 10, tzinfo=UTC)
    assert job.updated_at == datetime(2026, 4, 10, tzinfo=UTC)


def test_row_preserves_cron():
    row = {
        "id": "x",
        "job_type": "rewrite_data_files",
        "catalog": "",
        "table": "",
        "job_config": {},
        "cron": "0 2 * * *",
        "enabled": False,
        "created_at": datetime(2026, 4, 10, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 10, tzinfo=UTC),
    }
    assert row_to_job(row).cron == "0 2 * * *"
