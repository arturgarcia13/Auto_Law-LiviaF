"""Aplicação principal FastAPI para automação jurídica comercial e contratual."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager para inicialização de recursos (Postgres, Redis, Scheduler)."""
    # Recursos de persistência e grafo do LangGraph serão vinculados nas sprints posteriores
    yield


app = FastAPI(
    title="Auto Law — Dra. Lívia França",
    description="API de automação comercial e contratual com IA para advocacia trabalhista",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, Any]:
    """Endpoint raiz para validação rápida de status da aplicação."""
    return {"app": "Auto Law — Dra. Lívia França", "status": "running", "version": "0.1.0"}
