"""Define the iceberg_namespace_path function."""

from __future__ import annotations

from urllib.parse import quote

_SEPARATOR = "\x1f"


def iceberg_namespace_path(catalog: str, parts: tuple[str, ...] = ()) -> str:
    """Return the Iceberg REST path of ``parts`` in ``catalog``, relative to the catalog API base.

    Without parts it is the namespaces collection, ``/v1/{catalog}/namespaces``. With parts the
    last segment is the parts joined by U+001F and percent-encoded (``a%1Fb``), so a part with a
    dot or a space stays one part.
    """
    base = f"/v1/{quote(catalog, safe='')}/namespaces"
    if not parts:
        return base
    return f"{base}/{quote(_SEPARATOR.join(parts), safe='')}"
