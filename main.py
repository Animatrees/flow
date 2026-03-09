from fastapi import FastAPI

app = FastAPI(title="Flow")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "flow"}
