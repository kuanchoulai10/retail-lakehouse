"""Entry point: selects api, scheduler, or messaging component via GLAC_COMPONENT."""

from __future__ import annotations

from bootstrap.configs.component import Component
from bootstrap.dependencies.settings import get_settings


def main() -> None:
    """Dispatch to the component specified by GLAC_COMPONENT."""
    settings = get_settings()

    match settings.component:
        case Component.API:
            import uvicorn

            uvicorn.run("bootstrap.api:app", host="0.0.0.0", port=8000)
        case Component.SCHEDULER:
            from bootstrap.scheduler import main as scheduler_main

            scheduler_main()
        case Component.MESSAGING:
            from bootstrap.messaging import main as messaging_main

            messaging_main()


if __name__ == "__main__":
    main()
