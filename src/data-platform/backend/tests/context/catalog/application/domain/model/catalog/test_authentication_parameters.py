"""Test that the AuthenticationParameters value object never shows its secrets."""

from __future__ import annotations

from context.catalog.application.domain.model.catalog import AuthenticationParameters, AuthenticationType


def test_repr_leaves_out_the_client_secret_and_the_bearer_token():
    """A log line or traceback that prints the value object must not carry a credential."""
    oauth = AuthenticationParameters(
        authentication_type=AuthenticationType.OAUTH, client_id="remote-client", client_secret="oauth-s3cr3t"
    )
    bearer = AuthenticationParameters(authentication_type=AuthenticationType.BEARER, bearer_token="bearer-t0ken")

    assert "oauth-s3cr3t" not in repr(oauth)
    assert "remote-client" in repr(oauth)
    assert "bearer-t0ken" not in repr(bearer)
