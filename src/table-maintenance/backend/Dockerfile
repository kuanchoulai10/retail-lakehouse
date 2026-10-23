FROM ghcr.io/astral-sh/uv:0.10.2 AS uv

FROM python:3.14.3-slim-bookworm AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system --no-cache --require-hashes -r requirements.txt

FROM python:3.14.3-slim-bookworm

COPY --from=builder /usr/local /usr/local
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && install -d -o 10001 -g 10001 /app
WORKDIR /app
COPY --chown=10001:10001 . .

USER 10001
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "entrypoint.py"]
