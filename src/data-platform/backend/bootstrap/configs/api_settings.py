"""Define the ApiSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class ApiSettings(BaseModel):
    """HTTP API settings.

    ``root_path`` is the public prefix a proxy strips before forwarding, for example
    ``/api`` behind the platform gateway (``GLAC_API__ROOT_PATH``). It only moves the
    docs and the OpenAPI ``servers`` entry; empty means the API is served at the root.
    """

    root_path: str = ""
