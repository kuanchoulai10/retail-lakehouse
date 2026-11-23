"""Shared fixtures for top-level tests.

Under mutmut every mutated module imports ``mutmut`` for its trampolines, and the
active mutant lives in that module's state. Workflows run in Temporal's sandbox,
which re-imports modules, so ``mutmut`` is passed through it: the sandboxed code
then sees the mutant mutmut activated, and the import touches no restricted call.
"""

from __future__ import annotations

import sys

from temporalio.worker.workflow_sandbox import SandboxRestrictions

if "mutmut" in sys.modules:
    SandboxRestrictions.default.passthrough_modules.add("mutmut")
