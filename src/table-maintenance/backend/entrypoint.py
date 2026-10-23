"""Entry point: selects the component to run via GLAC_COMPONENT."""

from __future__ import annotations

from bootstrap.configs.component import Component
from bootstrap.dependencies.settings import get_settings


def main() -> None:
    """Dispatch to the component specified by GLAC_COMPONENT."""
    settings = get_settings()

    match settings.component:
        case Component.API:
            from bootstrap.api import main as api_main

            api_main()
        case Component.WORKER:
            from bootstrap.worker import main as worker_main

            worker_main()
        case Component.EVENT_CONSUMER:
            from bootstrap.event_consumer import main as event_consumer_main

            event_consumer_main()
        case Component.MIGRATE:
            from bootstrap.migrate import main as migrate_main

            migrate_main()


if __name__ == "__main__":
    main()
