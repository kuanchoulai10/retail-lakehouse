import pytest
from jobs.adapter.inbound.web.dto import JobRequest
from jobs.domain import JobType
from jobs.domain.config.expire_snapshots import ExpireSnapshotsConfig
from jobs.domain.config.rewrite_data_files import RewriteDataFilesConfig
from pydantic import ValidationError


def test_valid_rewrite_data_files_request():
    req = JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
    )
    assert req.job_type == JobType.REWRITE_DATA_FILES
    assert req.catalog == "retail"
    assert req.rewrite_data_files is not None
    assert req.rewrite_data_files.table == "inventory.orders"


def test_missing_config_for_job_type_raises():
    with pytest.raises(ValidationError, match="rewrite_data_files"):
        JobRequest(
            job_type=JobType.REWRITE_DATA_FILES,
            catalog="retail",
            spark_conf={},
        )


def test_wrong_config_for_job_type_raises():
    with pytest.raises(ValidationError):
        JobRequest(
            job_type=JobType.REWRITE_DATA_FILES,
            catalog="retail",
            spark_conf={},
            expire_snapshots=ExpireSnapshotsConfig(table="inventory.orders"),
        )


def test_cron_field_accepted():
    req = JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
        cron="0 2 * * *",
    )
    assert req.cron == "0 2 * * *"


def test_defaults():
    req = JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
    )
    assert req.driver_memory == "512m"
    assert req.executor_memory == "1g"
    assert req.executor_instances == 1
    assert req.cron is None
