"""Test that a role's settings come from its file, the environment and its flags, and refuse unknown names."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from bootstrap.configs import (
    ApiSettings,
    EventConsumerSettings,
    UnknownSettingError,
    WorkerSettings,
    load_role_settings,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.upper().startswith("GLAC_"):
            monkeypatch.delenv(name)


def _config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_the_file_sets_what_the_defaults_do_not(tmp_path: Path):
    """A key in the file wins over its default; the keys it leaves out keep theirs."""
    settings = load_role_settings(WorkerSettings, config_file=_config(tmp_path, "temporal:\n  address: from-file\n"))

    assert settings.temporal.address == "from-file"
    assert settings.temporal.namespace == "default"


def test_env_beats_the_file_and_keeps_the_file_siblings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """An environment variable replaces one key of a block; the file's other keys of that block stay."""
    monkeypatch.setenv("GLAC_TEMPORAL__ADDRESS", "from-env")
    config = _config(tmp_path, "temporal:\n  address: from-file\n  namespace: n\n")

    settings = load_role_settings(WorkerSettings, config_file=config)

    assert settings.temporal.address == "from-env"
    assert settings.temporal.namespace == "n"


def test_a_flag_beats_env(monkeypatch: pytest.MonkeyPatch):
    """A command-line flag wins over the environment."""
    monkeypatch.setenv("GLAC_LOG_LEVEL", "WARNING")

    settings = load_role_settings(WorkerSettings, config_file=None, cli_args=["--log-level=DEBUG"])

    assert settings.log_level == "DEBUG"


def test_an_unknown_key_in_the_file_is_refused_with_its_path(tmp_path: Path):
    """A misspelt key inside a block fails the load and says where it is."""
    with pytest.raises(ValidationError) as raised:
        load_role_settings(WorkerSettings, config_file=_config(tmp_path, "temporal:\n  adress: x\n"))

    assert raised.value.errors()[0]["loc"] == ("temporal", "adress")
    assert raised.value.errors()[0]["type"] == "extra_forbidden"


def test_an_unknown_glac_variable_is_refused_by_name(monkeypatch: pytest.MonkeyPatch):
    """A misspelt variable fails the load instead of leaving the default in place."""
    monkeypatch.setenv("GLAC_MAINTENANCE__MAX_ATTEMPT", "9")

    with pytest.raises(UnknownSettingError, match="GLAC_MAINTENANCE__MAX_ATTEMPT"):
        load_role_settings(WorkerSettings, config_file=None)


def test_a_variable_of_another_role_is_refused(monkeypatch: pytest.MonkeyPatch):
    """The API has no Kafka settings, so its Kafka variable is unknown; the event consumer takes it."""
    monkeypatch.setenv("GLAC_KAFKA__TOPIC", "t")

    with pytest.raises(UnknownSettingError, match="GLAC_KAFKA__TOPIC"):
        load_role_settings(ApiSettings, config_file=None)
    assert load_role_settings(EventConsumerSettings, config_file=None).kafka.topic == "t"


def test_a_lowercase_variable_and_a_whole_block_are_known(monkeypatch: pytest.MonkeyPatch):
    """Names compare as pydantic-settings reads them: any case, and a block given whole as JSON."""
    monkeypatch.setenv("glac_temporal__address", "x")
    monkeypatch.setenv("GLAC_SPARK__SIZE_S", '{"driver_memory": "1g", "executor_memory": "1g"}')

    settings = load_role_settings(WorkerSettings, config_file=None)

    assert settings.temporal.address == "x"
    assert settings.spark.size_s.driver_memory == "1g"


def test_a_lowercase_misspelt_variable_is_refused(monkeypatch: pytest.MonkeyPatch):
    """pydantic-settings reads names in any case, so a lowercase misspelling is checked too."""
    monkeypatch.setenv("glac_temporal__adress", "x")

    with pytest.raises(UnknownSettingError, match="glac_temporal__adress"):
        load_role_settings(WorkerSettings, config_file=None)


def test_a_missing_config_file_is_refused_by_path(tmp_path: Path):
    """A file that is not there fails the load instead of loading the defaults."""
    absent = tmp_path / "absent.yaml"

    with pytest.raises(UnknownSettingError, match=str(absent)):
        load_role_settings(WorkerSettings, config_file=absent)


def test_a_file_that_is_not_a_mapping_is_refused(tmp_path: Path):
    """A file whose top level is a list or a scalar is not a settings file."""
    with pytest.raises(UnknownSettingError, match="mapping"):
        load_role_settings(WorkerSettings, config_file=_config(tmp_path, "- a\n- b\n"))


@pytest.mark.parametrize(
    ("text", "path"),
    [
        ("database:\n  postgres:\n    db_url: postgresql://u:p@h/d\n", "database.postgres.db_url"),
        ("catalog:\n  credential: id:secret\n", "catalog.credential"),
        ("catalog:\n  s3_access_key_id: key\n", "catalog.s3_access_key_id"),
        ("catalog:\n  s3_secret_access_key: key\n", "catalog.s3_secret_access_key"),
    ],
)
def test_a_secret_in_the_file_is_refused(tmp_path: Path, text: str, path: str):
    """Secrets come from the environment only; one written in the file fails the load, naming it."""
    with pytest.raises(UnknownSettingError, match=path):
        load_role_settings(WorkerSettings, config_file=_config(tmp_path, text))


def test_an_unknown_flag_exits():
    """A misspelt flag stops the program with a usage error."""
    with pytest.raises(SystemExit) as raised:
        load_role_settings(WorkerSettings, config_file=None, cli_args=["--log-levl=DEBUG"])

    assert raised.value.code == 2
