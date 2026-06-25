from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import briefs, health, items, me, moodboards

app = FastAPI(
    title="agent-moodboard API",
    version="0.1.0",
    docs_url="/docs" if settings.local_dev else None,
    redoc_url="/redoc" if settings.local_dev else None,
)

_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(items.router)
app.include_router(briefs.router)
app.include_router(moodboards.router)
