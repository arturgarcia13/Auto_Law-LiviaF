# 📑 Architecture Decision Records (ADRs) — Auto_Law-LiviaF

Este diretório contém os registros formais de decisões arquiteturais (ADRs) do projeto de automação comercial e contratual do escritório de advocacia da Dra. Lívia França.

---

## Índice de Decisões Arquiteturais

| ID | Título | Status | Data | Resumo da Decisão |
|:---|:---|:---:|:---:|:---|
| [ADR-001](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-001-orquestrador-langgraph-vs-n8n.md) | Escolha do Orquestrador de Agente de IA | **Aceito** | 2026-08-27 | Adoção de **LangGraph + FastAPI** (Python puro) em substituição ao n8n para controle determinístico de estados e observabilidade profunda. |
| [ADR-002](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-002-gateway-whatsapp-evolution-baileys.md) | Gateway WhatsApp — Evolution API (Modo Baileys) | **Substituído** | 2026-08-27 | Substituído pela [ADR-008](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-008-gateway-kommo-chats.md) em favor da API nativa de conversas do Kommo CRM. |
| [ADR-003](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-003-observabilidade-langfuse-self-hosted.md) | Observabilidade e Tracing LLM — Langfuse Self-Hosted | **Aceito** | 2026-08-27 | Hospedagem do **Langfuse no próprio Docker Compose** para garantir sigilo advocatício, conformidade LGPD e zero custo recorrente de tracing. |
| [ADR-004](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-004-persistencia-postgresql-database-isolada.md) | Persistência de Dados — PostgreSQL Único Multi-DB | **Aceito** | 2026-08-27 | Um **único container PostgreSQL 16** com bases lógicas isoladas (`autolaw`, `langfuse`) para evitar conflito de schemas e economizar RAM. |
| [ADR-005](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-005-custo-zapsign-e-envio-via-evolution.md) | Integração ZapSign — Disparo de Link via WhatsApp | **Postergado** | 2026-08-27 | Emissão de contratos via ZapSign postergada para fases futuras do projeto. |
| [ADR-006](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-006-pipeline-incremental-e-tdd.md) | Metodologia — TDD e Docker Compose Incremental | **Aceito** | 2026-08-27 | Execução em sprints incrementais orientados a testes (TDD), subindo os serviços de infraestrutura apenas quando necessários. |
| [ADR-007](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-007-gestao-de-transbordo-e-reativacao-do-agente.md) | Gestão de Transbordo Humano e Reativação | **Aceito** | 2026-08-27 | Silenciamento imediato do bot via flag `humano_ativo` no LangGraph com **reativação automática orientada a eventos via webhook do Kommo CRM**. |
| [ADR-008](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-008-gateway-kommo-chats.md) | Gateway WhatsApp via Conversas do Kommo CRM | **Aceito** | 2026-08-31 | Utilização da **API de Conversas do Kommo CRM** para recepção e envio de mensagens WhatsApp, eliminando a dependência da Evolution API. |
| [ADR-009](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-009-processamento-audio-gemini-stt.md) | Transcrição de Áudio via Gemini Multimodal STT | **Aceito** | 2026-08-31 | Transcrição assíncrona de mensagens de voz/áudio utilizando o **Google Gemini Flash**, garantindo compreensão nativa de áudios no WhatsApp sem custos adicionais. |
| [ADR-010](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-010-lista-permissao-ambiente-testes-allowed-chat-ids.md) | Lista de Permissão em Ambientes de Teste (`ALLOWED_CHAT_IDS`) | **Aceito** | 2026-08-31 | Mecanismo de **Allowlist via `.env`** para isolamento de tráfego de testes no Kommo WhatsApp, impedindo respostas automáticas a clientes reais. |


---

## Formato Padrão das ADRs

Todas as ADRs seguem o padrão arquitetural estruturado em:
1. **Contexto e Problema**: Motivação de negócio e desafios técnicos.
2. **Alternativas Consideradas**: Prós e contras de cada caminho tecnológico analisado.
3. **Decisão**: A solução adotada e sua justificativa técnica.
4. **Consequências**: Benefícios diretos, riscos e suas respectivas estratégias de mitigação.
