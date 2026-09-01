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

### [2. Plano de Arquitetura & Implementação — Kommo CRM Messaging & Áudio com IA](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/plano_migracao_kommo_audio.md)
* **Arquivo**: `docs/artifacts/plano_migracao_kommo_audio.md`
* **Metadados**: `docs/artifacts/plano_migracao_kommo_audio.md.metadata.json`
* **Conteúdo**:
  - Unificação da mensageria via Kommo CRM (Talks / Chats API), eliminando o gateway Evolution API.
  - Recepção e transcrição de áudios com Google Gemini Flash Multimodal STT.
  - Isolamento de ZapSign, ADVbox e RAG para fases futuras.

### [2. Plano Geral de Automação Comercial e Contratual](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/plano_automacao_livia_franca.md)
* **Arquivo**: `docs/artifacts/plano_automacao_livia_franca.md`
* **Metadados**: `docs/artifacts/plano_automacao_livia_franca.md.metadata.json`
* **Conteúdo**:
  - Arquitetura geral e especificações de prompts e integrações originais.

### [3. Pipeline de Desenvolvimento Incremental (TDD)](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/pipeline_desenvolvimento.md)
* **Arquivo**: `docs/artifacts/pipeline_desenvolvimento.md`
* **Metadados**: `docs/artifacts/pipeline_desenvolvimento.md.metadata.json`
* **Conteúdo**:
  - Roteiro incremental de desenvolvimento guiado por testes unitários e de integração.

### [4. Análise Comparativa: n8n vs. LangGraph](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/n8n_vs_langgraph.md)
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

