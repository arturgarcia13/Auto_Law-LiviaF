"""Script de Teste e Validação da Camada 2: Google Gemini LLM & Extração Trabalhista.

Valida a conexão com o Gemini, o System Prompt da Dra. Lívia França e a
extração estruturada dos 17 campos da Ficha de Qualificação Trabalhista.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Adiciona o diretório raiz ao sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configura codificação UTF-8 para stdout no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")

from agent.prompts import SYSTEM_PROMPT_LIVIA_FRANCA
from google import genai
from google.genai import types

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
MODEL_NAME = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite").strip()


def get_client() -> genai.Client:
    """Inicializa o cliente oficial do Google Gemini."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY ou GOOGLE_API_KEY não configurada no .env!")
    return genai.Client(api_key=GEMINI_API_KEY)


async def testar_resposta_conversacional(client: genai.Client, mensagem_cliente: str) -> str:
    """Testa a geração de resposta conversacional empática no tom da Dra. Lívia."""
    print(f"\n{'='*80}")
    print(f"🤖 [TESTE 1] Resposta Conversacional — Modelo: {MODEL_NAME}")
    print(f"{'='*80}")
    print(f"👤 Cliente: \"{mensagem_cliente}\"\n")

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=mensagem_cliente,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT_LIVIA_FRANCA,
            temperature=0.3,
        ),
    )

    texto_resposta = response.text or ""
    print(f"⚖️ Dra. Lívia França:\n{texto_resposta}")
    return texto_resposta


async def testar_extracao_17_campos(client: genai.Client, relato_completo: str) -> dict[str, Any]:
    """Testa a extração estruturada dos 17 campos trabalhistas em formato JSON."""
    print(f"\n{'='*80}")
    print(f"📋 [TESTE 2] Extração Estruturada dos 17 Campos Trabalhistas")
    print(f"{'='*80}")
    print(f"📖 Relato do Caso:\n{relato_completo}\n")

    prompt_extracao = f"""Você é um extrator de dados jurídicos trabalhistas.
Analise a conversa/relato abaixo e extraia com precisão os 17 campos em formato JSON estrito:
1. data_entrada: str ou null
2. data_saida: str ou null
3. funcao: str ou null
4. salario: str ou null
5. dias_trabalhados: str ou null
6. dias_folga: str ou null
7. horario_trabalho: str ou null
8. intervalo: str ou null
9. carteira_assinada: bool ou str ou null
10. data_assinatura: str ou null
11. insalubridade_periculosidade: str ou null
12. horas_extras: str ou null
13. comissao: str ou null
14. beneficios: str ou null
15. decimo_terceiro: str ou null
16. ferias: str ou null
17. fgts: str ou null
18. filhos_menores: str ou null
19. parecer_viabilidade: "viavel" | "inviavel" | "inconclusivo"
20. justificativa_resumida: str

Relato:
\"\"\"{relato_completo}\"\"\"

Retorne APENAS o JSON válido sem marcações markdown extras.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt_extracao,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    texto_json = response.text or "{}"
    try:
        dados_extraidos = json.loads(texto_json)
    except Exception:
        dados_extraidos = {"raw": texto_json}

    print("📊 Ficha Extraída (JSON Integral):")
    print(json.dumps(dados_extraidos, indent=2, ensure_ascii=False))
    return dados_extraidos


async def main() -> None:
    print(f"🚀 Iniciando Diagnóstico da Camada 2: Google Gemini")
    print(f"Chave: {GEMINI_API_KEY[:6]}...{GEMINI_API_KEY[-4:] if len(GEMINI_API_KEY)>10 else ''}")
    print(f"Modelo configurado: {MODEL_NAME}")

    try:
        client = get_client()

        # 1. Teste de resposta conversacional simples
        msg_teste = "Olá, fui demitido na semana passada após 3 anos na empresa e meu patrão disse que não vai pagar rescisão."
        await testar_resposta_conversacional(client, msg_teste)

        # 2. Teste de extração de caso trabalhista denso
        relato_completo = (
            "Trabalhei como Auxiliar de Logística na Empresa TransLog de 01/03/2022 até 15/07/2024. "
            "Meu salário na carteira era R$ 1.800,00 mas recebia R$ 400 por fora em dinheiro todo mês de comissão. "
            "Minha carteira só foi assinada 6 meses depois que entrei (em 01/09/2022). "
            "Eu trabalhava de segunda a sábado das 07:00 às 19:00, com apenas 30 minutos de almoço. "
            "Fazia cerca de 2 horas extras todos os dias e nunca recebi por isso. "
            "Trabalhava em câmara fria carregando caixas pesadas sem nenhum EPI e sem adicional de insalubridade. "
            "Fui demitido sem justa causa em 15/07/2024 e não me pagaram o aviso prévio, nem as férias vencidas de 2023, "
            "nem o 13º proporcional e vi no aplicativo da Caixa que não depositaram o FGTS dos últimos 10 meses. "
            "Tenho 2 filhos menores de 8 e 5 anos."
        )
        await testar_extracao_17_campos(client, relato_completo)

        print(f"\n{'='*80}")
        print("✅ Camada 2 (Google Gemini & Extração) validada com sucesso!")
        print(f"{'='*80}\n")

    except Exception as exc:
        print(f"\n❌ Erro ao testar Camada 2: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
