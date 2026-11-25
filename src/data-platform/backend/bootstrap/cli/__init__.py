"""The ``glac`` command: one subcommand per backend role."""

from __future__ import annotations

from bootstrap.cli.glac import main
from bootstrap.cli.role_command import RoleCommand
from bootstrap.cli.role_commands import ROLE_COMMANDS

__all__ = ["ROLE_COMMANDS", "RoleCommand", "main"]
