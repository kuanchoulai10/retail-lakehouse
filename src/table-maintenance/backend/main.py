from fastapi import FastAPI

app = FastAPI(title="Table Maintenance Backend")


@app.get("/health")
def health():
    return {"status": "ok"}
