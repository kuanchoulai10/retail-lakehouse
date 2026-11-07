"""Define the PolarisStub, an in-process Polaris served through httpx.MockTransport."""

from __future__ import annotations

from collections import defaultdict
from urllib.parse import parse_qs

import httpx

from context.catalog.adapter.outbound.shared.polaris import PolarisHttpClient

BASE_URI = "http://polaris:8181/api/catalog"
MANAGEMENT_URI = "http://polaris:8181/api/management/v1"
TOKEN_PATH = "/api/catalog/v1/oauth/tokens"
CREDENTIAL = "root:s3cr3t"
SCOPE = "PRINCIPAL_ROLE:ALL"

type Reply = httpx.Response | Exception


class PolarisStub:
    """Answer token and API requests from queued replies and record every request.

    Each fetched token is ``tok-1``, ``tok-2`` and so on, unless a token reply is
    queued. Replies queued for a route are used in order and the last one repeats.
    A request to a route with nothing queued is answered with 404.
    """

    def __init__(self) -> None:
        """Start with no replies and no recorded requests."""
        self.requests: list[httpx.Request] = []
        self.token_requests: list[httpx.Request] = []
        self._token_replies: list[Reply] = []
        self._replies: dict[tuple[str, str], list[Reply]] = defaultdict(list)
        self._tokens_issued = 0

    def on(self, method: str, path: str, *replies: Reply) -> None:
        """Queue the replies for ``method`` on the raw (still percent-encoded) ``path``."""
        self._replies[(method, path)].extend(replies)

    def fail_token(self, *replies: Reply) -> None:
        """Queue replies for the next token requests; once used up, tokens are issued again."""
        self._token_replies.extend(replies)

    def client(self) -> PolarisHttpClient:
        """Return a Polaris client whose HTTP traffic this stub answers."""
        http = httpx.Client(transport=httpx.MockTransport(self._handle))
        return PolarisHttpClient(BASE_URI, MANAGEMENT_URI, CREDENTIAL, SCOPE, http)

    @staticmethod
    def form(request: httpx.Request) -> dict[str, str]:
        """Return the url-encoded form body of a request as a flat dict."""
        return {key: values[0] for key, values in parse_qs(request.content.decode()).items()}

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode().split("?", 1)[0]
        if request.method == "POST" and path == TOKEN_PATH:
            self.token_requests.append(request)
            return self._token(request)
        self.requests.append(request)
        replies = self._replies.get((request.method, path))
        if not replies:
            return httpx.Response(404, json={"error": {"message": f"no stub for {request.method} {path}"}})
        return self._reply(replies[0] if len(replies) == 1 else replies.pop(0), request)

    def _token(self, request: httpx.Request) -> httpx.Response:
        if self._token_replies:
            return self._reply(self._token_replies.pop(0), request)
        self._tokens_issued += 1
        return httpx.Response(
            200,
            json={"access_token": f"tok-{self._tokens_issued}", "token_type": "bearer", "expires_in": 3600},
        )

    @staticmethod
    def _reply(reply: Reply, request: httpx.Request) -> httpx.Response:
        if isinstance(reply, Exception):
            raise reply
        return httpx.Response(reply.status_code, headers=reply.headers, content=reply.content, request=request)
