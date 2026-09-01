"""Testes unitários para o serviço de transcrição de áudio via Gemini Flash STT."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from app.services.audio import baixar_audio, transcrever_audio


@pytest.mark.asyncio
async def test_baixar_audio_sucesso() -> None:
    """Verifica o download assíncrono de bytes de áudio a partir de uma URL."""
    url = "https://media.kommo.com/audio/sample_audio.ogg"
    conteudo_esperado = b"OGG_AUDIO_BYTES_MOCK"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(url).respond(status_code=200, content=conteudo_esperado)
        resultado = await baixar_audio(url)
        assert resultado == conteudo_esperado


@pytest.mark.asyncio
async def test_baixar_audio_falha_http() -> None:
    """Verifica se erro HTTP no download dispara exceção apropriada."""
    url = "https://media.kommo.com/audio/erro.ogg"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(url).respond(status_code=404)
        with pytest.raises(httpx.HTTPStatusError):
            await baixar_audio(url)


@pytest.mark.asyncio
async def test_transcrever_audio_com_bytes() -> None:
    """Verifica a transcrição de áudio passando bytes diretamente com mock do Gemini."""
    audio_bytes = b"FAKE_AUDIO_DATA_FOR_TESTING"
    texto_esperado = "Trabalhei 3 anos como estoquista sem receber horas extras."

    mock_response = MagicMock()
    mock_response.text = texto_esperado

    mock_models = MagicMock()
    mock_models.generate_content = AsyncMock(return_value=mock_response)

    mock_client = MagicMock()
    mock_client.aio.models = mock_models

    with patch("app.services.audio.genai.Client", return_value=mock_client), patch.dict(
        "os.environ", {"GEMINI_API_KEY": "fake_gemini_key"}
    ):
        resultado = await transcrever_audio(audio_bytes, mime_type="audio/ogg")
        assert resultado == texto_esperado
        mock_models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_transcrever_audio_com_url() -> None:
    """Verifica a transcrição de áudio a partir de uma URL remota."""
    url = "https://kommo.com/audio/test_voice.ogg"
    audio_bytes = b"REMOTE_AUDIO_BYTES"
    texto_esperado = "Fui demitido sem justa causa na semana passada."

    mock_response = MagicMock()
    mock_response.text = texto_esperado

    mock_models = MagicMock()
    mock_models.generate_content = AsyncMock(return_value=mock_response)

    mock_client = MagicMock()
    mock_client.aio.models = mock_models

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(url).respond(status_code=200, content=audio_bytes)
        with patch("app.services.audio.genai.Client", return_value=mock_client), patch.dict(
            "os.environ", {"GOOGLE_API_KEY": "fake_google_key"}
        ):
            resultado = await transcrever_audio(url, mime_type="audio/ogg")
            assert resultado == texto_esperado


@pytest.mark.asyncio
async def test_transcrever_audio_arquivo_local(tmp_path: Path) -> None:
    """Verifica a transcrição de áudio passando o caminho de um arquivo local."""
    arquivo_audio = tmp_path / "gravacao.ogg"
    arquivo_audio.write_bytes(b"LOCAL_AUDIO_PAYLOAD")
    texto_esperado = "Nunca recebi adicional de insalubridade."

    mock_response = MagicMock()
    mock_response.text = texto_esperado

    mock_models = MagicMock()
    mock_models.generate_content = AsyncMock(return_value=mock_response)

    mock_client = MagicMock()
    mock_client.aio.models = mock_models

    with patch("app.services.audio.genai.Client", return_value=mock_client), patch.dict(
        "os.environ", {"GEMINI_API_KEY": "fake_gemini_key"}
    ):
        resultado = await transcrever_audio(str(arquivo_audio))
        assert resultado == texto_esperado


@pytest.mark.asyncio
async def test_transcrever_audio_vazio() -> None:
    """Verifica que bytes de áudio vazios retornam string vazia sem chamar o LLM."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_gemini_key"}):
        resultado = await transcrever_audio(b"")
        assert resultado == ""


@pytest.mark.asyncio
async def test_transcrever_audio_sem_api_key() -> None:
    """Verifica que a ausência de chave de API dispara ValueError."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
        # Garante que os getenv retornem vazio
        with patch("os.getenv", return_value=""):
            with pytest.raises(ValueError, match="Chave de API do Gemini"):
                await transcrever_audio(b"AUDIO_DATA")
