"""Define the WorkerSettings configuration model."""

from __future__ import annotations

from bootstrap.configs.service_settings import ServiceSettings


class WorkerSettings(ServiceSettings):
    """The settings of ``glac worker``.

    ``callback_base_url`` is the API's address the Spark jobs post their results to.
    """

    callback_base_url: str = "http://table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000"
