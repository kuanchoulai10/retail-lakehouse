from adapter.inbound.web.job.dto import JobApiRequest


def test_valid_rewrite_data_files_request():
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
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
    )
    assert req.rewrite_data_files is None
    assert req.expire_snapshots is None


def test_cron_field_accepted():
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
        cron="0 2 * * *",
    )
    assert req.cron == "0 2 * * *"


def test_defaults():
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        rewrite_data_files={"table": "inventory.orders"},
    )
    assert req.cron is None
