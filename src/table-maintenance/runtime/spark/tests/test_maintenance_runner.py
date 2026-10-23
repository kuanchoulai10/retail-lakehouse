from __future__ import annotations

from maintenance_runner import run_maintenance


class _Row:
    def __init__(self, **values):
        self._values = values

    def asDict(self):
        return self._values


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def collect(self):
        return self._rows


def test_metrics_summed_across_calls(make_request):
    posted = []
    results = iter(
        [
            _Result([_Row(rewritten_data_files_count=2, note="x", rate=1.5, dry_run=True)]),
            _Result([_Row(rewritten_data_files_count=3, added_data_files_count=1)]),
        ]
    )
    code = run_maintenance(
        make_request(where=["a = 1", "a = 2"]),
        lambda _sql: next(results),
        post=lambda url, body: posted.append((url, body)) or True,
    )
    assert code == 0
    url, body = posted[0]
    assert url == "http://cb/result"
    assert body == {
        "run_id": "run-1",
        "operation": "rewrite_data_files",
        "attempt": 1,
        "succeeded": True,
        "metrics": {"rewritten_data_files_count": 5, "added_data_files_count": 1},
        "error": None,
    }


def test_failure_posts_error_and_exits_1(make_request):
    posted = []

    def boom(_sql):
        raise RuntimeError("catalog down")

    code = run_maintenance(make_request(), boom, post=lambda url, body: posted.append(body) or True)
    assert code == 1
    assert posted[0]["succeeded"] is False
    assert "catalog down" in posted[0]["error"]
    assert posted[0]["metrics"] == {}


def test_invalid_operation_posts_error_and_exits_1(make_request):
    posted = []
    code = run_maintenance(
        make_request(operation="nope"),
        lambda _sql: _Result([]),
        post=lambda url, body: posted.append(body) or True,
    )
    assert code == 1
    assert "Unsupported" in posted[0]["error"]


def test_exit_code_ignores_callback_delivery(make_request):
    code = run_maintenance(make_request(), lambda _s: _Result([]), post=lambda url, body: False)
    assert code == 0


def test_post_raising_on_success_still_exits_0(make_request):
    def post(url, body):
        raise RuntimeError("callback bug")

    assert run_maintenance(make_request(), lambda _s: _Result([]), post=post) == 0


def test_failed_run_and_failed_callback_exits_1(make_request):
    def boom(_sql):
        raise RuntimeError("catalog down")

    def post(url, body):
        raise RuntimeError("callback bug")

    assert run_maintenance(make_request(), boom, post=post) == 1


def test_error_is_truncated(make_request):
    posted = []

    def boom(_sql):
        raise RuntimeError("x" * 10000)

    run_maintenance(make_request(), boom, post=lambda u, b: posted.append(b) or True)
    assert len(posted[0]["error"]) == 4096
