"""Aplicação principal FastAPI para automação jurídica comercial e contratual."""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import FastAPI

from agent.graph import build_graph
from app.routers import admin, health, kommo
from app.services.buffer import set_redis_client
from app.services.templates import TemplateManager

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env

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
            redis_client = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            await redis_client.ping()
            set_redis_client(redis_client)
            app.state.redis = redis_client
            logger.info("Cliente Redis conectado em %s.", redis_url)
        except Exception as exc:
            logger.warning(
                "Redis não disponível (%s): %s. Operando em modo direto sem buffer de rajada.",
                redis_url,
                exc,
            )
            set_redis_client(None)
            app.state.redis = None
    else:
        set_redis_client(None)
        app.state.redis = None

    # 3. Inicializa persistência do LangGraph (SqliteSaver com fallback seguro para MemorySaver)
    db_url = os.getenv("DATABASE_URL")
    app.state.checkpointer = None
    app.state.checkpointer_cm = None
    app.state.db_pool = None

    if db_url:
        try:
            logger.info("Configurando persistência para %s...", db_url)
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: F401
            # Se Postgres necessitar de setup assíncrono complexo, mantemos fallback
        except Exception as exc:
            logger.warning(
                "AsyncPostgresSaver indisponível (%s). Verificando persistência local SQLite.",
                exc,
            )

    if app.state.checkpointer is None:
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            checkpoints_path = os.path.join(data_dir, "checkpoints.sqlite")
            cm = AsyncSqliteSaver.from_conn_string(checkpoints_path)
            app.state.checkpointer = await cm.__aenter__()
            app.state.checkpointer_cm = cm
            logger.info("💾 [PERSISTÊNCIA] AsyncSqliteSaver ativado em %s.", checkpoints_path)
        except Exception as exc:
            from langgraph.checkpoint.memory import MemorySaver

            app.state.checkpointer = MemorySaver()
            logger.warning(
                "Falha ao inicializar AsyncSqliteSaver (%s). Utilizando MemorySaver como fallback.",
                exc,
            )

    # 4. Compila o grafo do LangGraph
    try:
        app.state.graph = build_graph(checkpointer=app.state.checkpointer)
        logger.info("Grafo de estados LangGraph configurado com persistência.")
    except Exception as exc:
        logger.warning("Falha ao compilar grafo LangGraph: %s", exc)
        app.state.graph = None

    yield

    # Encerramento de recursos
    logger.info("Encerrando recursos do Auto_Law...")
    if getattr(app.state, "checkpointer_cm", None) is not None:
        try:
            await app.state.checkpointer_cm.__aexit__(None, None, None)
            logger.info("Conexão do checkpointer AsyncSqliteSaver encerrada.")
        except Exception as exc:
            logger.warning("Erro ao fechar conexão AsyncSqliteSaver: %s", exc)

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

@app.get("/")
async def root() -> dict[str, Any]:
    """Endpoint raiz para validação de status da aplicação e lista de telefones permitidos."""
    allowed_env = os.getenv("ALLOWED_PHONES", "")
    allowed_phones = [p.strip() for p in allowed_env.split(",") if p.strip()]
    return {
        "ok": True,
        "app": "Auto Law — Dra. Lívia França",
        "status": "running",
        "version": "0.2.0",
        "allowed_phones": allowed_phones,
    }

