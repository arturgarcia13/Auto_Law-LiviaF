#!/usr/bin/env python3
"""CLI para Gestão, Auditoria e Auto-Cura de Webhooks no Kommo CRM.

Permite listar, inserir, alterar permissões, remover, testar e executar a
auto-cura de webhooks da plataforma Kommo via terminal ou scripts de automação.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Garante inclusão do diretório raiz no sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configura UTF-8 no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

from integrations.kommo import (  # noqa: E402
    DEFAULT_WEBHOOK_EVENTS,
    KOMMO_AVAILABLE_WEBHOOK_EVENTS,
    criar_webhook,
    garantir_webhook_ativo,
    listar_webhooks,
    modificar_webhook_permissoes,
    remover_webhook,
    testar_ping_webhook,
)


def _obter_url_padrao() -> str:
    """Deriva a URL do webhook padrão com base no .env."""
    domain = (os.getenv("NGROK_DOMAIN") or "").strip()
    secret = (os.getenv("KOMMO_WEBHOOK_SECRET") or "").strip()
    if not domain:
        return ""
    scheme = "https://" if not domain.startswith("http") else ""
    query = f"?token={secret}" if secret else ""
    return f"{scheme}{domain}/kommo/webhook{query}"


async def cmd_listar(destination: str | None, as_json: bool) -> int:
    webhooks = await listar_webhooks(destination=destination)
    if as_json:
        print(json.dumps(webhooks, indent=2, ensure_ascii=False))
        return 0

    print("\n" + "=" * 70)
    print(f"📋 WEBHOOKS CADASTRADOS NO KOMMO CRM (Total: {len(webhooks)})")
    print("=" * 70)
    if not webhooks:
        print("ℹ️ Nenhum webhook encontrado na conta.")
        return 0

    for i, w in enumerate(webhooks, 1):
        status_txt = "🔴 DESATIVADO" if w.get("disabled") else "🟢 ATIVO"
        print(f"\n[{i}] ID: {w.get('id')} | Status: {status_txt}")
        print(f"    URL:      {w.get('destination')}")
        print(f"    Eventos:  {', '.join(w.get('settings', []))}")
        if w.get("created_at"):
            print(f"    Criado:   {w.get('created_at')}")
    print("\n" + "=" * 70)
    return 0


async def cmd_eventos(as_json: bool) -> int:
    dados = {
        "default": DEFAULT_WEBHOOK_EVENTS,
        "available": KOMMO_AVAILABLE_WEBHOOK_EVENTS,
    }
    if as_json:
        print(json.dumps(dados, indent=2, ensure_ascii=False))
        return 0

    print("\n" + "=" * 70)
    print("📌 EVENTOS DISPONÍVEIS NA API V4 DO KOMMO CRM")
    print("=" * 70)
    print(f"👉 Evento Padrão Atual: {DEFAULT_WEBHOOK_EVENTS}\n")
    for categoria, eventos in KOMMO_AVAILABLE_WEBHOOK_EVENTS.items():
        print(f"📂 {categoria.upper()}:")
        for ev in eventos:
            print(f"   · {ev}")
    print("=" * 70)
    return 0


async def cmd_inserir(destination: str, events: list[str], as_json: bool) -> int:
    if not destination:
        print("❌ Erro: URL de destino não informada e não encontrada no .env.", file=sys.stderr)
        return 1

    print(f"🚀 Cadastrando webhook no Kommo: {destination}")
    print(f"👉 Eventos solicitados: {events}")
    res = await criar_webhook(destination=destination, events=events)

    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    if res.get("ok"):
        print(f"✅ Webhook cadastrado com sucesso! (Status HTTP: {res.get('status_code')})")
        return 0
    else:
        print(
            f"❌ Falha ao cadastrar webhook: {res.get('error') or res.get('data')}", file=sys.stderr
        )
        return 1


async def cmd_modificar(destination: str, events: list[str], as_json: bool) -> int:
    if not destination:
        print("❌ Erro: URL de destino não informada.", file=sys.stderr)
        return 1

    print(f"🔄 Modificando permissões do webhook: {destination}")
    print(f"👉 Novos eventos: {events}")
    res = await modificar_webhook_permissoes(destination=destination, events=events)

    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    if res.get("ok"):
        print("✅ Permissões modificadas com sucesso!")
        return 0
    else:
        print(
            f"❌ Falha ao atualizar permissões: {res.get('create_step', {}).get('error')}",
            file=sys.stderr,
        )
        return 1


async def cmd_remover(destination: str, as_json: bool) -> int:
    if not destination:
        print("❌ Erro: URL de destino não informada.", file=sys.stderr)
        return 1

    print(f"🗑️ Removendo webhook na Kommo: {destination}")
    res = await remover_webhook(destination=destination)

    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    if res.get("ok"):
        print("✅ Webhook removido com sucesso!")
        return 0
    else:
        print(
            f"❌ Falha ao remover webhook: {res.get('data') or res.get('error')}", file=sys.stderr
        )
        return 1


async def cmd_verificar(destination: str, as_json: bool) -> int:
    if not destination:
        print("❌ Erro: URL de destino não informada.", file=sys.stderr)
        return 1

    print(f"🔍 Auditando webhook: {destination}")
    webhooks = await listar_webhooks(destination=destination)
    ping = await testar_ping_webhook(destination)

    registrado = len(webhooks) > 0
    webhook_obj = webhooks[0] if registrado else {}
    desativado = webhook_obj.get("disabled", False)
    eventos = webhook_obj.get("settings", [])
    ping_ok = ping.get("ok", False)

    is_healthy = registrado and (not desativado) and ping_ok

    relatorio = {
        "ok": is_healthy,
        "destination": destination,
        "registrado": registrado,
        "ativo": not desativado if registrado else False,
        "eventos": eventos,
        "ping": ping,
    }

    if as_json:
        print(json.dumps(relatorio, indent=2, ensure_ascii=False))
        return 0 if is_healthy else 1

    print("\n" + "=" * 70)
    print("🩺 RELATÓRIO DE AUDITORIA DO WEBHOOK")
    print("=" * 70)
    print(f"URL Alvo:           {destination}")
    print(f"Registrado no CRM:  {'✅ SIM' if registrado else '❌ NÃO'}")
    if registrado:
        print(f"Status no CRM:      {'🔴 DESATIVADO' if desativado else '🟢 ATIVO'}")
        print(f"Eventos Inscritos:  {', '.join(eventos) if eventos else 'Nenhum'}")
    lat = ping.get("latency_ms")
    cod = ping.get("status_code")
    ping_ico = "✅ OK" if ping_ok else "❌ FALHOU"
    print(f"Teste Ping Local:   {ping_ico} ({lat} ms, HTTP {cod})")
    print("-" * 70)
    if is_healthy:
        print("✨ DIAGNÓSTICO: Webhook 100% operacional e saudável!")
    else:
        print("⚠️ DIAGNÓSTICO: Webhook necessita de reparo/auto-cura.")
    print("=" * 70 + "\n")
    return 0 if is_healthy else 1


async def cmd_sync(destination: str, events: list[str], as_json: bool) -> int:
    if not destination:
        print("❌ Erro: URL de destino não configurada.", file=sys.stderr)
        return 1

    print("⚡ [AUTO-CURA] Sincronizando webhook na Kommo...")
    print(f"👉 URL:     {destination}")
    print(f"👉 Eventos: {events}")

    res = await garantir_webhook_ativo(destination=destination, required_events=events)

    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res.get("ok") else 1

    print("\n" + "=" * 70)
    if res.get("action") == "none":
        print("✅ [SAUDÁVEL] Webhook já está cadastrado, ativo e respondendo!")
    else:
        print("🔄 [REPARADO] Webhook foi removido e reinserido com sucesso!")
        if res.get("motivos_reparo"):
            print(f"   Motivos do reparo: {', '.join(res.get('motivos_reparo', []))}")

    print(f"👉 Status Final:  {'🟢 OPERACIONAL' if res.get('ok') else '🔴 FALHA'}")
    print(f"👉 Eventos:       {', '.join(res.get('events', []))}")
    ping = res.get("ping", {})
    print(f"👉 Teste Ping:    HTTP {ping.get('status_code')} em {ping.get('latency_ms')} ms")
    print("=" * 70 + "\n")
    return 0 if res.get("ok") else 1


async def main_async() -> int:
    parser = argparse.ArgumentParser(
        description="Gestor e Auto-Cura de Webhooks do Kommo CRM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--sync",
        action="store_true",
        help="Executa ciclo de auto-cura (verifica, recria se necessário e testa)",
    )
    action_group.add_argument(
        "--listar", action="store_true", help="Lista os webhooks cadastrados na Kommo"
    )
    action_group.add_argument(
        "--inserir", action="store_true", help="Cadastra novo webhook na Kommo"
    )
    action_group.add_argument(
        "--modificar",
        action="store_true",
        help="Modifica eventos/permissões de um webhook existente",
    )
    action_group.add_argument("--remover", action="store_true", help="Remove webhook cadastrado")
    action_group.add_argument(
        "--verificar", action="store_true", help="Audita status e ping do webhook"
    )
    action_group.add_argument(
        "--eventos", action="store_true", help="Lista todos os eventos suportados pela Kommo"
    )

    parser.add_argument(
        "--url",
        type=str,
        default="",
        help="URL de destino do webhook (default: detectada via .env)",
    )
    parser.add_argument(
        "--events",
        type=str,
        default="add_message",
        help="Lista de eventos separados por vírgula (default: add_message)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Exibe saída em formato JSON estruturado"
    )

    args = parser.parse_args()

    url_alvo = args.url.strip() or _obter_url_padrao()
    lista_eventos = [e.strip() for e in args.events.split(",") if e.strip()]
    if not lista_eventos:
        lista_eventos = DEFAULT_WEBHOOK_EVENTS

    if args.eventos:
        return await cmd_eventos(as_json=args.json)
    elif args.listar:
        return await cmd_listar(destination=args.url.strip() or None, as_json=args.json)
    elif args.inserir:
        return await cmd_inserir(destination=url_alvo, events=lista_eventos, as_json=args.json)
    elif args.modificar:
        return await cmd_modificar(destination=url_alvo, events=lista_eventos, as_json=args.json)
    elif args.remover:
        return await cmd_remover(destination=url_alvo, as_json=args.json)
    elif args.verificar:
        return await cmd_verificar(destination=url_alvo, as_json=args.json)
    elif args.sync:
        return await cmd_sync(destination=url_alvo, events=lista_eventos, as_json=args.json)

    return 0


def main() -> None:
    codigo = asyncio.run(main_async())
    sys.exit(codigo)


if __name__ == "__main__":
    main()
