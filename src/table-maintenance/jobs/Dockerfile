FROM apache/spark:3.5.3

USER root
WORKDIR /opt/spark/work-dir

COPY pyproject.toml .
RUN pip install --no-cache-dir "pydantic>=2.12.5" "pydantic-settings>=2.0"

COPY configs/ ./configs/
COPY main.py .

USER spark
