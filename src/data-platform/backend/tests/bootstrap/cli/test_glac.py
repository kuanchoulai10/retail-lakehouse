"""Test that ``glac`` picks the role from its subcommand and hands it settings loaded for that role."""

from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING, Any

import pytest

from bootstrap.cli import main
from bootstrap.configs import ApiSettings, EventConsumerSettings, MigrateSettings, WorkerSettings

if TYPE_CHECKING:
    from pathlib import Path

ROLES = [
    ("api", "bootstrap.api", ApiSettings),
    ("worker", "bootstrap.worker", WorkerSettings),
    ("event-consumer", "bootstrap.event_consumer", EventConsumerSettings),
    ("migrate", "bootstrap.migrate", MigrateSettings),
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.upper().startswith("GLAC_"):
            monkeypatch.delenv(name)


def _record(monkeypatch: pytest.MonkeyPatch, module: str) -> list[tuple[Any, dict[str, Any]]]:
    calls: list[tuple[Any, dict[str, Any]]] = []
    monkeypatch.setattr(importlib.import_module(module), "main", lambda settings, **kw: calls.append((settings, kw)))
    return calls


def _config(tmp_path: Path, text: str = "log_level: INFO\n") -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_help_lists_the_four_subcommands(capsys: pytest.CaptureFixture[str]):
    """``glac --help`` names every role."""
    with pytest.raises(SystemExit) as raised:
        main(["--help"])

    assert raised.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: glac")
    for name in ("api", "worker", "event-consumer", "migrate"):
        assert name in out


def test_no_subcommand_prints_the_help_and_fails(capsys: pytest.CaptureFixture[str]):
    """``glac`` alone does not guess a role."""
    with pytest.raises(SystemExit) as raised:
        main([])

    assert raised.value.code == 2
    assert "event-consumer" in capsys.readouterr().out


@pytest.mark.parametrize(("name", "module", "settings_cls"), ROLES)
def test_each_subcommand_runs_its_role_with_its_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, module: str, settings_cls: type
):
    """Each subcommand runs its role's main with that role's settings, read from the given file."""
    calls = _record(monkeypatch, module)

    main([name, f"--config-file={_config(tmp_path, 'log_level: WARNING\n')}"])

    assert len(calls) == 1
    assert type(calls[0][0]) is settings_cls
    assert calls[0][0].log_level == "WARNING"


def test_flags_after_the_subcommand_set_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A settings flag after the subcommand wins over the file."""
    calls = _record(monkeypatch, "bootstrap.worker")

    main(["worker", f"--config-file={_config(tmp_path)}", "--log-level=DEBUG", "--temporal.namespace=tm"])

    assert calls[0][0].log_level == "DEBUG"
    assert calls[0][0].temporal.namespace == "tm"


def test_an_unknown_variable_exits_with_its_name(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    """A misspelt variable stops the role before it starts, naming the variable."""
    calls = _record(monkeypatch, "bootstrap.worker")
    monkeypatch.setenv("GLAC_MAINTENANCE__MAX_ATTEMPT", "9")

    with pytest.raises(SystemExit) as raised:
        main(["worker"])

    assert raised.value.code == 2
    assert "GLAC_MAINTENANCE__MAX_ATTEMPT" in capsys.readouterr().err
    assert calls == []


def test_an_unknown_key_in_the_file_exits_with_its_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """A misspelt key in the settings file stops the role, naming where it is."""
    calls = _record(monkeypatch, "bootstrap.api")

    with pytest.raises(SystemExit) as raised:
        main(["api", f"--config-file={_config(tmp_path, 'temporal:\n  adress: x\n')}"])

    assert raised.value.code == 2
    assert "temporal.adress" in capsys.readouterr().err
    assert calls == []


def test_a_missing_settings_file_exits_with_its_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """A settings file that is not there stops the role instead of running on defaults."""
    absent = tmp_path / "absent.yaml"

    with pytest.raises(SystemExit) as raised:
        main(["migrate", f"--config-file={absent}"])

    assert raised.value.code == 2
    assert str(absent) in capsys.readouterr().err


@pytest.mark.parametrize(("argv", "wait"), [(["migrate", "--wait"], True), (["migrate"], False)])
def test_migrate_wait_reaches_the_role_as_wait(monkeypatch: pytest.MonkeyPatch, argv: list[str], wait: bool):
    """``glac migrate --wait`` asks the migrate role to wait for the schema instead of creating it."""
    calls = _record(monkeypatch, "bootstrap.migrate")

    main(argv)

    assert calls[0][1] == {"wait": wait}
