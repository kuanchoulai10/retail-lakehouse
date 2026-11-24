ARG BACKEND_IMAGE

FROM ghcr.io/astral-sh/uv:0.10.2 AS uv

FROM ${BACKEND_IMAGE}

USER root
COPY --from=uv /uv /tmp/uv
COPY requirements-e2e.txt /tmp/requirements-e2e.txt
RUN /tmp/uv pip install --system --no-cache --require-hashes -r /tmp/requirements-e2e.txt \
    && rm /tmp/uv /tmp/requirements-e2e.txt
COPY --chown=10001:10001 e2e/ e2e/

USER 10001
CMD ["python", "-m", "pytest", "e2e", "-p", "no:cacheprovider", "-m", "critical"]
