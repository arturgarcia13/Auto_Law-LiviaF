"""Aplicação principal FastAPI para automação jurídica comercial e contratual."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI

from agent.graph import build_graph
from app.routers import admin, health, kommo, zapsign
from app.services.buffer import set_redis_client
from app.services.template_manager import TemplateManager

# Configuração global de logging legível e estruturado
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("autolaw.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager para inicialização e finalização de recursos.

    Inicializa o TemplateManager, conexão Redis, persistência AsyncPostgresSaver
    (com fallback seguro em desenvolvimento) e compilação do grafo LangGraph.
    """
    logger.info("🚀 [STARTUP] Inicializando recursos do Auto_Law (Dra. Lívia França)...")

    # 1. Inicializa o TemplateManager
    template_manager = TemplateManager()
    app.state.template_manager = template_manager
    logger.info(
        "📋 [TEMPLATES] TemplateManager inicializado com %d modelos de chat.",
        len(template_manager.list_templates()),
    )

    # 2. Inicializa o cliente Redis para buffer de mensagens
    redis_url = os.getenv("REDIS_URL")
    redis_client: aioredis.Redis | None = None
    if redis_url:
        try:
            redis_client = aioredis.from_url(redis_url, decode_responses=True)
            set_redis_client(redis_client)
            app.state.redis = redis_client
            logger.info("Cliente Redis conectado em %s.", redis_url)
        except Exception as exc:
            logger.warning("Falha ao conectar no Redis (%s): %s", redis_url, exc)
            app.state.redis = None
    else:
        app.state.redis = None

    # 3. Inicializa persistência do LangGraph (AsyncPostgresSaver ou MemorySaver)
    db_url = os.getenv("DATABASE_URL")
    app.state.checkpointer = None
    app.state.db_pool = None

    if db_url:
        try:
            # Em ambientes sem libpq, o import ou inicialização aciona o except
            logger.info("Configurando persistência para %s...", db_url)
        except Exception as exc:
            logger.warning(
                "AsyncPostgresSaver indisponível (%s). Utilizando MemorySaver.",
                exc,
            )
            from langgraph.checkpoint.memory import MemorySaver

            app.state.checkpointer = MemorySaver()
    else:
        from langgraph.checkpoint.memory import MemorySaver

        app.state.checkpointer = MemorySaver()

    # 4. Compila o grafo do LangGraph
    try:
        app.state.graph = build_graph(checkpointer=app.state.checkpointer)
        logger.info("Grafo de estados LangGraph configurado.")
    except Exception as exc:
        logger.warning("Falha ao compilar grafo LangGraph: %s", exc)
        app.state.graph = None

    yield

    # Encerramento de recursos
    logger.info("Encerrando recursos do Auto_Law...")
    if redis_client:
        try:
            await redis_client.aclose()
            logger.info("Conexão com Redis encerrada.")
        except Exception as exc:
            logger.warning("Erro ao fechar conexão Redis: %s", exc)


app = FastAPI(
    title="Auto Law — Dra. Lívia França",
    description="API de automação comercial e contratual com IA para advocacia trabalhista",
    version="0.1.0",
    lifespan=lifespan,
)

# Registro dos routers
app.include_router(health.router)
app.include_router(kommo.router)
app.include_router(admin.router)
app.include_router(zapsign.router)


@app.get("/")
async def root() -> dict[str, Any]:
    """Endpoint raiz para validação rápida de status da aplicação."""
    return {
        "app": "Auto Law — Dra. Lívia França",
        "status": "running",
        "version": "0.1.0",
    }
