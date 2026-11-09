"""OpenAPI export entry point: writes the API's document for the console's generated client."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from bootstrap.container import build_openapi_document


def main(argv: list[str] | None = None) -> None:
    """Write the OpenAPI document to the path given as the only argument."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        msg = "usage: python -m bootstrap.export_openapi <path>"
        raise SystemExit(msg)
    document = build_openapi_document()
    Path(args[0]).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
