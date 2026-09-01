"""Serviço assíncrono para download e transcrição de áudios via Google Gemini Flash STT."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

PROMPT_TRANSCRICAO = (
    "Você é um transcritor especializado em áudios de WhatsApp para o escritório de advocacia "
    "da Dra. Lívia França. Transcreva o áudio com máxima fidelidade em português brasileiro, "
    "preservando nomes, valores, datas, relatos sobre trabalho, empresas e termos informados "
    "pelo cliente. Retorne apenas o texto transcrito puro, sem comentários adicionais."
)


async def baixar_audio(media_url: str, timeout: float = 30.0) -> bytes:
    """Baixa os bytes do arquivo de áudio a partir de uma URL remota."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(media_url)
        response.raise_for_status()
        return response.content


async def transcrever_audio(
    audio_data: str | bytes,
    mime_type: str = "audio/ogg",
    model: str | None = None,
) -> str:
    """Transcreve mensagem de voz/áudio para texto utilizando o Google Gemini Flash Multimodal STT.

    Args:
        audio_data: Bytes do áudio, caminho local do arquivo ou URL HTTP/HTTPS para download.
        mime_type: Tipo MIME do áudio (ex: audio/ogg, audio/mp3, audio/wav, audio/m4a).
        model: Identificador do modelo Gemini (padrão: gemini-2.5-flash ou GEMINI_STT_MODEL).

    Returns:
        Texto transcrito puro em português brasileiro.
    """
    audio_bytes: bytes

    if isinstance(audio_data, str):
        if audio_data.startswith("http://") or audio_data.startswith("https://"):
            logger.info(f"Baixando áudio da URL: {audio_data}")
            audio_bytes = await baixar_audio(audio_data)
        else:
            path = Path(audio_data)
            if path.exists() and path.is_file():
                audio_bytes = path.read_bytes()
            else:
                raise ValueError(
                    f"Caminho de arquivo de áudio inválido ou não encontrado: {audio_data}"
                )
    elif isinstance(audio_data, (bytes, bytearray)):
        audio_bytes = bytes(audio_data)
    else:
        raise TypeError(f"Tipo de audio_data não suportado: {type(audio_data)}")

    if not audio_bytes:
        logger.warning("Bytes de áudio vazios fornecidos para transcrição.")
        return ""

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("Chave de API do Google Gemini não configurada.")
        raise ValueError("Chave de API do Gemini não encontrada no ambiente.")

    target_model: str = str(model or os.getenv("GEMINI_STT_MODEL", "gemini-2.5-flash"))
    client = genai.Client(api_key=api_key)

    try:
        response = await client.aio.models.generate_content(
            model=target_model,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                PROMPT_TRANSCRICAO,
            ],
        )

        texto = response.text.strip() if response and response.text else ""
        return texto
    except Exception as exc:
        logger.error(f"Falha ao transcrever áudio com Gemini ({target_model}): {exc}")
        raise
