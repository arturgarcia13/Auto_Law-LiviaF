# 📚 Documentação Técnica — Auto_Law-LiviaF

Bem-vindo à central de documentação da automação comercial e contratual do escritório de advocacia da Dra. Lívia França.

---

## 🗂️ Estrutura do Diretório `docs/`

```
docs/
├── README.md                          # Este índice geral
│
├── artifacts/                         # Artefatos técnicos centrais e seus metadados
│   ├── plano_funil_vendas_kommo.md              # ⭐ [PLANO ATUAL] Funil de Vendas (Pipeline 14107071)
│   ├── plano_funil_vendas_kommo.md.metadata.json
│   ├── plano_migracao_kommo_audio.md            # Transição Kommo Messaging & Áudio com IA
│   ├── plano_migracao_kommo_audio.md.metadata.json
│   ├── plano_automacao_livia_franca.md          # Arquitetura original e especificação inicial
│   ├── plano_automacao_livia_franca.md.metadata.json
│   ├── pipeline_desenvolvimento.md              # Roteiro incremental TDD
│   ├── pipeline_desenvolvimento.md.metadata.json
│   ├── n8n_vs_langgraph.md                      # Análise comparativa técnica e benchmark
│   └── n8n_vs_langgraph.md.metadata.json
│
└── adr/                               # Architecture Decision Records (ADRs)
    ├── README.md                                # Índice e sumário executivo das ADRs
    ├── ADR-001-orquestrador-langgraph-vs-n8n.md
    ├── ADR-002-gateway-whatsapp-evolution-baileys.md (Substituído por ADR-008)
    ├── ADR-003-observabilidade-langfuse-self-hosted.md
    ├── ADR-004-persistencia-postgresql-database-isolada.md
    ├── ADR-005-custo-zapsign-e-envio-via-evolution.md (Postergado)
    ├── ADR-006-pipeline-incremental-e-tdd.md
    ├── ADR-007-gestao-de-transbordo-e-reativacao-do-agente.md
    ├── ADR-008-gateway-kommo-chats.md           # [NOVO] Mensageria nativa Kommo CRM
    ├── ADR-009-processamento-audio-gemini-stt.md # [NOVO] Transcrição de áudio Gemini STT
    └── ADR-010-lista-permissao-ambiente-testes-allowed-chat-ids.md # [NOVO] Allowlist de testes
```

---

## 🏛️ 1. Artefatos Centrais do Projeto

Os artefatos abaixo documentam todas as especificações de requisitos, payloads, diagramas de sequência e o planejamento de entrega:

### [1. Plano de Arquitetura & Implementação — Pipeline 'FUNIL DE VENDAS' (Dra. Lívia França)](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/plano_funil_vendas_kommo.md) ⭐ **[PLANO VIGENTE]**
* **Arquivo**: `docs/artifacts/plano_funil_vendas_kommo.md`
* **Metadados**: `docs/artifacts/plano_funil_vendas_kommo.md.metadata.json`
* **Conteúdo**:
  - Mapeamento das 5 etapas da pipeline `14107071`: *Leads de Entrada -> Análise de Viabilidade -> Lead Qualificado -> Oferta de Contrato -> Envio do Contrato*.
  - Análise de viabilidade focada estritamente em causas da alçada trabalhista da Dra. Lívia França.
  - Resgate dinâmico de modelos de chat via Kommo API (`/api/v4/chats/templates`).
  - Handoff com silenciamento automático do bot e criação de tarefa no Kommo para o advogado enviar o contrato.

### [2. Pipeline & Fases de Desenvolvimento](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/pipeline_desenvolvimento.md) ⭐ **[ROADMAP VIGENTE]**
* **Arquivo**: `docs/artifacts/pipeline_desenvolvimento.md`
* **Conteúdo**:
  - Matriz consolidada das **9 Fases do Projeto** (Fases 1 a 6 Concluídas, Fase 7 de Higienização Concluída, Fases 8 e 9 de Homologação/Observabilidade no Backlog).
  - Soberania com ChatOllama (`llama3.1:8b`), Meta Cloud API, Kommo CRM e persistência SQLite/Postgres.
  - Registro de descontinuação definitiva de escopos legados (Evolution API, ZapSign e ADVBOX).

### [3. Arquitetura em 4 Camadas](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/plano_reconstrucao_camadas.md)
* **Arquivo**: `docs/artifacts/plano_reconstrucao_camadas.md`
* **Conteúdo**:
  - Especificação detalhada das 4 camadas ativas: Kommo CRM API v4 (Camada 1), Inteligência Soberana ChatOllama + Gemini STT (Camada 2), Orquestração LangGraph & Persistência (Camada 3) e Gateway FastAPI + Meta Cloud API + Fast ACK (Camada 4).

### [4. Plano de Arquitetura & Implementação — Kommo CRM Messaging & Áudio com IA](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/plano_migracao_kommo_audio.md)
* **Arquivo**: `docs/artifacts/plano_migracao_kommo_audio.md`
* **Metadados**: `docs/artifacts/plano_migracao_kommo_audio.md.metadata.json`
* **Conteúdo**:
  - Unificação da mensageria via Kommo CRM e Meta Cloud API.
  - Recepção e transcrição de áudios com Google Gemini Flash Multimodal STT.

### [5. Análise Comparativa: n8n vs. LangGraph](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/n8n_vs_langgraph.md)
* **Arquivo**: `docs/artifacts/n8n_vs_langgraph.md`
* **Metadados**: `docs/artifacts/n8n_vs_langgraph.md.metadata.json`

---

## 📑 2. Decisões Arquiteturais Registradas (ADRs)

Para entender o racional técnico por trás de cada escolha do projeto, consulte as ADRs em [`docs/adr/`](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/README.md):

1. **[ADR-001](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-001-orquestrador-langgraph-vs-n8n.md)**: Adoção do LangGraph + FastAPI sobre n8n.
2. **[ADR-002](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-002-gateway-whatsapp-evolution-baileys.md)**: Gateway WhatsApp via Evolution API *(Substituído pela ADR-008)*.
3. **[ADR-003](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-003-observabilidade-langfuse-self-hosted.md)**: Observabilidade e auditoria com Langfuse Self-Hosted.
4. **[ADR-004](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-004-persistencia-postgresql-database-isolada.md)**: PostgreSQL único gerenciando bases lógicas isoladas (`autolaw`, `langfuse`).
5. **[ADR-005](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-005-custo-zapsign-e-envio-via-evolution.md)**: Integração ZapSign *(Postergado)*.
6. **[ADR-006](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-006-pipeline-incremental-e-tdd.md)**: Metodologia TDD e Docker Compose progressivo.
7. **[ADR-007](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-007-gestao-de-transbordo-e-reativacao-do-agente.md)**: Silenciamento do bot em casos de transbordo e reativação via webhooks do CRM.
8. **[ADR-008](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-008-gateway-kommo-chats.md)**: Gateway WhatsApp via API de Conversas do Kommo CRM.
9. **[ADR-009](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-009-processamento-audio-gemini-stt.md)**: Transcrição de Áudio via Google Gemini Multimodal STT.
10. **[ADR-010](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-010-lista-permissao-ambiente-testes-allowed-chat-ids.md)**: Lista de Permissão em Ambientes de Teste (`ALLOWED_CHAT_IDS`).
11. **[ADR-011](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-011-gateway-whatsapp-meta-cloud-api.md)**: Gateway WhatsApp via Meta Cloud API e Kommo CRM.
12. **[ADR-012](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-012-tunel-estatico-ngrok.md)**: Túnel de Desenvolvimento Seguro com Domínio Estático Ngrok.
13. **[ADR-013](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-013-deduplicacao-idempotencia-fast-ack.md)**: Deduplicação de Mensagens (Idempotência) e Fast ACK para Webhooks.
14. **[ADR-014](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-014-memoria-langgraph-contexto-temporal.md)**: Persistência de Memória Conversacional e Injeção de Contexto Temporal.
15. **[ADR-015](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-015-migracao-llm-gemini-para-ollama.md)**: Migração da Camada Conversacional para ChatOllama (Cluster AtLab UFC).
16. **[ADR-016](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-016-automacao-gestao-webhooks-kommo.md)**: Automação e Auto-Cura de Webhooks na Kommo CRM.

