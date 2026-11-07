"""Define the PolarisHttpClient."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import httpx

from context.catalog.adapter.outbound.shared.polaris.polaris_error_mapper import (
    raise_for_polaris,
)
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

_TOKEN_PATH = "/v1/oauth/tokens"
_UNAUTHORIZED = 401
_ANY_ERROR = (CatalogUnavailableError, ConflictError, NotFoundError, PermissionDeniedError, ValidationError)


class PolarisHttpClient:
    """Send authenticated requests to one Polaris server and map its errors.

    Two bases, one per Polaris API:

    - ``base_uri`` is the catalog API base and ends in ``/api/catalog``. ``catalog_request``
      appends its path to it, so an Iceberg REST path starts with ``/v1/{prefix}/...`` and a
      Polaris generic-table path starts with ``/polaris/v1/{prefix}/...`` (the prefix is the
      catalog name). The OAuth token endpoint, ``/v1/oauth/tokens``, sits under the same base.
    - ``management_uri`` ends in ``/api/management/v1``. ``management_request`` paths start
      with ``/catalogs``.

    A path is appended verbatim, so the caller percent-encodes each segment; a namespace is
    its parts joined by the unit separator U+001F, sent as ``%1F``.

    The client-credentials token is fetched on the first request and reused. When Polaris
    answers 401, the token is dropped, a new one is fetched and the request is retried once;
    a 401 after that means Polaris rejects the backend credential (CatalogUnavailableError).
    Failing to get a token raises ``CatalogUnavailableError``: it is the backend's own
    credential that failed, not the caller's privileges, and no token is kept, so the next
    request tries again. A transport failure raises ``CatalogUnavailableError`` too, and every
    response passes through ``raise_for_polaris``.
    """

    def __init__(
        self,
        base_uri: str,
        management_uri: str,
        credential: str,
        scope: str,
        client: httpx.Client,
    ) -> None:
        """Bind the two API bases, the ``client_id:secret`` credential, the token scope and the HTTP client."""
        self._base_uri = base_uri.rstrip("/")
        self._management_uri = management_uri.rstrip("/")
        self._client_id, _, self._client_secret = credential.partition(":")
        self._scope = scope
        self._client = client
        self._lock = threading.Lock()
        self._access_token: str | None = None

    def catalog_request(
        self,
        method: str,
        path: str,
        *,
        json: object = None,
        params: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Send a request to the catalog API (Iceberg REST and Polaris generic tables)."""
        return self._send(method, f"{self._base_uri}{path}", json=json, params=params)

    def management_request(
        self,
        method: str,
        path: str,
        *,
        json: object = None,
        params: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Send a request to the Polaris management API."""
        return self._send(method, f"{self._management_uri}{path}", json=json, params=params)

    def _send(self, method: str, url: str, *, json: object, params: Mapping[str, str] | None) -> httpx.Response:
        token = self._token()
        response = self._request(method, url, token, json=json, params=params)
        if response.status_code == _UNAUTHORIZED:
            self._drop(token)
            response = self._request(method, url, self._token(), json=json, params=params)
        raise_for_polaris(response)
        return response

    def _request(
        self, method: str, url: str, token: str, *, json: object, params: Mapping[str, str] | None
    ) -> httpx.Response:
        try:
            return self._client.request(
                method, url, json=json, params=params, headers={"Authorization": f"Bearer {token}"}
            )
        except httpx.TransportError as exc:
            raise CatalogUnavailableError(f"Polaris is unreachable: {exc}") from exc

    def _token(self) -> str:
        with self._lock:
            if self._access_token is None:
                self._access_token = self._fetch_token()
            return self._access_token

    def _drop(self, token: str) -> None:
        with self._lock:
            if self._access_token == token:
                self._access_token = None

    def _fetch_token(self) -> str:
        try:
            response = self._client.post(
                f"{self._base_uri}{_TOKEN_PATH}",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._scope,
                },
            )
            raise_for_polaris(response)
        except httpx.TransportError as exc:
            raise CatalogUnavailableError(f"could not get a Polaris token, Polaris is unreachable: {exc}") from exc
        except _ANY_ERROR as exc:
            raise CatalogUnavailableError(f"could not get a Polaris token: {exc}") from exc
        try:
            body = response.json()
        except ValueError:
            body = None
        token = body.get("access_token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            raise CatalogUnavailableError("could not get a Polaris token: the response has no access token")
        return token
