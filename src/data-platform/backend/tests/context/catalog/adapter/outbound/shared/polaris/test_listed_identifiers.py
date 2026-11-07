"""Test the listed_identifiers guard that every identifier listing passes through."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.shared.polaris import listed_identifiers
from context.catalog.application.exceptions import CatalogUnavailableError

WHAT = "the views of namespace ['retail']"


def test_returns_namespace_parts_and_name_of_each_identifier():
    """Each identifier becomes ``(parts, name)``; an absent ``identifiers`` key is an empty listing."""
    response = httpx.Response(200, json={"identifiers": [{"namespace": ["a.b", "c"], "name": "v"}]})

    assert listed_identifiers(response, WHAT) == [(("a.b", "c"), "v")]
    assert listed_identifiers(httpx.Response(200, json={}), WHAT) == []


@pytest.mark.parametrize(
    "reply",
    [
        httpx.Response(200, json=["identifiers"]),
        httpx.Response(200, text="<html>nope</html>"),
        httpx.Response(200, json={"identifiers": [{"namespace": "retail", "name": "v"}]}),
        httpx.Response(200, json={"identifiers": [{"namespace": ["retail"], "name": 7}]}),
        httpx.Response(200, json={"identifiers": [{"name": "v"}]}),
        httpx.Response(200, json={"identifiers": ["v"]}),
        httpx.Response(200, json={"identifiers": 3}),
    ],
)
def test_unreadable_listing_names_what_was_listed(reply: httpx.Response):
    """A non-dict body, a non-list namespace or any other unreadable shape is CatalogUnavailableError."""
    with pytest.raises(CatalogUnavailableError, match=r"the views of namespace \['retail'\] in a form this backend"):
        listed_identifiers(reply, WHAT)


def test_a_next_page_token_is_refused():
    """A listing with more pages raises instead of returning a cut list (Ruling R8)."""
    body: dict[str, Any] = {"identifiers": [{"namespace": ["retail"], "name": "v"}], "next-page-token": "p2"}

    with pytest.raises(CatalogUnavailableError, match="paged"):
        listed_identifiers(httpx.Response(200, json=body), WHAT)


def test_a_null_next_page_token_is_not_paging():
    """Polaris sends ``null`` on the last page; that is a complete listing."""
    body: dict[str, Any] = {"identifiers": [], "next-page-token": None}

    assert listed_identifiers(httpx.Response(200, json=body), WHAT) == []
