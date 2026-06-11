from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import chesscom, games

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chess Coach", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router)
app.include_router(chesscom.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": settings.anthropic_model,
        "stockfish": settings.resolve_stockfish() is not None,
    }
