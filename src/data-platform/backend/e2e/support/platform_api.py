"""Provide PlatformApi, the scenarios' client for the table maintenance API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

_DEFAULT_ONLY = ("id", "name", "is_default", "version", "created_at", "updated_at")


class PlatformApi:
    """Call the table maintenance API, failing with the call and the answer when it is refused."""

    def __init__(self, http: httpx.Client) -> None:
        """Call the API ``http`` points at (its ``base_url``)."""
        self._http = http

    def call(self, method: str, path: str, json: Any = None, **params: Any) -> Any:  # noqa: ANN401
        """Make one call and return its JSON (None for an empty answer)."""
        reply = self._http.request(method, path, json=json, params=params or None)
        assert reply.is_success, f"{method} {path} answered {reply.status_code}: {reply.text}"
        return reply.json() if reply.content else None

    def get(self, path: str, **params: Any) -> Any:  # noqa: ANN401
        """Read one resource."""
        return self.call("GET", path, **params)

    def create_maintenance_policy(self, name: str, description: str, change: Callable[[dict], dict]) -> dict:
        """Create a maintenance policy from the platform default, changed by ``change``."""
        body = {
            key: value
            for key, value in self.get("/v1/maintenance-policies/default").items()
            if key not in _DEFAULT_ONLY
        }
        return self.call(
            "POST", "/v1/maintenance-policies", change({**body, "description": description}) | {"name": name}
        )

    def attach(self, kind: str, name: str, target: dict) -> str:
        """Attach policy ``name`` of ``kind`` (``maintenance-policies`` or ``discovery-policies``) and return the id."""
        return self.call("PUT", f"/v1/{kind}/{name}/attachments", {"target": target})["id"]

    def table(self, catalog: str, namespace: str, table: str) -> dict | None:
        """Return the table the platform keeps at this place in the catalog, or None."""
        for found in self.get("/v1/tables"):
            if (found["catalog"], found["namespace"], found["table"]) == (catalog, namespace, table):
                return found
        return None

    def runs(self, table_uuid: str) -> list[dict]:
        """Return the table's maintenance runs, newest first."""
        return self.get(f"/v1/tables/{table_uuid}/table-maintenance-runs", limit=500)

    def platform_setting(self, key: str) -> Any:  # noqa: ANN401
        """Return the value of one platform setting."""
        groups = self.get("/v1/platform-settings")["groups"]
        [value] = [item["value"] for group in groups for item in group["items"] if item["key"] == key]
        return value
