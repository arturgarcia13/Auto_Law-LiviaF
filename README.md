# 🏛️ Auto_Law — Dra. Lívia França

Automação comercial e contratual ponta a ponta para escritório de advocacia trabalhista, integrando qualificação de leads por IA no WhatsApp, coleta de dados, geração e assinatura eletrônica de contratos, e sincronização automática com CRM e sistema jurídico.

---

## 🧭 Acesso Rápido à Documentação

Toda a documentação técnica e decisões de projeto estão centralizadas na pasta [`docs/`](docs/):

* 🏛️ **[Plano Geral de Automação](docs/artifacts/plano_automacao_livia_franca.md)** — Arquitetura completa, fluxos, system prompts e mapeamento de APIs.
* 🚀 **[Pipeline de Desenvolvimento (TDD)](docs/artifacts/pipeline_desenvolvimento.md)** — Roteiro de entrega em 9 sprints com testes e Definition of Done.
* 📑 **[Architecture Decision Records (ADRs)](docs/adr/README.md)** — Decisões arquiteturais registradas (LangGraph, Baileys, Langfuse self-hosted, etc.).
* 📊 **[Estudo n8n vs. LangGraph](docs/artifacts/n8n_vs_langgraph.md)** — Comparativo técnico detalhado.
* 📚 **[Central de Documentação (docs/README.md)](docs/README.md)** — Índice navegável de todos os documentos.

---

## 🧱 Stack Tecnológica

| Componente | Tecnologia | Papel no Sistema |
|---|---|---|
| **API Server** | FastAPI (Python 3.12+) | Endpoints HTTP, webhooks assíncronos e routers |
| **Agente de IA** | LangGraph + Google Gemini | Máquina de estados conversacional e triagem trabalhista |
| **Persistência** | PostgreSQL 16 (`autolaw`) | Checkpointing de estados conversacionais (`AsyncPostgresSaver`) |
| **Buffer & Cache** | Redis 7 | Agrupamento de mensagens simultâneas em rajada |
| **Observabilidade** | Langfuse (Self-Hosted) | Tracing de nós, consumo de tokens, custos e tool calls |
| **WhatsApp Gateway** | Evolution API v2 (Baileys) | Recepção e envio de mensagens via QR Code |
| **CRM Comercial** | Kommo CRM API v4 | Gestão de leads, etapas do funil e transbordo humano |
| **Assinatura Digital** | ZapSign API | Emissão de contratos de honorários e procurações |
| **Sistema Jurídico** | ADVBOX API v1 | Cadastro automatizado de clientes e processos |

---

## 📂 Estrutura do Projeto

```
Auto_Law-LiviaF/
├── app/                        # Aplicação FastAPI
│   ├── main.py                 # Lifespan e registro central de routers
│   ├── routers/                # Endpoints (webhook, zapsign, kommo, health, admin)
│   ├── schemas/                # Schemas Pydantic de validação
│   └── services/               # Serviços de infraestrutura (buffer Redis, etc.)
│
├── agent/                      # Agente de IA com LangGraph
│   ├── graph.py                # Compilação do StateGraph
│   ├── state.py                # TypedDict LeadState
│   ├── nodes.py                # Nós de execução (triagem, coleta, transbordo)
│   ├── prompts.py              # System prompts especializados
│   └── tools.py                # Ferramentas acionáveis pelo agente
│
├── integrations/               # Clientes HTTP assíncronos para APIs externas
│   ├── evolution.py            # Gateway WhatsApp
│   ├── kommo.py                # Kommo CRM API v4
│   ├── zapsign.py              # ZapSign API REST
│   └── advbox.py               # ADVBOX API v1
│
├── scheduler/                  # Agendador de tarefas periódicas (APScheduler)
│   └── jobs.py                 # Lembretes de contratos pendentes
│
├── scripts/                    # Scripts utilitários e testes manuais de API
│   ├── api_check.py            # Teste manual de conexão com Kommo CRM
│   └── config.py               # Loader de variáveis de ambiente para scripts
│
├── tests/                      # Suíte de testes automatizados (Pytest)
│   ├── conftest.py             # Fixtures e mocks compartilhados
│   ├── test_health.py          # Testes de integridade da API
│   ├── test_webhooks.py        # Validação de schemas e webhooks
│   └── test_agent_nodes.py     # Testes unitários dos nós do agente
│
├── docs/                       # Documentação técnica completa
│   ├── artifacts/              # Planos e especificações originais
│   └── adr/                    # Architecture Decision Records
│
├── .env.example                # Template público de variáveis de ambiente
├── .env.test                   # Variáveis de ambiente para execução de testes
├── .gitignore                  # Regras estritas contra vazamento de secrets
├── pyproject.toml              # Configurações do Pytest, Mypy e Ruff
├── requirements.txt            # Dependências de produção
└── requirements-dev.txt        # Dependências de desenvolvimento e testes
```

---

## 🚀 Como Executar Localmente

### 1. Ativar o Ambiente Virtual
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar Dependências
```powershell
pip install -r requirements-dev.txt
```

### 3. Executar os Testes Automatizados (TDD)
```powershell
pytest
```

### 4. Executar Verificações de Qualidade (Linters e Tipagem)
```powershell
ruff check .
mypy app agent integrations scheduler tests
```

### 5. Iniciar a API em Modo de Desenvolvimento
```powershell
uvicorn app.main:app --reload --port 8000
```
Documentação interativa disponível em: `http://localhost:8000/docs`.
