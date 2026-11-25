"""Define the HttpSettings configuration model."""

from __future__ import annotations

from bootstrap.configs.settings_block import SettingsBlock


class HttpSettings(SettingsBlock):
    """HTTP settings of the API.

    ``root_path`` is the public prefix a proxy strips before forwarding, for example
    ``/api`` behind the platform gateway. It only moves the docs and the OpenAPI
    ``servers`` entry; empty means the API is served at the root.
    """

    root_path: str = ""
