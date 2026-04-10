from jobs.adapter.inbound.web.dto import JobApiRequest


def test_valid_rewrite_data_files_request():
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
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
        spark_conf={},
    )
    assert req.rewrite_data_files is None
    assert req.expire_snapshots is None


def test_cron_field_accepted():
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={},
        rewrite_data_files={"table": "inventory.orders"},
        cron="0 2 * * *",
    )
    assert req.cron == "0 2 * * *"


def test_defaults():
    req = JobApiRequest(
        job_type="rewrite_data_files",
        catalog="retail",
        spark_conf={},
        rewrite_data_files={"table": "inventory.orders"},
    )
    assert req.driver_memory == "512m"
    assert req.executor_memory == "1g"
    assert req.executor_instances == 1
    assert req.cron is None
