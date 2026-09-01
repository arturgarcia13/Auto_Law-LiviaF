"""Testes unitários para o gerenciador de templates (TemplateManager)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.templates import TemplateManager, get_texto


def test_template_manager_singleton() -> None:
    """Verifica se instâncias sucessivas de TemplateManager compartilham o mesmo estado."""
    tm1 = TemplateManager()
    tm2 = TemplateManager()
    assert tm1 is tm2


def test_template_manager_get_texto_existente() -> None:
    """Verifica resgate de texto para chaves conhecidas."""
    tm = TemplateManager()
    texto_saudacao = tm.get_texto("saudacao_inicial")
    assert "Dra. Lívia França" in texto_saudacao

    texto_recepcao = tm.get_texto("recepcao")
    assert "Dra. Lívia França" in texto_recepcao or "escritório trabalhista" in texto_recepcao


def test_template_manager_get_texto_normalizacao() -> None:
    """Verifica resgate de texto com chaves com acentos ou maiúsculas."""
    tm = TemplateManager()
    # Chave com acento/espaço correspondente a "recepcao"
    texto = tm.get_texto("Recepção")
    assert len(texto) > 0

    # Chave original vs normalizada
    assert tm.get_texto("saudacao_inicial") == tm.get_texto("SAUDACAO_INICIAL")


def test_template_manager_fallback() -> None:
    """Verifica retorno de fallback quando a chave não existe."""
    tm = TemplateManager()
    fallback_esperado = "Texto padrão de fallback"
    resultado = tm.get_texto("chave_inexistente_xyz_123", fallback=fallback_esperado)
    assert resultado == fallback_esperado


def test_template_manager_modulo_get_texto() -> None:
    """Verifica a função auxiliar de nível de módulo get_texto."""
    texto = get_texto("lead_qualificado")
    assert "viabilidade" in texto.lower() or "direitos" in texto.lower()


def test_template_manager_carregar_arquivo_customizado(tmp_path: Path) -> None:
    """Verifica o carregamento de templates a partir de um arquivo JSON personalizado."""
    custom_json = tmp_path / "custom_templates.json"
    dados = {
        "templates": {
            "template_teste_1": "Mensagem personalizada de teste 1",
            "template_teste_2": "Mensagem personalizada de teste 2",
        }
    }
    custom_json.write_text(json.dumps(dados), encoding="utf-8")

    tm = TemplateManager()
    tm.carregar_templates(custom_json)

    assert tm.get_texto("template_teste_1") == "Mensagem personalizada de teste 1"
    assert tm.get_texto("template_teste_2") == "Mensagem personalizada de teste 2"

    # Restaura o carregamento do arquivo padrão
    tm.carregar_templates()


def test_template_manager_arquivo_inexistente(tmp_path: Path) -> None:
    """Verifica comportamento seguro e uso de fallbacks quando o arquivo não existe."""
    arquivo_inexistente = tmp_path / "inexistente.json"
    tm = TemplateManager()
    tm.carregar_templates(arquivo_inexistente)

    # Deve continuar respondendo com os fallbacks embutidos
    assert "Dra. Lívia França" in tm.get_texto("saudacao_inicial")

    # Restaura para padrão
    tm.carregar_templates()


def test_template_manager_operadores() -> None:
    """Verifica suporte aos operadores 'in' e '[]'."""
    tm = TemplateManager()
    assert "saudacao_inicial" in tm
    assert len(tm["saudacao_inicial"]) > 0

    with pytest.raises(KeyError):
        _ = tm["chave_totalmente_inexistente_9999"]
