FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .
RUN uv pip install --system --no-cache \
    "fastapi[standard]>=0.115" \
    "kubernetes>=32.0" \
    "sqlalchemy>=2.0" \
    "psycopg[binary]>=3.2" \
    "pyiceberg>=0.9"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
