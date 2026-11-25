"""Define the ApiSettings configuration model."""

from __future__ import annotations

from pydantic import Field

from bootstrap.configs.http_settings import HttpSettings
from bootstrap.configs.service_settings import ServiceSettings


class ApiSettings(ServiceSettings):
    """The settings of ``glac api``."""

    http: HttpSettings = Field(default_factory=HttpSettings)
