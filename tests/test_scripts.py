"""Testes unitários para o script de população de templates e etapas."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import respx

from scripts.popular_templates import (
    FALLBACK_STAGE_IDS,
    atualizar_env_com_etapas,
    consultar_e_salvar_templates,
    consultar_etapas_pipeline,
)


def test_consultar_etapas_pipeline_sucesso() -> None:
    """Verifica consulta das 5 etapas da pipeline via API mock do Kommo."""
    pipeline_id = 14107071
    subdomain = "liviafranaadv"
    api_key = "fake_jwt"
    endpoint = f"https://{subdomain}.kommo.com/api/v4/leads/pipelines/{pipeline_id}"

    mock_statuses = [
        {"id": 108897143, "name": "Etapa de leads de entrada"},
        {"id": 108897147, "name": "Análise de Viabilidade"},
        {"id": 108897151, "name": "Lead Qualificado"},
        {"id": 108897155, "name": "Oferta de Contrato"},
        {"id": 108897159, "name": "Envio do Contrato"},
    ]

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(endpoint).respond(
            status_code=200,
            json={"id": pipeline_id, "_embedded": {"statuses": mock_statuses}},
        )
        etapas = consultar_etapas_pipeline(subdomain, api_key, pipeline_id)
        assert etapas["KOMMO_STATUS_LEADS_ENTRADA"] == 108897143
        assert etapas["KOMMO_STATUS_ANALISE_VIABILIDADE"] == 108897147
        assert etapas["KOMMO_STATUS_LEAD_QUALIFICADO"] == 108897151
        assert etapas["KOMMO_STATUS_OFERTA_CONTRATO"] == 108897155
        assert etapas["KOMMO_STATUS_ENVIO_CONTRATO"] == 108897159


def test_consultar_etapas_pipeline_fallback_em_erro() -> None:
    """Verifica uso dos IDs de fallback quando a API falha."""
    pipeline_id = 14107071
    subdomain = "liviafranaadv"
    api_key = "fake_jwt"
    endpoint = f"https://{subdomain}.kommo.com/api/v4/leads/pipelines/{pipeline_id}"

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(endpoint).respond(status_code=500)
        etapas = consultar_etapas_pipeline(subdomain, api_key, pipeline_id)
        assert etapas == FALLBACK_STAGE_IDS


def test_atualizar_env_com_etapas(tmp_path: Path) -> None:
    """Verifica a escrita das chaves de etapas no arquivo .env."""
    env_mock = tmp_path / ".env"
    env_mock.write_text("SUBDOMAIN=liviafranaadv\nAPI_KEY=fake_key\n", encoding="utf-8")

    etapas = {
        "KOMMO_STATUS_LEADS_ENTRADA": 111,
        "KOMMO_STATUS_ANALISE_VIABILIDADE": 222,
        "KOMMO_STATUS_LEAD_QUALIFICADO": 333,
        "KOMMO_STATUS_OFERTA_CONTRATO": 444,
        "KOMMO_STATUS_ENVIO_CONTRATO": 555,
    }

    with patch("scripts.popular_templates.ENV_FILE", env_mock):
        atualizar_env_com_etapas(etapas, pipeline_id=14107071)

    conteudo = env_mock.read_text(encoding="utf-8")
    assert "KOMMO_PIPELINE_ID=14107071" in conteudo
    assert "KOMMO_STATUS_LEADS_ENTRADA=111" in conteudo
    assert "KOMMO_STATUS_ENVIO_CONTRATO=555" in conteudo
    assert "SUBDOMAIN=liviafranaadv" in conteudo


def test_consultar_e_salvar_templates(tmp_path: Path) -> None:
    """Verifica o resgate de templates e salvamento no arquivo chat_templates.json."""
    templates_json = tmp_path / "chat_templates.json"
    subdomain = "liviafranaadv"
    api_key = "fake_jwt"
    endpoint = f"https://{subdomain}.kommo.com/api/v4/chats/templates"

    mock_chat_templates = [
        {"id": 27528, "name": "Recepção", "content": "Olá, sou da equipe da Dra. Lívia."},
        {"id": 68676, "name": "Escritório", "content": "Nosso endereço é em Maracanaú - CE."},
    ]

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(endpoint).respond(
            status_code=200,
            json={"_embedded": {"chat_templates": mock_chat_templates}},
        )
        with patch("scripts.popular_templates.TEMPLATES_FILE", templates_json):
            resultado = consultar_e_salvar_templates(subdomain, api_key)

    assert templates_json.exists()
    assert "templates" in resultado
    dados_salvos = json.loads(templates_json.read_text(encoding="utf-8"))
    assert "recepcao" in dados_salvos["templates"]
    assert "escritorio" in dados_salvos["templates"]
    assert "saudacao_inicial" in dados_salvos["templates"]  # default mantido
