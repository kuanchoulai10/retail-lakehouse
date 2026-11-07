from __future__ import annotations

import json

from result_callback import post_result


class _Response:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_posts_json_once_on_success():
    seen = []

    def opener(request, timeout):
        seen.append(request)
        return _Response(200)

    assert post_result("http://x/y", {"a": 1}, sleep=lambda _s: None, opener=opener)
    assert len(seen) == 1
    assert json.loads(seen[0].data) == {"a": 1}
    assert seen[0].get_method() == "POST"


def test_retries_three_times_five_seconds_apart():
    sleeps = []
    calls = []

    def opener(request, timeout):
        calls.append(1)
        raise ConnectionError("nope")

    assert not post_result("http://x/y", {}, sleep=sleeps.append, opener=opener)
    assert len(calls) == 3
    assert sleeps == [5, 5]


def test_recovers_after_failure():
    responses = iter([ConnectionError("x"), _Response(204)])

    def opener(request, timeout):
        r = next(responses)
        if isinstance(r, Exception):
            raise r
        return r

    assert post_result("http://x/y", {}, sleep=lambda _s: None, opener=opener)


def test_non_2xx_status_is_retried():
    calls = []

    def opener(request, timeout):
        calls.append(1)
        return _Response(500)

    assert not post_result("http://x/y", {}, sleep=lambda _s: None, opener=opener)
    assert len(calls) == 3


def test_http_exception_and_value_error_are_retried():
    import http.client

    errors = iter([http.client.BadStatusLine("x"), ValueError("bad url"), ConnectionError()])

    def opener(request, timeout):
        raise next(errors)

    assert not post_result("http://x/y", {}, sleep=lambda _s: None, opener=opener)
