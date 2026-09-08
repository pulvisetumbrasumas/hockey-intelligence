from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import get_settings
from app.data.seeder import ensure_data_source
from app.database.connection import async_session_factory, init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session_factory() as session:
        await ensure_data_source(session)
        await session.commit()
    yield


settings = get_settings()

app = FastAPI(
    title="Hockey Intelligence",
    description=(
        "Open-source NHL hockey intelligence platform. The database is the "
        "source of truth, the statistics engine is deterministic, and the "
        "Ollama integration is the reasoning layer."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "model_configured": settings.ollama_model}


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
