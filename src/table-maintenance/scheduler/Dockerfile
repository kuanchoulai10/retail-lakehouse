FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY scheduler/pyproject.toml .
RUN uv pip install --system --no-cache .

FROM python:3.14-slim

COPY --from=builder /usr/local /usr/local
WORKDIR /app

COPY backend/ ./backend/
COPY scheduler/scheduler_loop.py scheduler/main.py ./scheduler/

ENV PYTHONPATH="/app/backend:/app/scheduler"
CMD ["python", "/app/scheduler/main.py"]
