from fastapi import FastAPI

from .routers import notes

app = FastAPI(title="XIXI API")

app.include_router(notes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
