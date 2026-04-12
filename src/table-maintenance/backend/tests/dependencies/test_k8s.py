from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.k8s import get_k8s_api


def test_get_k8s_api_returns_api_from_app_state():
    mock_api = MagicMock()
    mock_request = MagicMock()
    mock_request.app.state.k8s_api = mock_api

    result = get_k8s_api(mock_request)

    assert result is mock_api
