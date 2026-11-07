from __future__ import annotations

import json

import pytest

from job_request import JobRequest


@pytest.fixture
def make_request():
    def _make(**overrides) -> JobRequest:
        data = {
            "app_name": "tm-1",
            "run_id": "run-1",
            "operation": "rewrite_data_files",
            "attempt": 1,
            "catalog": "iceberg",
            "namespace": "sales.eu",
            "table": "orders",
            "where": [],
            "procedure_args": {
                "target-file-size-bytes": 536870912,
                "min-input-files": 2,
                "partial-progress.enabled": True,
            },
            "callback_url": "http://cb/result",
        }
        data.update(overrides)
        return JobRequest.from_json(json.dumps(data))

    return _make
