"""Define the ROLE_COMMANDS table."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from bootstrap.cli.role_command import RoleCommand
from bootstrap.configs import ApiSettings, EventConsumerSettings, MigrateSettings, WorkerSettings

if TYPE_CHECKING:
    import argparse


def _api(settings: Any, _arguments: argparse.Namespace) -> None:  # noqa: ANN401
    importlib.import_module("bootstrap.api").main(settings)


def _worker(settings: Any, _arguments: argparse.Namespace) -> None:  # noqa: ANN401
    importlib.import_module("bootstrap.worker").main(settings)


def _event_consumer(settings: Any, _arguments: argparse.Namespace) -> None:  # noqa: ANN401
    importlib.import_module("bootstrap.event_consumer").main(settings)


def _migrate(settings: Any, arguments: argparse.Namespace) -> None:  # noqa: ANN401
    importlib.import_module("bootstrap.migrate").main(settings, wait=arguments.wait)


ROLE_COMMANDS: tuple[RoleCommand, ...] = (
    RoleCommand("api", ApiSettings, _api, "serve the control plane API"),
    RoleCommand("worker", WorkerSettings, _worker, "run the Temporal worker"),
    RoleCommand("event-consumer", EventConsumerSettings, _event_consumer, "turn catalog events into table hints"),
    RoleCommand("migrate", MigrateSettings, _migrate, "create the schema and seed the default policies"),
)
