"""Script para testar a injeção de mensagens na timeline do lead via API de Notes da Kommo."""

import os
import sys
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# UTF-8 para Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(ROOT_DIR / ".env")

SUBDOMAIN = (os.getenv("KOMMO_SUBDOMAIN") or os.getenv("SUBDOMAIN") or "liviafranaadv").strip()
API_KEY = (os.getenv("KOMMO_API_KEY") or os.getenv("API_KEY") or "").strip()
LEAD_ID = 20429066  # Lead de teste

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def testar_note_type(nome_teste: str, payload_note: list[dict]):
    url = f"https://{SUBDOMAIN}.kommo.com/api/v4/leads/{LEAD_ID}/notes"
    print(f"\n{'='*70}\n🧪 Testando {nome_teste}\nPOST {url}\n{'='*70}")
    print("Payload enviado:")
    print(json.dumps(payload_note, indent=2, ensure_ascii=False))

    with httpx.Client(timeout=15.0) as client:
        try:
            res = client.post(url, json=payload_note, headers=HEADERS)
            print(f"\nStatus HTTP: {res.status_code}")
            try:
                print("Response JSON:")
                print(json.dumps(res.json(), indent=2, ensure_ascii=False))
            except Exception:
                print("Response Text:", res.text)
            return res.status_code, res.text
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
            return None, str(e)


def main():
    print(f"🚀 Iniciando teste de injeção de notas no Lead ID: {LEAD_ID}")
    print(f"Subdomínio: {SUBDOMAIN}")

    # Teste 1: extended_service_message (código do usuário)
    payload_1 = [
        {
            "note_type": "extended_service_message",
            "params": {
                "text": "Olá! Teste de mensagem via extended_service_message da Dra. Lívia.",
                "service": "WhatsApp"
            }
        }
    ]
    testar_note_type("1. extended_service_message", payload_1)

    # Teste 2: service_message
    payload_2 = [
        {
            "note_type": "service_message",
            "params": {
                "text": "Olá! Teste de mensagem via service_message da Dra. Lívia.",
                "service": "WhatsApp"
            }
        }
    ]
    testar_note_type("2. service_message", payload_2)

    # Teste 3: common (nota padrão da timeline)
    payload_3 = [
        {
            "note_type": "common",
            "params": {
                "text": "💬 [RESPOSTA IA] Olá! Teste de nota comum na timeline da Dra. Lívia."
            }
        }
    ]
    testar_note_type("3. common (nota padrão)", payload_3)


if __name__ == "__main__":
    main()
