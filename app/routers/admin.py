"""Router administrativo para auditoria, inspeção e controle manual de conversas."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/conversation/{telefone}")
async def inspecionar_conversa(telefone: str) -> dict[str, Any]:
    """Inspeciona o estado atual de um lead pelo número de telefone."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint em desenvolvimento - será ativado no Sprint 5",
    )


@router.post("/conversation/{telefone}/reset")
async def resetar_conversa(telefone: str) -> dict[str, Any]:
    """Reseta o estado da conversa e limpa pendências de transbordo."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint em desenvolvimento - será ativado no Sprint 5",
    )


@router.post("/conversation/{telefone}/reativar-bot")
async def reativar_bot(telefone: str) -> dict[str, Any]:
    """Reativa o atendimento automatizado da IA para o lead."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint em desenvolvimento - será ativado no Sprint 5",
    )
