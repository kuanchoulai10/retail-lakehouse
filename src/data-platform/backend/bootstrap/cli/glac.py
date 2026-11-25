"""Provide the glac command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from bootstrap.cli.role_commands import ROLE_COMMANDS
from bootstrap.configs import UnknownSettingError, load_role_settings

if TYPE_CHECKING:
    from collections.abc import Sequence

USAGE_ERROR = 2


def main(argv: Sequence[str] | None = None) -> None:
    """Run the role the subcommand names, on the settings loaded for that role.

    Flags the subcommand itself does not take are settings flags (``--log-level=DEBUG``,
    ``--temporal.namespace=tm``) and win over the environment and the settings file.
    """
    parser = argparse.ArgumentParser(prog="glac", description="Run one role of the table maintenance backend.")
    subcommands = parser.add_subparsers(dest="role", metavar="{" + ",".join(c.name for c in ROLE_COMMANDS) + "}")
    for command in ROLE_COMMANDS:
        sub = subcommands.add_parser(command.name, help=command.help, allow_abbrev=False)
        sub.add_argument("--config-file", type=Path, help="the role's YAML settings file")
        if command.name == "migrate":
            sub.add_argument("--wait", action="store_true", help="wait until the schema is ready; create nothing")
    arguments, settings_flags = parser.parse_known_args(sys.argv[1:] if argv is None else list(argv))
    command = next((c for c in ROLE_COMMANDS if c.name == arguments.role), None)
    if command is None:
        parser.print_help()
        raise SystemExit(USAGE_ERROR)
    try:
        settings = load_role_settings(command.settings_cls, config_file=arguments.config_file, cli_args=settings_flags)
    except (UnknownSettingError, ValidationError) as error:
        print(f"glac {command.name}: {error}", file=sys.stderr)  # noqa: T201
        raise SystemExit(USAGE_ERROR) from error
    command.run(settings, arguments)
