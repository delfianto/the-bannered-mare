"""Candlekeep Core - FastAPI Application Entry Point"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.admin.router import router as admin_router
from src.character import router as characters_router
from src.chat_message import router as chat_messages_router
from src.chat_session import router as chats_router
from src.core.config import settings
from src.core.logging import RequestLoggingMiddleware, configure_structlog, get_logger, mongo_logger
from src.core.utils.storage import ensure_storage_directories
from src.health import router as health_router
from src.lore import router as lore_router
from src.model import router as models_router
from src.model_family import router as model_families_router
from src.persona import router as personas_router
from src.preset import router as presets_router
from src.prompt_fragment import fragment_router as prompt_fragments_router
from src.prompt_fragment import template_fragment_router as template_fragments_router
from src.prompt_template import router as prompt_templates_router
from src.provider import router as providers_router
from src.rag import data_bank_router, rag_router

configure_structlog()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan event handler"""
    ensure_storage_directories()
    logger.info(
        "application_startup",
        storage_path=settings.storage_path,
        database_url=settings.database_url.split("@")[-1],  # Hide credentials
    )

    from src.fixtures.service import seed_database

    seed_database()

    await mongo_logger.initialize()

    yield

    logger.info("application_shutdown")
    await mongo_logger.close()


app = FastAPI(
    title="Candlekeep Core",
    description="FastAPI backend for RP platform with character cards and chat management",
    version="0.2.5",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)


app.include_router(admin_router)
app.include_router(providers_router)
app.include_router(model_families_router)
app.include_router(models_router)
app.include_router(characters_router)
app.include_router(chats_router)
app.include_router(chat_messages_router)
app.include_router(personas_router)
app.include_router(presets_router)
app.include_router(prompt_templates_router)
app.include_router(prompt_fragments_router)
app.include_router(template_fragments_router)
app.include_router(lore_router)
app.include_router(data_bank_router)
app.include_router(rag_router)
app.include_router(health_router)


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Candlekeep Core API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "demo": "/demo",
    }


@app.get("/demo", response_class=HTMLResponse)
def demo():
    """Minimal chat UI for developer testing"""
    html_path = Path(__file__).parent / "demo" / "index.html"
    return HTMLResponse(content=html_path.read_text())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # Enable auto-reload for development
    )
