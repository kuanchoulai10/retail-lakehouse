from sqlalchemy import Boolean, DateTime, String

from adapter.outbound.sql.jobs_table import jobs_table


def test_table_name():
    assert jobs_table.name == "jobs"


def test_primary_key_is_id():
    pks = [c.name for c in jobs_table.primary_key]
    assert pks == ["id"]


def test_has_expected_columns():
    names = {c.name for c in jobs_table.columns}
    assert names == {
        "id",
        "job_type",
        "catalog",
        "table",
        "job_config",
        "cron",
        "enabled",
        "created_at",
        "updated_at",
    }


def test_id_is_string_not_null():
    col = jobs_table.c.id
    assert isinstance(col.type, String)
    assert col.nullable is False


def test_enabled_is_boolean():
    assert isinstance(jobs_table.c.enabled.type, Boolean)


def test_cron_is_nullable():
    assert jobs_table.c.cron.nullable is True


def test_timestamps_are_tz_aware():
    assert isinstance(jobs_table.c.created_at.type, DateTime)
    assert jobs_table.c.created_at.type.timezone is True
    assert isinstance(jobs_table.c.updated_at.type, DateTime)
    assert jobs_table.c.updated_at.type.timezone is True
