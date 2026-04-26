"""Entry point: selects api, scheduler, or outbox-publisher role via ROLE env var."""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Dispatch to api, scheduler, or outbox-publisher based on ROLE env var."""
    role = os.environ.get("ROLE", "api")

    if role == "api":
        import uvicorn

        uvicorn.run("bootstrap.api:app", host="0.0.0.0", port=8000)
    elif role == "scheduler":
        from scheduler.main import main as scheduler_main

        scheduler_main()
    elif role == "outbox-publisher":
        from outbox_publisher.main import main as publisher_main

        publisher_main()
    else:
        print(
            f"Unknown ROLE: {role!r}. Use 'api', 'scheduler', or 'outbox-publisher'.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
