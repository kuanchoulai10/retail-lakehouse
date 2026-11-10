"""Guard test: `.importlinter` has the ring/adapter contracts and no exemptions."""

from __future__ import annotations

import configparser
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / ".importlinter"
CONTRACT_PREFIX = "importlinter:contract:"
SINGLE_CONTEXT = re.compile(r"\bcontext\.(?!\*)")

REQUIRED_CONTRACTS = {
    "domain-pure",
    "application-ring-order",
    "application-no-outer-rings",
    "application-outer-rings-pydantic-free",
    "adapters-see-only-ports",
    "adapter-directions-separate",
    "hybrid-directions-separate",
    "hybrid-contracts-neutral",
    "hybrid-contracts-private",
    "temporal-workflows-sandbox-safe",
    "inbound-channels-independent",
    "adapters-no-bootstrap",
    "configs-leaf",
    "base-isolation",
    "application-exceptions-leaf",
}


def _config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    assert parser.read(CONFIG_PATH), f"{CONFIG_PATH} not found"
    return parser


def test_no_ignore_imports():
    """No import-linter contract carries an ignore_imports exemption."""
    parser = _config()
    offenders = [s for s in parser.sections() if parser.has_option(s, "ignore_imports")]
    assert offenders == [], f"ignore_imports is an exemption; remove it from {offenders}"


def test_required_contracts_present():
    """Every required import-linter contract is configured."""
    contracts = {
        section.removeprefix(CONTRACT_PREFIX) for section in _config().sections() if section.startswith(CONTRACT_PREFIX)
    }
    missing = REQUIRED_CONTRACTS - contracts
    assert not missing, f"missing import-linter contracts: {sorted(missing)}"


def test_root_packages_are_base_bootstrap_context():
    """The import-linter root packages are base, bootstrap and context."""
    roots = set(_config().get("importlinter", "root_packages").split())
    assert roots == {"base", "bootstrap", "context"}


def test_contracts_name_no_single_context():
    """Every context reference is ``context.*``, so each contract covers every context."""
    parser = _config()
    offenders = [
        f"{section}.{option}: {line}"
        for section in parser.sections()
        if section.startswith(CONTRACT_PREFIX)
        for option, value in parser.items(section)
        for line in value.split()
        if SINGLE_CONTEXT.search(line)
    ]
    assert offenders == [], "\n".join(offenders)
