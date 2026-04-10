"""Stub: re-exports from new locations for backward compatibility.

status_from_k8s tests -> tests.jobs.adapter.outbound.k8s.test_status_mapper
JobResponse tests -> tests.jobs.domain.test_job_status (already exists separately)
"""

from tests.jobs.adapter.outbound.k8s.test_status_mapper import *  # noqa: F401, F403
from tests.jobs.domain.test_job_status import *  # noqa: F401, F403
