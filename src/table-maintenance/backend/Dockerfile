# Build context: src/table-maintenance/
# docker build -t table-maintenance-backend -f backend/Dockerfile src/table-maintenance/
FROM python:3.14-slim

RUN pip install --no-cache-dir uv

# Install shared jobs package (provides configs/ models)
COPY jobs/ /jobs
RUN uv pip install --system --no-cache /jobs

# Install backend dependencies
WORKDIR /app
COPY backend/ .
RUN uv pip install --system --no-cache \
    "fastapi[standard]>=0.115" \
    "kubernetes>=32.0"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
