"""Test interrupt_on_sigterm, which lets a pod's SIGTERM unwind pytest so the cleanup runs."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]

SCENARIO = """
import os
import signal
import time

import pytest

from e2e.support import CleanupStack, interrupt_on_sigterm

interrupt_on_sigterm()


@pytest.fixture
def cleanup():
    stack = CleanupStack()
    yield stack
    stack.run()


def test_terminated_half_way(cleanup):
    cleanup.push("mark", lambda: open({mark!r}, "w").write("cleaned"))
    os.kill(os.getpid(), signal.SIGTERM)
    time.sleep(30)
"""


def test_a_terminated_run_still_runs_the_cleanup(tmp_path):
    """The kubelet's SIGTERM (deadline, eviction, pod delete) ends the run through its cleanup."""
    mark = tmp_path / "mark"
    scenario = tmp_path / "test_terminated.py"
    scenario.write_text(textwrap.dedent(SCENARIO.format(mark=str(mark))))
    finished = subprocess.run(
        [sys.executable, "-m", "pytest", str(scenario), "-p", "no:cacheprovider", "-q"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(BACKEND)},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert mark.read_text() == "cleaned", finished.stdout + finished.stderr
    assert finished.returncode != 0
