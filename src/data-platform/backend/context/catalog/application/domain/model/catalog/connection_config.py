"""Define the ConnectionConfig value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.catalog.authentication_parameters import (
    AuthenticationParameters,
)
from context.catalog.application.domain.model.catalog.connection_type import ConnectionType


class ConnectionConfig(ValueObject):
    """The remote catalog service an external catalog mirrors, and how to reach it.

    ``authentication`` is None only for a catalog read back without authentication parameters.
    ``to_primitives`` describes the connection without its secrets.
    """

    connection_type: ConnectionType
    uri: str | None = None
    authentication: AuthenticationParameters | None = None
