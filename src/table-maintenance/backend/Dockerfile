FROM python:3.14-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .
RUN uv pip install --system --no-cache \
    "fastapi[standard]>=0.115" \
    "kubernetes>=32.0"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
