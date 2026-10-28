"""Guard test: `.importlinter` has the ring/adapter contracts and no exemptions."""

from __future__ import annotations

import configparser
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / ".importlinter"
CONTRACT_PREFIX = "importlinter:contract:"

REQUIRED_CONTRACTS = {
    "domain-pure",
    "application-ring-order",
    "application-no-outer-rings",
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
}


def _config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    assert parser.read(CONFIG_PATH), f"{CONFIG_PATH} not found"
    return parser


def test_no_ignore_imports():
    parser = _config()
    offenders = [s for s in parser.sections() if parser.has_option(s, "ignore_imports")]
    assert offenders == [], (
        f"ignore_imports is an exemption; remove it from {offenders}"
    )


def test_required_contracts_present():
    contracts = {
        section.removeprefix(CONTRACT_PREFIX)
        for section in _config().sections()
        if section.startswith(CONTRACT_PREFIX)
    }
    missing = REQUIRED_CONTRACTS - contracts
    assert not missing, f"missing import-linter contracts: {sorted(missing)}"
