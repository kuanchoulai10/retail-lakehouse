from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.repos import get_jobs_repo
from adapter.outbound.k8s.k8s_jobs_repo import K8sJobsRepo
from shared.configs import AppSettings


def test_get_jobs_repo_returns_k8s_jobs_repo():
    mock_api = MagicMock()
    settings = AppSettings()

    result = get_jobs_repo(api=mock_api, settings=settings)

    assert isinstance(result, K8sJobsRepo)
