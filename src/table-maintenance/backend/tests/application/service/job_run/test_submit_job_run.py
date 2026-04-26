"""Tests for SubmitJobRunService."""

from unittest.mock import MagicMock

from application.port.inbound.job_run.submit_job_run import (
    SubmitJobRunInput,
    SubmitJobRunUseCase,
)
from application.port.outbound.job_run.job_submission import JobSubmission
from application.service.job_run.submit_job_run import SubmitJobRunService


def _make_input(**overrides) -> SubmitJobRunInput:
    defaults = {
        "run_id": "r1",
        "job_id": "j1",
        "job_type": "compaction",
        "catalog": "warehouse",
        "table": "orders",
        "job_config": {"option": "value"},
        "driver_memory": "1g",
        "executor_memory": "2g",
        "executor_instances": 3,
        "cron_expression": "0 0 * * *",
    }
    defaults.update(overrides)
    return SubmitJobRunInput(**defaults)


class TestSubmitJobRunService:
    """Tests for SubmitJobRunService."""

    def test_submits_job_with_correct_mapping(self) -> None:
        executor = MagicMock()
        service = SubmitJobRunService(executor)
        inp = _make_input()

        service.execute(inp)

        executor.submit.assert_called_once_with(
            JobSubmission(
                run_id="r1",
                job_id="j1",
                job_type="compaction",
                catalog="warehouse",
                table="orders",
                job_config={"option": "value"},
                driver_memory="1g",
                executor_memory="2g",
                executor_instances=3,
                cron_expression="0 0 * * *",
            )
        )

    def test_submits_job_with_no_cron(self) -> None:
        executor = MagicMock()
        service = SubmitJobRunService(executor)
        inp = _make_input(cron_expression=None)

        service.execute(inp)

        submission = executor.submit.call_args[0][0]
        assert submission.cron_expression is None

    def test_implements_use_case_interface(self) -> None:
        executor = MagicMock()
        service = SubmitJobRunService(executor)
        assert isinstance(service, SubmitJobRunUseCase)
