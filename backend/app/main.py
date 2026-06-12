import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .logging_config import configure_logging
from .routers import accounts, approvals, reports, transactions

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialise logging and ensure the schema exists before serving requests."""
    configure_logging()
    logger.info(
        "Starting Bookkeeping AI Control Tower (ai_engine=%s, model=%s)",
        "claude" if settings.anthropic_api_key else "rule-based",
        settings.ai_model,
    )
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Bookkeeping AI Control Tower",
    description="Core MVP: intake → AI classification + HITL approval → ledger → reports.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "ai_engine": "claude" if settings.anthropic_api_key else "rule-based",
        "model": settings.ai_model,
        "confidence_threshold": settings.confidence_threshold,
    }


app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(approvals.router)
app.include_router(reports.router)
