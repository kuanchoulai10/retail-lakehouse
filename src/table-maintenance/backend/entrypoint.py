"""Entry point: selects api or scheduler role via ROLE env var."""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Dispatch to api or scheduler based on ROLE env var."""
    role = os.environ.get("ROLE", "api")

    if role == "api":
        import uvicorn

        uvicorn.run("api.main:app", host="0.0.0.0", port=8000)
    elif role == "scheduler":
        from scheduler.main import main as scheduler_main

        scheduler_main()
    else:
        print(f"Unknown ROLE: {role!r}. Use 'api' or 'scheduler'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
