"""Test remove_prefix, which removes a storage prefix a scenario wrote under."""

from __future__ import annotations

import pytest
from pyarrow import fs

from e2e.support import remove_prefix


def test_the_prefix_and_everything_under_it_is_removed(tmp_path):
    """Files, nested directories and the directory itself are gone."""
    (tmp_path / "ns" / "t" / "data").mkdir(parents=True)
    (tmp_path / "ns" / "t" / "data" / "f.parquet").write_text("x")
    remove_prefix(fs.LocalFileSystem(), str(tmp_path / "ns"))
    assert not (tmp_path / "ns").exists()


def test_a_missing_prefix_is_left_alone(tmp_path):
    """Nothing to remove is not an error."""
    remove_prefix(fs.LocalFileSystem(), str(tmp_path / "never-written"))


class _KeepsTheMarker(fs.LocalFileSystem):
    def delete_dir(self, path: str) -> None:
        """Remove the contents but keep the directory, as a store that keeps a marker would."""
        self.delete_dir_contents(path)


def test_a_prefix_still_there_after_the_delete_fails(tmp_path):
    """A leftover marker fails the cleanup instead of passing for a removal."""
    (tmp_path / "ns").mkdir()
    with pytest.raises(AssertionError, match=r"ns is still there after its removal"):
        remove_prefix(_KeepsTheMarker(), str(tmp_path / "ns"))
