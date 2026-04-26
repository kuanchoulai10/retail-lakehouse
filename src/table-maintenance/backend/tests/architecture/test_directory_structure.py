"""Guard test: backend top-level directories match hexagonal architecture."""

from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]

EXPECTED_TOP_LEVEL = {"adapter", "application", "base", "bootstrap"}


class TestDirectoryStructure:
    """Verify the backend follows the target hexagonal layout."""

    @pytest.mark.parametrize("directory", sorted(EXPECTED_TOP_LEVEL))
    def test_required_directories_exist(self, directory: str):
        assert (BACKEND / directory).is_dir(), (
            f"Missing required directory: {directory}/"
        )

    def test_core_directory_does_not_exist(self):
        assert not (BACKEND / "core").is_dir(), (
            "core/ should not exist — its contents should be in "
            "adapter/, application/, base/, and bootstrap/"
        )

    @pytest.mark.parametrize(
        "subdir",
        [
            "adapter/inbound/web",
            "adapter/inbound/scheduler",
            "adapter/inbound/messaging/outbox",
            "adapter/outbound",
        ],
    )
    def test_adapter_subdirectories_exist(self, subdir: str):
        assert (BACKEND / subdir).is_dir(), f"Missing adapter subdirectory: {subdir}/"

    @pytest.mark.parametrize(
        "subdir",
        ["bootstrap/configs", "bootstrap/dependencies"],
    )
    def test_bootstrap_subdirectories_exist(self, subdir: str):
        assert (BACKEND / subdir).is_dir(), f"Missing bootstrap subdirectory: {subdir}/"

    def test_no_stale_top_level_directories(self):
        """Top-level should not have old scattered entry point dirs."""
        for stale in ("api", "scheduler", "outbox_publisher", "dependencies"):
            assert not (BACKEND / stale).is_dir(), (
                f"{stale}/ should not exist at top level — "
                f"moved to adapter/inbound/ or bootstrap/"
            )
