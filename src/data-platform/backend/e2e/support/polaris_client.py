"""Provide PolarisClient, which calls Polaris's catalog and management APIs with one principal's token."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class PolarisClient:
    """Call Polaris as one principal, getting its client-credentials token on first use."""

    def __init__(
        self,
        http: httpx.Client,
        *,
        catalog_uri: str,
        management_uri: str,
        credential: str,
        scope: str,
    ) -> None:
        """Call Polaris at the two API roots, as the principal ``credential`` names (``id:secret``)."""
        self._http = http
        self._catalog_uri = catalog_uri.rstrip("/")
        self._management_uri = management_uri.rstrip("/")
        self._client_id, _, self._client_secret = credential.partition(":")
        self._scope = scope
        self._token: str | None = None

    def catalog(self, method: str, path: str, json: Any = None) -> httpx.Response:  # noqa: ANN401
        """Call the catalog API (the Iceberg REST API and Polaris's own catalog routes)."""
        return self._call(self._catalog_uri, method, path, json)

    def management(self, method: str, path: str, json: Any = None) -> httpx.Response:  # noqa: ANN401
        """Call the management API (catalogs, principals, roles and grants)."""
        return self._call(self._management_uri, method, path, json)

    def _call(self, base: str, method: str, path: str, json: Any) -> httpx.Response:  # noqa: ANN401
        headers = {"Authorization": f"Bearer {self._bearer()}"}
        return self._http.request(method, base + path, json=json, headers=headers, timeout=30)

    def _bearer(self) -> str:
        if self._token is None:
            reply = self._http.post(
                self._catalog_uri + "/v1/oauth/tokens",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._scope,
                },
                timeout=30,
            )
            reply.raise_for_status()
            self._token = reply.json()["access_token"]
        return self._token
