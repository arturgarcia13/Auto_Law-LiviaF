# 🏛️ Auto_Law — Dra. Lívia França

Automação comercial e jurídica ponta a ponta para escritório de advocacia trabalhista, integrando qualificação de leads por IA no WhatsApp via Meta Cloud API, coleta estruturada de 17 campos trabalhistas, e sincronização automática com o Kommo CRM (funil, notas com `wamid` e tarefas para envio de contratos).

---

## 🧭 Acesso Rápido à Documentação

Toda a documentação técnica e decisões de projeto estão centralizadas na pasta [`docs/`](docs/):

* 🏛️ **[Plano Geral de Automação](docs/artifacts/plano_automacao_livia_franca.md)** — Arquitetura completa, fluxos, system prompts e mapeamento de APIs.
* 📑 **[Architecture Decision Records (ADRs)](docs/adr/README.md)** — Decisões arquiteturais registradas ([ADR-011: Meta Cloud API](docs/adr/ADR-011-gateway-whatsapp-meta-cloud-api.md), LangGraph, etc.).
* 📚 **[Central de Documentação (docs/README.md)](docs/README.md)** — Índice navegável de todos os documentos.

---

## 🧱 Stack Tecnológica

| Componente | Tecnologia | Papel no Sistema |
|---|---|---|
| **API Server** | FastAPI (Python 3.12+) | Endpoints HTTP (`/kommo/webhook`, `/send`, `/health`), webhooks e routers |
| **Agente de IA** | LangGraph + Google Gemini Flash | Máquina de estados conversacional e qualificação de 17 campos da ficha |
| **WhatsApp Gateway** | Meta WhatsApp Cloud API (Graph API) | Recepção e envio oficial de mensagens de texto e templates HSM |
| **CRM Comercial** | Kommo CRM API v4 | Gestão de leads, etapas do funil, tarefas urgentes e timeline de notas |
| **Transcrição STT** | Google Gemini Multimodal Flash | Transcrição assíncrona nativa de mensagens de voz/áudio |
| **Buffer & Cache** | Redis 7 | Agrupamento de mensagens simultâneas em rajada (debounce) |
| **Persistência** | PostgreSQL 16 (`autolaw`) | Checkpointing de estados conversacionais (`AsyncPostgresSaver` / Memory) |
| **Observabilidade** | Langfuse (Self-Hosted) | Tracing de nós, consumo de tokens, custos e tool calls |

---

## 📂 Estrutura do Projeto

```
Auto_Law-LiviaF/
├── app/                        # Aplicação FastAPI
│   ├── main.py                 # Lifespan e registro central de routers
│   ├── routers/                # Endpoints (kommo webhook, send, health, admin)
│   ├── schemas/                # Schemas Pydantic de validação (kommo, meta)
│   └── services/               # Serviços de infraestrutura (buffer Redis, audio Gemini STT)
│
├── agent/                      # Agente de IA com LangGraph
│   ├── graph.py                # Compilação do StateGraph (5 etapas do funil)
│   ├── state.py                # TypedDict LeadState e Ficha Trabalhista (17 campos)
│   ├── nodes.py                # Nós de execução (entrada, viabilidade, qualificado, oferta, envio)
│   ├── prompts.py              # System prompts especializados da Dra. Lívia França
│   └── tools.py                # Ferramentas acionáveis pelo agente
│
├── integrations/               # Clientes HTTP assíncronos para APIs externas
│   ├── meta.py                 # Meta WhatsApp Cloud API (Graph API)
│   └── kommo.py                # Kommo CRM API v4 (leads, notas com wamid, tarefas, funil)
│
├── scheduler/                  # Agendador de tarefas periódicas (APScheduler)
│   └── jobs.py                 # Rotinas em background
│
├── tests/                      # Suíte de testes automatizados (Pytest)
│   ├── conftest.py             # Fixtures compartilhadas
│   ├── test_health.py          # Testes de integridade da API e subsistemas
│   ├── test_meta.py            # Testes do cliente Meta Cloud API
│   ├── test_kommo.py           # Testes do cliente Kommo CRM v4
│   ├── test_webhooks.py        # Validação de webhooks, autenticação e /send
│   └── test_agent_nodes.py     # Testes unitários dos nós do agente LangGraph
│
├── docs/                       # Documentação técnica completa
│   ├── artifacts/              # Planos e especificações
│   └── adr/                    # Architecture Decision Records
│
├── .env.example                # Template público de variáveis de ambiente
├── .env.test                   # Variáveis de ambiente para execução de testes
├── pyproject.toml              # Configurações do Pytest, Mypy e Ruff
└── requirements.txt            # Dependências de produção
```

---

## 🚀 Como Executar Localmente

### 1. Instalar Dependências
```powershell
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Executar os Testes Automatizados (TDD)
```powershell
pytest
```

### 3. Executar Verificações de Qualidade (Linters e Tipagem)
```powershell
ruff check app agent integrations tests
mypy app agent integrations scheduler tests
```

### 4. Iniciar a API com Túnel Ngrok (Recomendado para Webhooks Kommo)
```powershell
.\start_tunnel.ps1
```
O script iniciará o servidor Uvicorn, estabelecerá o túnel público no Ngrok (com suporte opcional a domínio estático `NGROK_DOMAIN` no `.env`) e imprimirá na tela as URLs exatas com o token de segurança para você colar na Kommo.

### 5. Iniciar Apenas a API Localmente
```powershell
uvicorn app.main:app --reload --port 8000
```
Documentação interativa disponível em: `http://localhost:8000/docs`.

