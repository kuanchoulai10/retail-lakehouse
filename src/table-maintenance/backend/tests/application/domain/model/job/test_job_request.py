"""Tests for JobApiRequest."""

from api.adapter.inbound.web.job.dto import JobApiRequest


def test_valid_rewrite_data_files_request():
    """Verify that a valid rewrite_data_files request stores all fields."""
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
    )
    assert req.job_type == "rewrite_data_files"
    assert req.catalog == "retail"
    assert req.rewrite_data_files is not None
    assert req.rewrite_data_files["table"] == "inventory.orders"


def test_missing_config_fields_default_to_none():
    """Verify that config fields default to None when not provided."""
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
    )
    assert req.rewrite_data_files is None
    assert req.expire_snapshots is None


def test_cron_field_accepted():
    """Verify that the cron field is accepted and stored."""
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
        cron="0 2 * * *",
    )
    assert req.cron == "0 2 * * *"


def test_defaults():
    """Verify that optional fields default to None."""
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
    )
    assert req.cron is None
