"""
SkillFlow — FastAPI application entry point.

Start the server from the backend/ directory:
# From the backend directory:
cd backend
..\.venv\Scripts\activate
uvicorn app.main:app --reload


The knowledge base is validated at startup so any data file issues are
reported immediately rather than on the first request.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.knowledge import router
from app.routes.conversation import router as conversation_router
from app.routes.recommendations import router as recommendations_router
from app.services.knowledge_base import get_knowledge_base

import sys

# Ensure UTF-8 output on Windows consoles to prevent UnicodeEncodeError with Devanagari / regional scripts
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — replaces the deprecated @app.on_event("startup") pattern.
# The knowledge base is loaded eagerly so any data file issues are
# surfaced at startup, not on the first request.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    # Startup
    try:
        kb = get_knowledge_base()
        logger.info(
            "SkillFlow backend started. "
            "Knowledge base loaded: %d roles, version %s",
            len(kb.roles),
            kb.version,
        )
    except (FileNotFoundError, ValueError) as exc:
        # Log the error but don't prevent startup — routes will return 500
        # until the data file is fixed, rather than crashing the process.
        logger.error("Failed to load knowledge base at startup: %s", exc)

    yield  # Application runs here

    # Shutdown (nothing to clean up in this service)
    logger.info("SkillFlow backend shutting down.")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SkillFlow API",
    description=(
        "AI-Driven Voice Assistant for Livelihood Mapping and NSQF-Aligned "
        "Skilling Recommendations for SC Communities under PM-AJAY (SIH26097).\n\n"
        "This backend exposes a curated, government-aligned knowledge base of "
        "NSQF vocational pathways and a deterministic skill-matching engine."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server during development.
# Do not use allow_origins=["*"] in production.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default dev port
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(router, prefix="/api")
app.include_router(conversation_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")
