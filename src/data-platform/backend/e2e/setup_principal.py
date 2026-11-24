"""Give the e2e its own Polaris principal and hand its fresh credentials to the scenarios.

Run as ``python -m e2e.setup_principal`` in the e2e pod's init container, which alone holds the
platform's credential. It ensures principal ``tm-e2e``, principal role ``tm_e2e``, catalog role
``tm_e2e`` on the platform's catalog with ``CATALOG_MANAGE_CONTENT``, and the ``service_admin``
principal role (to read back the catalogs a scenario creates through the API), then rotates the
principal's credentials and writes ``<client_id>:<client_secret>`` to the file the scenarios read.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from e2e.support import PolarisClient

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

_EXISTS = 409


def ensure_principal(polaris: PolarisClient, *, catalog: str, principal: str = "tm-e2e") -> str:
    """Create or keep the e2e principal and its grants, rotate its credentials and return them."""
    role = principal.replace("-", "_")
    _create(polaris, "/principals", {"principal": {"name": principal}, "credentialRotationRequired": False})
    _create(polaris, "/principal-roles", {"principalRole": {"name": role}})
    _create(polaris, f"/catalogs/{catalog}/catalog-roles", {"catalogRole": {"name": role}})
    _put(
        polaris,
        f"/catalogs/{catalog}/catalog-roles/{role}/grants",
        {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}},
    )
    _put(polaris, f"/principal-roles/{role}/catalog-roles/{catalog}", {"catalogRole": {"name": role}})
    _put(polaris, f"/principals/{principal}/principal-roles", {"principalRole": {"name": role}})
    _put(polaris, f"/principals/{principal}/principal-roles", {"principalRole": {"name": "service_admin"}})
    credentials = _checked(polaris.management("POST", f"/principals/{principal}/rotate"), "POST", "rotate")
    secrets = credentials.json()["credentials"]
    return f"{secrets['clientId']}:{secrets['clientSecret']}"


def _create(polaris: PolarisClient, path: str, body: object) -> None:
    reply = polaris.management("POST", path, json=body)
    if reply.status_code != _EXISTS:
        _checked(reply, "POST", path)


def _put(polaris: PolarisClient, path: str, body: object) -> None:
    _checked(polaris.management("PUT", path, json=body), "PUT", path)


def _checked(reply: httpx.Response, method: str, path: str) -> httpx.Response:
    if not reply.is_success:
        try:
            message = reply.json()["error"]["message"]
        except ValueError, KeyError, TypeError:
            message = reply.text
        raise RuntimeError(f"{method} {path} answered {reply.status_code}: {message}")
    return reply


def main(environ: Mapping[str, str] = os.environ, http_factory: Callable[[], httpx.Client] = httpx.Client) -> None:
    """Ensure the principal with the platform's credential and write its credentials, readable by the owner only."""
    target = Path(environ["E2E_POLARIS_CREDENTIAL_FILE"])
    with http_factory() as http:
        polaris = PolarisClient(
            http,
            catalog_uri=environ["GLAC_CATALOG__URI"],
            management_uri=environ["GLAC_CATALOG__MANAGEMENT_URI"],
            credential=environ["GLAC_CATALOG__CREDENTIAL"],
            scope=environ["GLAC_CATALOG__SCOPE"],
        )
        credential = ensure_principal(polaris, catalog=environ["E2E_CATALOG"])
    target.touch(mode=0o600, exist_ok=True)
    target.chmod(0o600)
    target.write_text(credential)
    print(f"principal tm-e2e ready, credentials written to {target}")  # noqa: T201


if __name__ == "__main__":
    main()
