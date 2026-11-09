"""Test that the OpenAPI export entry point writes a stable document."""

from __future__ import annotations

import json

from bootstrap.export_openapi import main


def test_writes_the_document_with_sorted_keys_and_a_trailing_newline(tmp_path):
    """The file is the API's document, written the same way every run so a diff shows only API changes."""
    target = tmp_path / "openapi.json"

    main([str(target)])
    first = target.read_text()
    main([str(target)])

    assert target.read_text() == first
    assert first.endswith("}\n")
    document = json.loads(first)
    assert "/v1/catalogs" in document["paths"]
    assert list(document) == sorted(document)
