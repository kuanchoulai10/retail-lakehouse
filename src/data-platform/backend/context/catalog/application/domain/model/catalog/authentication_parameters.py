"""Define the AuthenticationParameters value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.catalog.application.domain.model.catalog.authentication_type import (
        AuthenticationType,
    )


@dataclass(frozen=True)
class AuthenticationParameters(ValueObject):
    """How an external catalog's connection authenticates; each field belongs to one type.

    - OAUTH: ``token_uri``, ``client_id``, ``client_secret``, ``scopes``.
    - BEARER: ``bearer_token``.
    - SIGV4: ``role_arn``, ``role_session_name``, ``external_id``, ``signing_region``, ``signing_name``.
    - IMPLICIT: none; the credentials come from the catalog service's environment.

    ``client_secret`` and ``bearer_token`` are secrets: they are sent when a catalog is
    created, the catalog service never returns them, no output carries them, and ``repr``
    leaves them out.
    """

    authentication_type: AuthenticationType
    token_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = field(default=None, repr=False)
    scopes: tuple[str, ...] = ()
    bearer_token: str | None = field(default=None, repr=False)
    role_arn: str | None = None
    role_session_name: str | None = None
    external_id: str | None = None
    signing_region: str | None = None
    signing_name: str | None = None
