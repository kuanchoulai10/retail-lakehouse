from __future__ import annotations

from error_text import MAX_ERROR_LENGTH, error_text

OOM_LINE = "java.lang.OutOfMemoryError: Java heap space"


def test_short_error_is_unchanged():
    assert error_text(RuntimeError("catalog down")) == "RuntimeError: catalog down"


def test_long_error_is_cut_to_the_cap():
    text = error_text(RuntimeError("x" * 10000))
    assert len(text) == MAX_ERROR_LENGTH
    assert text.startswith("RuntimeError: xxx")


def test_error_keeps_the_out_of_memory_line_beyond_the_cap():
    message = "\n".join(["Py4JJavaError: An error occurred", *(["\tat org.apache.Frame(x)"] * 400), OOM_LINE, "tail"])
    text = error_text(RuntimeError(message))
    assert len(text) <= MAX_ERROR_LENGTH
    assert text.startswith("RuntimeError: Py4JJavaError")
    assert OOM_LINE in text


def test_error_keeps_the_executor_exit_code_52_line():
    line = "ExecutorLostFailure (executor 1 exited caused by one of the running tasks) Reason: exit code 52"
    text = error_text(RuntimeError("\n".join([*(["y" * 100] * 100), line])))
    assert len(text) <= MAX_ERROR_LENGTH
    assert "exit code 52" in text


def test_a_very_long_out_of_memory_line_keeps_its_marker():
    message = "z" * 5000 + "\n" + "w" * 3000 + OOM_LINE + "w" * 3000
    text = error_text(RuntimeError(message))
    assert len(text) <= MAX_ERROR_LENGTH
    assert "OutOfMemoryError" in text


def test_an_out_of_memory_line_within_the_cap_is_kept_where_it_is():
    message = OOM_LINE + "\n" + "x" * 10000
    text = error_text(RuntimeError(message))
    assert text == f"RuntimeError: {message}"[:MAX_ERROR_LENGTH]
