"""Guard test: backend top-level directories match hexagonal architecture."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.contexts import context_dir, context_names

BACKEND = Path(__file__).resolve().parents[2]

EXPECTED_TOP_LEVEL = {"context", "base", "bootstrap"}
EXPECTED_CONTEXT_LAYERS = {"application", "adapter"}
REQUIRED_ADAPTER_SUBDIRECTORIES = (
    "adapter/inbound/web",
    "adapter/outbound",
)


def missing_adapter_subdirectories(context_root: Path) -> list[str]:
    """Return the required adapter subdirectories the context at ``context_root`` lacks.

    The event consumer and the hybrid technologies are optional, so they are not listed.
    """
    return [subdir for subdir in REQUIRED_ADAPTER_SUBDIRECTORIES if not (context_root / subdir).is_dir()]


class TestDirectoryStructure:
    """Verify the backend follows the target hexagonal layout."""

    @pytest.mark.parametrize("directory", sorted(EXPECTED_TOP_LEVEL))
    def test_required_directories_exist(self, directory: str):
        """Each required top-level directory exists."""
        assert (BACKEND / directory).is_dir(), f"Missing required directory: {directory}/"

    def test_core_directory_does_not_exist(self):
        """The retired core directory is gone."""
        assert not (BACKEND / "core").is_dir(), (
            "core/ should not exist — its contents should be in adapter/, application/, base/, and bootstrap/"
        )

    def test_context_root_holds_a_context(self):
        """The context directory holds at least one bounded context."""
        assert context_names(), "context/ holds no bounded context"

    @pytest.mark.parametrize("context", context_names())
    def test_context_holds_application_and_adapter(self, context: str):
        """Each context contains exactly the application and adapter layers."""
        layers = {
            child.name for child in context_dir(context).iterdir() if child.is_dir() and child.name != "__pycache__"
        }
        assert layers == EXPECTED_CONTEXT_LAYERS, (
            f"context/{context} must hold exactly {sorted(EXPECTED_CONTEXT_LAYERS)}, found {sorted(layers)}"
        )

    @pytest.mark.parametrize("context", context_names())
    def test_adapter_subdirectories_exist(self, context: str):
        """Each context has a web inbound adapter and an outbound adapter directory."""
        assert missing_adapter_subdirectories(context_dir(context)) == []

    def test_context_without_hybrid_or_event_consumer_passes_layout(self, tmp_path: Path):
        """A context with only web inbound and outbound adapters meets the layout rules."""
        (tmp_path / "adapter" / "inbound" / "web").mkdir(parents=True)
        (tmp_path / "adapter" / "outbound").mkdir(parents=True)
        assert missing_adapter_subdirectories(tmp_path) == []

    def test_context_without_web_fails_layout(self, tmp_path: Path):
        """A context that lacks the web inbound adapter is reported."""
        (tmp_path / "adapter" / "outbound").mkdir(parents=True)
        assert missing_adapter_subdirectories(tmp_path) == ["adapter/inbound/web"]

    @pytest.mark.parametrize(
        "subdir",
        ["bootstrap/configs", "bootstrap/container"],
    )
    def test_bootstrap_subdirectories_exist(self, subdir: str):
        """Each required bootstrap subdirectory exists."""
        assert (BACKEND / subdir).is_dir(), f"Missing bootstrap subdirectory: {subdir}/"

    def test_no_stale_top_level_directories(self):
        """Top-level should not have old scattered entry point dirs."""
        for stale in ("api", "scheduler", "outbox_publisher", "dependencies"):
            assert not (BACKEND / stale).is_dir(), (
                f"{stale}/ should not exist at top level — moved to adapter/inbound/ or bootstrap/"
            )

    def test_no_bootstrap_dependencies_directory(self):
        """Composition lives in bootstrap/container; the old providers are gone."""
        assert not list((BACKEND / "bootstrap" / "dependencies").glob("*.py"))
