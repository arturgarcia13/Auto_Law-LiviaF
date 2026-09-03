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
| [ADR-008](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-008-gateway-kommo-chats.md) | Gateway WhatsApp via Conversas do Kommo CRM | **Substituído** | 2026-08-31 | Substituído pela [ADR-011](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-011-gateway-whatsapp-meta-cloud-api.md) em favor da Meta WhatsApp Cloud API. |
| [ADR-009](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-009-processamento-audio-gemini-stt.md) | Transcrição de Áudio via Gemini Multimodal STT | **Aceito** | 2026-08-31 | Transcrição assíncrona de mensagens de voz/áudio utilizando o **Google Gemini Flash**, garantindo compreensão nativa de áudios no WhatsApp sem custos adicionais. |
| [ADR-010](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-010-lista-permissao-ambiente-testes-allowed-chat-ids.md) | Lista de Permissão em Ambientes de Teste (`ALLOWED_CHAT_IDS`) | **Substituído** | 2026-08-31 | Substituído pela [ADR-011](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-011-gateway-whatsapp-meta-cloud-api.md) em favor de `ALLOWED_PHONES`. |
| [ADR-011](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-011-gateway-whatsapp-meta-cloud-api.md) | Gateway WhatsApp via Meta Cloud API e Kommo CRM | **Aceito** | 2026-09-02 | Adoção da **Meta WhatsApp Cloud API (Graph API)** para disparos de mensagens e templates com sincronização de notas/etapas no Kommo CRM e allowlist por `ALLOWED_PHONES`. |
| [ADR-012](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-012-tunel-estatico-ngrok.md) | Túnel de Desenvolvimento Seguro com Domínio Estático Ngrok | **Aceito** | 2026-09-02 | Substituição do Cloudflare Quick Tunnel pelo **Ngrok com domínio estático gratuito permanente**, eliminando reconfigurações manuais de URLs de webhooks. |
| [ADR-013](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-013-deduplicacao-idempotencia-fast-ack.md) | Deduplicação de Mensagens (Idempotência) e Fast ACK para Webhooks | **Aceito** | 2026-09-02 | Implementação de **Fast ACK (< 50ms)** no webhook da Kommo e serviço `MessageDeduplicator` com TTL de 15min para eliminar retentativas e disparos repetidos. |
| [ADR-014](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-014-memoria-langgraph-contexto-temporal.md) | Persistência de Memória Conversacional e Injeção de Contexto Temporal | **Aceito** | 2026-09-02 | Adoção de `MemorySaver()` e `add_messages` no LangGraph para retenção de turnos anteriores e injeção de data/hora oficial no fuso de Brasília. |



---

## Formato Padrão das ADRs

Todas as ADRs seguem o padrão arquitetural estruturado em:
1. **Contexto e Problema**: Motivação de negócio e desafios técnicos.
2. **Alternativas Consideradas**: Prós e contras de cada caminho tecnológico analisado.
3. **Decisão**: A solução adotada e sua justificativa técnica.
4. **Consequências**: Benefícios diretos, riscos e suas respectivas estratégias de mitigação.
