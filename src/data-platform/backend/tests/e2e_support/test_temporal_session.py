"""Test TemporalSession, which lets the synchronous scenarios use the asynchronous Temporal client."""

from __future__ import annotations

from e2e.support import TemporalSession


def test_runs_a_coroutine_with_the_client_and_returns_its_result():
    """A scenario hands a coroutine function and gets its result back."""

    async def connect() -> str:
        return "client"

    async def describe(client: str) -> str:
        return f"{client} described"

    session = TemporalSession.connect(connect)
    try:
        assert session.run(describe) == "client described"
        assert session.run(describe) == "client described"
    finally:
        session.close()
