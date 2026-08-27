# 📚 Documentação Técnica — Auto_Law-LiviaF

Bem-vindo à central de documentação da automação comercial e contratual do escritório de advocacia da Dra. Lívia França.

---

## 🗂️ Estrutura do Diretório `docs/`

```
docs/
├── README.md                          # Este índice geral
│
├── artifacts/                         # Artefatos técnicos centrais e seus metadados
│   ├── plano_automacao_livia_franca.md          # Arquitetura e especificação de ponta a ponta
│   ├── plano_automacao_livia_franca.md.metadata.json
│   ├── pipeline_desenvolvimento.md              # Roteiro incremental TDD em 9 sprints
│   ├── pipeline_desenvolvimento.md.metadata.json
│   ├── n8n_vs_langgraph.md                      # Análise comparativa técnica e benchmark
│   └── n8n_vs_langgraph.md.metadata.json
│
└── adr/                               # Architecture Decision Records (ADRs)
    ├── README.md                                # Índice e sumário executivo das ADRs
    ├── ADR-001-orquestrador-langgraph-vs-n8n.md
    ├── ADR-002-gateway-whatsapp-evolution-baileys.md
    ├── ADR-003-observabilidade-langfuse-self-hosted.md
    ├── ADR-004-persistencia-postgresql-database-isolada.md
    ├── ADR-005-custo-zapsign-e-envio-via-evolution.md
    ├── ADR-006-pipeline-incremental-e-tdd.md
    └── ADR-007-gestao-de-transbordo-e-reativacao-do-agente.md
```

---

## 🏛️ 1. Artefatos Centrais do Projeto

Os artefatos abaixo documentam todas as especificações de requisitos, payloads, diagramas de sequência e o planejamento de entrega:

### [1. Plano Geral de Automação Comercial e Contratual](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/plano_automacao_livia_franca.md)
* **Arquivo**: `docs/artifacts/plano_automacao_livia_franca.md`
* **Metadados**: `docs/artifacts/plano_automacao_livia_franca.md.metadata.json`
* **Conteúdo**:
  - Arquitetura geral e diagramas Mermaid.
  - Stack tecnológica completa (FastAPI, LangGraph, Gemini 1.5, PostgreSQL, Redis, Evolution API, Langfuse).
  - Mapeamento das etapas do funil no Kommo CRM (Novo Lead -> Qualificado -> Contrato Enviado -> Ganho / Transbordo).
  - Especificação detalhada dos 5 routers da API (`webhook`, `zapsign`, `kommo`, `health`, `admin`).
  - System prompts especializados para qualificação trabalhista e coleta de dados cadastrais.
  - Docker Compose para ambiente local (`docker-compose.local.yml`) e produção com proxy reverso Caddy (`docker-compose.yml`).

### [2. Pipeline de Desenvolvimento Incremental (TDD)](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/pipeline_desenvolvimento.md)
* **Arquivo**: `docs/artifacts/pipeline_desenvolvimento.md`
* **Metadados**: `docs/artifacts/pipeline_desenvolvimento.md.metadata.json`
* **Conteúdo**:
  - Estratégia de implementação dividida em 9 sprints estritamente sequenciais.
  - Princípio de subida gradual dos containers no Docker Compose conforme a cadeia de dependências.
  - Especificações completas de testes unitários e de integração (`pytest-asyncio`) para cada sprint.
  - Critérios objetivos de *Definition of Done (DoD)* por sprint.

### [3. Análise Comparativa: n8n vs. LangGraph](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/artifacts/n8n_vs_langgraph.md)
* **Arquivo**: `docs/artifacts/n8n_vs_langgraph.md`
* **Metadados**: `docs/artifacts/n8n_vs_langgraph.md.metadata.json`
* **Conteúdo**:
  - Estudo de 10 critérios técnicos comparando n8n puro, LangGraph + FastAPI e modelo híbrido.
  - Análise de trade-offs de manutenção, observabilidade no Langfuse, persistência de estado e controle determinístico.

---

## 📑 2. Decisões Arquiteturais Registradas (ADRs)

Para entender o racional técnico por trás de cada escolha do projeto, consulte as ADRs em [`docs/adr/`](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/README.md):

1. **[ADR-001](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-001-orquestrador-langgraph-vs-n8n.md)**: Adoção do LangGraph + FastAPI sobre n8n.
2. **[ADR-002](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-002-gateway-whatsapp-evolution-baileys.md)**: Gateway WhatsApp via Evolution API no modo Baileys (QR Code).
3. **[ADR-003](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-003-observabilidade-langfuse-self-hosted.md)**: Observabilidade e auditoria com Langfuse Self-Hosted.
4. **[ADR-004](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-004-persistencia-postgresql-database-isolada.md)**: PostgreSQL único gerenciando bases lógicas isoladas (`autolaw`, `langfuse`, `evolution_db`).
5. **[ADR-005](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-005-custo-zapsign-e-envio-via-evolution.md)**: Disparo do link ZapSign via WhatsApp próprio para eliminar tarifa de R$ 0,50/envio.
6. **[ADR-006](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-006-pipeline-incremental-e-tdd.md)**: Desenvolvimento orientado a testes (TDD) e Docker Compose progressivo.
7. **[ADR-007](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-007-gestao-de-transbordo-e-reativacao-do-agente.md)**: Silenciamento do bot em casos de transbordo e reativação via webhooks do CRM.
