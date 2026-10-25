import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (registers tables)
from app.db import Base, engine
from app.routes import contacts, deals, reports

STATIC = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Sales Pipeline CRM", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.getenv("CORS_ORIGINS", "").split(",") if o],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(contacts.router, prefix="/api")
app.include_router(deals.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC / "index.html")
