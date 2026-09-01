"""Script interativo para simular uma conversa com a IA no terminal."""

import asyncio

from agent.graph import build_graph
from agent.state import formatar_ficha_oficial
from app.services.templates import TemplateManager


async def main() -> None:
    print("=" * 70)
    print("🤖 Auto_Law — Simulador de Atendimento da Dra. Lívia França")
    print("=" * 70)
    print("Dica: Digite as mensagens do cliente e veja as respostas da IA.")
    print("Para sair, digite 'sair' ou pressione Ctrl+C.\n")

    template_manager = TemplateManager()
    graph = build_graph()

    telefone = "5585999999999"
    chat_id = "20429066"
    config = {"configurable": {"thread_id": telefone}}

    # Saudação inicial
    saudacao = template_manager.get_texto(
        "saudacao_inicial",
        "Olá! Tudo bem? Aqui é do escritório trabalhista da Dra. Lívia França. "
        "Como podemos te ajudar com seu caso trabalhista?",
    )
    print(f"👩‍⚖️ Dra. Lívia França (IA): {saudacao}\n")

    while True:
        try:
            texto_usuario = input("👤 Cliente: ").strip()
            if not texto_usuario:
                continue
            if texto_usuario.lower() in ("sair", "exit", "quit"):
                print("\nEncerrando simulação. Até logo!")
                break

            input_data = {
                "telefone": telefone,
                "chat_id": chat_id,
                "messages": [{"role": "user", "content": texto_usuario}],
            }

            resultado = await graph.ainvoke(input_data, config=config)

            if isinstance(resultado, dict):
                fase_atual = resultado.get("fase", "analise_viabilidade")
                ficha = resultado.get("ficha", {})
                humano = resultado.get("humano_ativo", False)

                # Recupera a última mensagem gerada
                msgs = resultado.get("messages", [])
                resposta_texto = ""
                if msgs:
                    last = msgs[-1]
                    resposta_texto = getattr(last, "content", None) or str(last)

                print(f"\n👩‍⚖️ Dra. Lívia França (IA) [Etapa: {fase_atual}]:")
                print(f"{resposta_texto}\n")

                if humano:
                    print("🚨 [Transbordo/Envio de Contrato]: Bot pausado. Advogado humano assume.")
                    print("\n📋 Ficha Trabalhista gerada:")
                    print(formatar_ficha_oficial(ficha))
                    break

        except KeyboardInterrupt:
            print("\nSimulação interrompida.")
            break
        except Exception as exc:
            print(f"\n❌ Erro durante processamento: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())
