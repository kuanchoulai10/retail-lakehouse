FROM apache/spark:4.0.0

USER root
WORKDIR /opt/spark/work-dir

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN uv pip install --system --no-cache "pydantic>=2.12.5" "pydantic-settings>=2.0"

COPY configs/ ./configs/
COPY sql_builder.py .
COPY main.py .

USER spark
