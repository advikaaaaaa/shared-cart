from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.database.db import init_db
from backend.app.paths import ensure_dirs

app = FastAPI(
    title="SharedCart API",
    description="SharedCart — Smarter Food Delivery Through Intelligent Order Pooling",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    ensure_dirs()
    init_db()


@app.get("/")
def root():
    return {
        "product": "SharedCart",
        "tagline": "SharedCart — Smarter Food Delivery Through Intelligent Order Pooling",
        "docs": "/docs",
        "health": "/api/health",
    }
