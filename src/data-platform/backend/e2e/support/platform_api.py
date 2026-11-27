"""Provide PlatformApi, the scenarios' client for the table maintenance API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

_DEFAULT_ONLY = ("id", "name", "is_default", "version", "created_at", "updated_at")
_KINDS = ("maintenance", "discovery")
_NOT_ATTACHED = 404


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

    def attach(self, kind: str, name: str, target: dict) -> None:
        """Attach policy ``name`` of ``kind`` (``maintenance`` or ``discovery``) to the place ``target`` names."""
        self.call("PUT", _attachments(kind, name), {"target": {"type": target["type"], "path": target["path"]}})

    def detach(self, kind: str, name: str, target: dict, *, missing_ok: bool = False) -> None:
        """Detach policy ``name`` of ``kind`` from the place ``target`` names (its ``type`` and ``path``).

        The API answers 404 when the policy is not attached there; ``missing_ok`` makes that fine, for a
        cleanup undo that runs whether or not the scenario already detached it. Any other refusal fails.
        """
        path = _attachments(kind, name)
        reply = self._http.request("DELETE", path, params={"target_type": target["type"], "path": target["path"]})
        if missing_ok and reply.status_code == _NOT_ATTACHED:
            return
        called = reply.request.url.raw_path.decode()
        assert reply.is_success, f"DELETE {called} answered {reply.status_code}: {reply.text}"

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


def _attachments(kind: str, name: str) -> str:
    if kind not in _KINDS:
        raise ValueError(f"a policy kind is maintenance or discovery, not {kind!r}")
    return f"/v1/{kind}-policies/{name}/attachments"
