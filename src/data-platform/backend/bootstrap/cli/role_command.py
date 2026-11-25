"""Define the RoleCommand value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable

    from bootstrap.configs import RoleSettings


@dataclass(frozen=True)
class RoleCommand:
    """One ``glac`` subcommand: the role it runs and the settings class that role reads."""

    name: str
    settings_cls: type[RoleSettings]
    run: Callable[[Any, argparse.Namespace], None]
    help: str
