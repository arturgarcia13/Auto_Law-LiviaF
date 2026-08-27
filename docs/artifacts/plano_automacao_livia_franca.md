# 🏛️ Automação Comercial e Contratual — Escritório Dra. Lívia França
## Arquitetura Definitiva: LangGraph + FastAPI

> [!NOTE]
> Plano revisado em 27/08/2026. Arquitetura escolhida: **Opção B — LangGraph + FastAPI puro Python**.
> Decisão baseada em: perfil técnico do desenvolvedor, necessidade de observabilidade com Langfuse e controle fino sobre o estado conversacional do agente.

---

## Por que Opção B e não C (Híbrido)?

A Opção C (LangGraph + n8n) adiciona uma **camada extra desnecessária**: o n8n seria apenas um proxy entre a Evolution API e a FastAPI, introduzindo latência e mais um serviço para manter — sem nenhum benefício real para um desenvolvedor Python.

Com a Opção B:
- **Langfuse rastreia tudo nativamente** via `CallbackHandler` — cada nó do grafo, cada chamada ao Gemini, cada tool call vira um span no dashboard. Isso **não funciona** dentro do AI Agent node do n8n.
- **Sem latência extra**: WhatsApp → Evolution API → FastAPI → LangGraph (sem n8n no meio)
- **Menos infra**: Docker Compose mais simples, sem pagar/manter o n8n
- **APScheduler** resolve os cron jobs (lembretes) em Python puro
- Os módulos `kommo/`, `zapsign/`, `advbox/` viram **LangGraph Tools** — exatamente o que você já começou a escrever

---

## 🧱 Arquitetura Definitiva

```mermaid
flowchart TD
    A["Lead clica no anúncio\nFacebook/Instagram/Google"] --> B[WhatsApp]
    B --> C["Evolution API\nGateway WhatsApp\n:8080"]
    C -->|"MESSAGES_UPSERT\nwebhook POST"| D["FastAPI\n/webhook/message\n:8000"]
    D -->|"BackgroundTask\nasync"| E["LangGraph Agent\nGrafo de Estados"]
    E --> F["Google Gemini\nvia ChatGoogleGenerativeAI\ntool_calling"]
    F --> E
    E --> G{Estado atual\ndo lead?}
    G -->|"triagem"| H["Nó: qualificar_lead\nTools: Kommo API"]
    G -->|"coleta"| I["Nó: coletar_dados\nValidação Pydantic"]
    G -->|"contrato"| J["Nó: gerar_contrato\nTool: ZapSign API"]
    G -->|"transbordo"| K["Nó: transbordo_humano\nTool: Kommo Task API"]
    G -->|"assinado"| L["Nó: pos_assinatura\nTools: Kommo + ADVBOX"]
    E -->|"Evolution API\nsendText"| M[WhatsApp\nresposta ao lead]
    E --> N[("PostgreSQL\nAsyncPostgresSaver\ncheckpoints por thread_id")]
    E --> O["Langfuse\nCallbackHandler\nTracing completo"]
    P["APScheduler\nCron: lembretes contrato"] --> E

    style A fill:#4CAF50,color:#fff
    style K fill:#FF9800,color:#fff
    style O fill:#7B1FA2,color:#fff
    style N fill:#1565C0,color:#fff
    style F fill:#00897B,color:#fff
```

---

## 🔧 Stack Tecnológica Definitiva

| Componente | Ferramenta | Versão/Detalhe |
|---|---|---|
| **API Server** | **FastAPI** | Async, lifespan context manager |
| **Agente de IA** | **LangGraph** | `StateGraph` + `AsyncPostgresSaver` |
| **LLM** | **Google Gemini** | `ChatGoogleGenerativeAI` via `langchain-google-genai` |
| **Memória/Estado** | **PostgreSQL** | `AsyncPostgresSaver` (checkpoints por `thread_id`) |
| **Buffer WhatsApp** | **Redis** | Agrupar msgs simultâneas (3-5s) |
| **Observabilidade** | **Langfuse** | `CallbackHandler` + `@observe` decorator |
| **Cron Jobs** | **APScheduler** | Lembretes de contrato + cleanup de checkpoints |
| **WhatsApp Gateway** | **Evolution API v2** | **Modo Baileys** (QR Code) — sem API oficial Meta, sem burocracia |
| **CRM** | **Kommo CRM API v4** | `httpx.AsyncClient` |
| **Assinatura** | **ZapSign API** | `httpx.AsyncClient` |
| **Sistema Jurídico** | **ADVBOX API v1** | `httpx.AsyncClient` |
| **Containerização** | **Docker Compose** | FastAPI + Evolution + PostgreSQL + Redis + Caddy |
| **Validação** | **Pydantic v2** | Schemas de webhook e dados do contrato |
| **Testes** | **pytest-asyncio** | Testes unitários por nó do grafo |

---

## ⚠️ Itens para Revisão

> [!NOTE]
> **WhatsApp Gateway: Evolution API — Modo Baileys (QR Code) ✅ Confirmado**
> Sem necessidade de API oficial Meta. A conexão ocorre via QR Code escaneado pelo celular — idêntico ao WhatsApp Web. Modo ideal para desenvolvimento, staging e produção de baixo-médio volume. Caminho de migração para modo Cloud API (Meta oficial) disponível quando necessário no futuro, sem mudança de código.

> [!WARNING]
> **Custo ZapSign — WhatsApp automático**: `send_automatic_whatsapp: true` custa R$ 0,50/envio. **Recomendação**: usar `false` e enviar o `sign_url` retornado pela API via Evolution API — gratuito e mais rápido.

> [!IMPORTANT]
> **Plano Kommo**: Webhooks globais exigem plano **Advanced ou superior**. Verificar plano atual.

> [!NOTE]
> **Langfuse: Self-hosted ✅ Confirmado**
> Langfuse rodará na mesma VPS via Docker Compose. Requer **~1GB RAM adicional** e usa um banco **PostgreSQL próprio** (separado do banco da aplicação para evitar conflito de schemas). URL interna: `http://langfuse:3000`. Acesso externo via Caddy em `https://langfuse.seudominio.com`.

---

## ❓ Perguntas em Aberto

> [!IMPORTANT]
> 1. **ZapSign template_id**: Encontrado na URL do modelo no painel ZapSign — qual é?
> 2. **Funil Kommo**: Qual o nome e IDs das etapas? (Novo Lead, Qualificado, Contrato Enviado, Ganho)
> 3. **ADVBOX**: Precisamos consultar `GET /settings` para mapear `type_lawsuit_id` e `stage_id` trabalhistas — tem acesso à API no plano atual?
> 4. **Transbordo**: A IA deve transferir automaticamente em casos de "acidente grave" e "assédio sexual", ou a Dra. Lívia quer definir as regras ela mesma?

---

## 🔄 Mapeamento de Etapas no Funil Kommo

O bot move automaticamente os leads entre as etapas do funil conforme o progresso da conversa. Cada transição é acionada por um nó do grafo LangGraph:

| Evento / Nó | Etapa no Kommo | Variável `.env` |
|---|---|---|
| Primeira mensagem recebida (novo lead) | → **Novo Lead** | `KOMMO_STATUS_NOVO` |
| Lead qualificado na triagem → inicia coleta de dados | → **Qualificado** | `KOMMO_STATUS_QUALIFICADO` |
| Contrato gerado e link enviado via ZapSign | → **Contrato Enviado** | `KOMMO_STATUS_CONTRATO_ENVIADO` |
| Caso complexo: bot envia para atendimento humano | → **Transbordo** | `KOMMO_STATUS_TRANSBORDO` |
| Contrato assinado + ADVBOX cadastrado | → **Ganho** | `KOMMO_STATUS_GANHO` |

```mermaid
flowchart LR
    A[Novo Lead] -->|triagem ok| B[Qualificado]
    B -->|dados coletados| C[Contrato Enviado]
    C -->|doc_signed webhook| D[Ganho ✅]
    A -->|caso complexo| E[Transbordo ⚠️]
    B -->|caso complexo| E
    E -->|humano resolve| D
```

> [!NOTE]
> Todas as transições também registram uma **nota automática no Kommo** com o contexto (dados coletados, link do contrato, token ZapSign, etc.), mantendo o histórico do lead visível para a equipe.

> [!IMPORTANT]
> Para que as transições funcionem, é necessário mapear os IDs reais das etapas do funil da conta da Dra. Lívia no Kommo e preencher o `.env`. Esses IDs são obtidos via `GET /api/v4/leads/pipelines` ou diretamente na URL do painel Kommo ao clicar na etapa.

---

## 📋 Plano de Implementação

### FASE 0 — Evolution API: Configuração Modo Baileys (QR Code)

> [!CAUTION]
> **ToS do WhatsApp**: O modo Baileys utiliza o protocolo não oficial do WhatsApp Web (biblioteca open-source). A Meta proíbe automação fora da API oficial nos seus termos de serviço. Riscos práticos para uso com volume moderado (~50-200 conversas/dia): **baixo** se evitar disparos em massa. Risco cresce com volume alto ou comportamento de spam. Para produção de grande escala no futuro, migrar para API oficial.

#### Como funciona o modo Baileys

A Evolution API em modo Baileys **emula o protocolo do WhatsApp Web** via WebSocket. Você:
1. Cria uma instância via API (`POST /instance/create`)
2. Solicita o QR Code (`GET /instance/connect/{nome}`)
3. Escaneia com o celular do escritório (igual ao WhatsApp Web)
4. A sessão fica persistida no **PostgreSQL** + **Redis** — não cai ao reiniciar o container

A grande vantagem sobre o WhatsApp Web puro: a sessão é **mantida no servidor 24/7** sem depender de um navegador aberto.

#### [NEW] Seção Evolution API no `docker-compose.yml`

```yaml
evolution-api:
  image: evoapicloud/evolution-api:v2.2.3   # ⚠️ Fixar versão — não usar latest
  container_name: evolution_api
  restart: unless-stopped
  ports:
    - "8080:8080"
  environment:
    # Servidor
    SERVER_URL: https://whatsapp.seudominio.com
    AUTHENTICATION_API_KEY: ${EVOLUTION_API_KEY}

    # Banco de dados (persistência das instâncias/sessões)
    DATABASE_PROVIDER: postgresql
    DATABASE_CONNECTION_URI: postgresql://user:password@postgres:5432/evolution_db

    # Redis (estado das conexões WebSocket)
    CACHE_REDIS_ENABLED: "true"
    CACHE_REDIS_URI: redis://redis:6379/6

    # QR Code
    QRCODE_LIMIT: "30"             # Máximo de tentativas antes de expirar
    CONFIG_SESSION_PHONE_VERSION: "2.3000.1023204200"  # Versão do WhatsApp Web atual

    # Logs
    LOG_LEVEL: ERROR               # Trocar para DEBUG se precisar depurar
    LOG_BAILEYS: error

  volumes:
    - evolution_instances:/evolution/instances   # Backup das sessões
  depends_on:
    - postgres
    - redis
  networks:
    - autolaw-net
```

#### Setup inicial: criar instância e escanear QR Code

```bash
# 1. Criar instância Baileys (executar UMA vez)
curl -X POST https://whatsapp.seudominio.com/instance/create \
  -H "apikey: SUA_EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "livia-franca",
    "qrcode": true,
    "integration": "WHATSAPP-BAILEYS"
  }'

# 2. Obter QR Code (imagem base64 ou URL)
curl -X GET https://whatsapp.seudominio.com/instance/connect/livia-franca \
  -H "apikey: SUA_EVOLUTION_API_KEY"
# → Retorna {"base64": "data:image/png;base64,..."} — abrir no browser e escanear

# 3. Verificar status da conexão
curl -X GET https://whatsapp.seudominio.com/instance/connectionState/livia-franca \
  -H "apikey: SUA_EVOLUTION_API_KEY"
# → {"instance": {"state": "open"}}  ← conectado!

# 4. Registrar webhook da instância → aponta para a FastAPI
curl -X POST https://whatsapp.seudominio.com/webhook/set/livia-franca \
  -H "apikey: SUA_EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.seudominio.com/webhook/message",
    "webhook_by_events": false,
    "webhook_base64": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

#### Estrutura do payload recebido (`MESSAGES_UPSERT`)

```json
{
  "event": "messages.upsert",
  "instance": "livia-franca",
  "data": {
    "key": {
      "remoteJid": "5511999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "MSG_ID"
    },
    "pushName": "João Silva",
    "message": {
      "conversation": "Olá, vi o anúncio sobre direitos trabalhistas"
    },
    "messageType": "conversation",
    "messageTimestamp": 1787834888
  }
}
```

#### [NEW] `app/schemas/evolution.py` (Pydantic)

```python
from pydantic import BaseModel
from typing import Optional


class MessageKey(BaseModel):
    remoteJid: str
    fromMe: bool
    id: str


class MessageContent(BaseModel):
    conversation: Optional[str] = None
    audioMessage: Optional[dict] = None  # para transcrição de áudio futura
    imageMessage: Optional[dict] = None


class EvolutionData(BaseModel):
    key: MessageKey
    pushName: Optional[str] = None
    message: MessageContent
    messageType: str
    messageTimestamp: int


class EvolutionWebhookPayload(BaseModel):
    event: str
    instance: str
    data: EvolutionData

    @property
    def telefone(self) -> str:
        return self.data.key.remoteJid.replace("@s.whatsapp.net", "")

    @property
    def texto(self) -> str | None:
        return self.data.message.conversation

    @property
    def e_minha_mensagem(self) -> bool:
        return self.data.key.fromMe
```

#### [NEW] `integrations/evolution.py` (envio de mensagens)

```python
import httpx
import os

EVOLUTION_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "livia-franca")

HEADERS = {
    "apikey": EVOLUTION_KEY,
    "Content-Type": "application/json",
}


async def enviar_texto(telefone: str, texto: str) -> dict:
    """Envia mensagem de texto via Evolution API (Baileys)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}",
            headers=HEADERS,
            json={
                "number": telefone,
                "text": texto,
                "delay": 1500,  # simula digitação natural (ms)
            },
        )
        resp.raise_for_status()
        return resp.json()


async def verificar_status() -> str:
    """Retorna o estado da conexão: 'open', 'close', 'connecting'."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{EVOLUTION_URL}/instance/connectionState/{EVOLUTION_INSTANCE}",
            headers=HEADERS,
        )
        data = resp.json()
        return data.get("instance", {}).get("state", "unknown")
```

#### Dica: endpoint de status para monitoramento

Adicionar no FastAPI um endpoint de health check que verifica se a sessão Baileys está ativa:

```python
# app/routers/health.py
@router.get("/health")
async def health():
    estado = await evolution.verificar_status()
    return {
        "api": "ok",
        "whatsapp": estado,  # "open" = conectado, "close" = desconectado
    }
```

Se `state != "open"`, o sistema dispara um alerta (log de erro + e-mail/Langfuse alert) e aguarda reconexão.

---

### FASE 1 — Estrutura do Projeto e Dependências


#### [NEW] Estrutura de diretórios completa

```
Auto_Law-LiviaF/
├── .env                        # Secrets (nunca commitar)
├── .env.example                # Template sem valores reais
├── config.py                   # Carrega env vars (já existe)
├── api_check.py                # Testes manuais de API (já existe)
├── requirements.txt            # Dependências Python
├── Dockerfile                  # Container da FastAPI
├── docker-compose.yml          # Stack completa
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + lifespan
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhook.py          # POST /webhook/message     ← Evolution API (msg recebida)
│   │   ├── zapsign.py          # POST /webhook/zapsign     ← ZapSign (contrato assinado)
│   │   ├── kommo.py            # POST /webhook/kommo       ← Kommo (eventos do CRM)
│   │   ├── health.py           # GET  /health              ← Docker/monitoramento
│   │   └── admin.py            # GET/POST /admin/...       ← Operações manuais
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── evolution.py        # Pydantic: payload do webhook WhatsApp
│   │   ├── lead.py             # Pydantic: dados de triagem e contrato
│   │   └── zapsign.py          # Pydantic: evento doc_signed
│   └── services/
│       ├── __init__.py
│       └── buffer.py           # Redis buffer (agrupar msgs simultâneas)
│
├── agent/
│   ├── __init__.py
│   ├── graph.py                # Definição do StateGraph LangGraph
│   ├── state.py                # LeadState TypedDict
│   ├── nodes.py                # Funções de cada nó do grafo
│   ├── prompts.py              # System prompts por fase
│   └── tools.py                # @tool decorators (Kommo, ZapSign, ADVBOX)
│
├── integrations/
│   ├── __init__.py
│   ├── kommo.py                # AsyncClient Kommo API v4
│   ├── zapsign.py              # AsyncClient ZapSign API
│   ├── advbox.py               # AsyncClient ADVBOX API
│   └── evolution.py            # AsyncClient Evolution API (envio)
│
├── scheduler/
│   ├── __init__.py
│   └── jobs.py                 # APScheduler: lembretes + cleanup
│
└── tests/
    ├── conftest.py
    ├── test_agent_nodes.py     # Testa cada nó do grafo isoladamente
    ├── test_integrations.py    # Testa chamadas às APIs externas
    └── test_webhooks.py        # Testa endpoints FastAPI
```

#### [NEW] `requirements.txt`

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-dotenv>=1.0.0

# LangGraph + LangChain
langgraph>=0.2.0
langchain>=0.3.0
langchain-google-genai>=2.0.0
langchain-core>=0.3.0
langgraph-checkpoint-postgres>=2.0.0
psycopg[pool]>=3.2.0

# Observabilidade
langfuse>=2.36.0

# Redis (buffer de mensagens)
redis[asyncio]>=5.0.0

# Scheduler (cron jobs)
apscheduler>=3.10.0

# Testes
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx  # já listado acima (usado no TestClient)
```

---

### FASE 2 — Estado do Agente (LangGraph Core)

#### [NEW] `agent/state.py`

```python
from typing import Literal, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

FaseLead = Literal[
    "triagem",  # IA qualificando o caso
    "coleta",  # IA coletando dados para o contrato
    "aguardando_assinatura",  # Contrato enviado, esperando ZapSign webhook
    "transbordo",  # Transferido para equipe humana
    "concluido",  # Contrato assinado + ADVBOX cadastrado
]


class LeadState(TypedDict):
    # Histórico de mensagens (LangGraph acumula automaticamente)
    messages: Annotated[list[BaseMessage], add_messages]

    # Identificadores
    telefone: str  # Chave de sessão (thread_id)
    lead_id: str | None  # ID no Kommo CRM
    contato_id: str | None  # ID do contato no Kommo

    # Controle de estado
    fase: FaseLead
    humano_ativo: bool  # Quando True, bot para de responder

    # Dados da triagem trabalhista
    dados_triagem: dict  # {tempo_servico, tem_ctps, salario, motivo, provas}

    # Dados para o contrato
    dados_contrato: dict  # {nome, cpf, rg, data_nasc, estado_civil, profissao, endereco, email}

    # ZapSign
    zapsign_doc_token: str | None
    zapsign_sign_url: str | None

    # ADVBOX
    advbox_customer_id: str | None
    advbox_lawsuit_id: str | None

    # Motivo do transbordo (para nota no Kommo)
    motivo_transbordo: str | None
```

#### [NEW] `agent/graph.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from agent.state import LeadState
from agent.nodes import (
    buffer_mensagens,
    triagem_node,
    coleta_dados_node,
    gerar_contrato_node,
    transbordo_node,
    pos_assinatura_node,
)


def roteador(state: LeadState) -> str:
    """Decide qual nó executar baseado na fase atual do lead."""
    if state.get("humano_ativo"):
        return END  # Bot silenciado, humano está atendendo
    return state.get("fase", "triagem")


def build_graph(checkpointer: AsyncPostgresSaver) -> StateGraph:
    graph = StateGraph(LeadState)

    # Nós
    graph.add_node("triagem", triagem_node)
    graph.add_node("coleta", coleta_dados_node)
    graph.add_node("gerar_contrato", gerar_contrato_node)
    graph.add_node("transbordo", transbordo_node)
    graph.add_node("pos_assinatura", pos_assinatura_node)

    # Ponto de entrada
    graph.set_entry_point("triagem")

    # Roteamento condicional após cada nó
    graph.add_conditional_edges(
        "triagem",
        roteador,
        {
            "triagem": "triagem",
            "coleta": "coleta",
            "transbordo": "transbordo",
            END: END,
        },
    )
    graph.add_conditional_edges(
        "coleta",
        roteador,
        {
            "coleta": "coleta",
            "gerar_contrato": "gerar_contrato",
            "transbordo": "transbordo",
            END: END,
        },
    )
    graph.add_edge("gerar_contrato", END)  # Aguarda webhook ZapSign
    graph.add_edge("transbordo", END)
    graph.add_edge("pos_assinatura", END)

    return graph.compile(checkpointer=checkpointer)
```

---

### FASE 3 — FastAPI + Langfuse

#### [NEW] `app/main.py`

```python
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from agent.graph import build_graph
from app.routers import webhook, zapsign as zapsign_router
from scheduler.jobs import registrar_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Conexão com PostgreSQL e compilação do grafo
    async with AsyncConnectionPool(conninfo=os.environ["DATABASE_URL"]) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()  # Cria tabelas se não existirem
        app.state.graph = build_graph(checkpointer)

        # Cron jobs (lembretes de contrato)
        scheduler = AsyncIOScheduler()
        registrar_jobs(scheduler, app.state.graph)
        scheduler.start()

        yield

        scheduler.shutdown()


app = FastAPI(title="Auto Law — Dra. Lívia França", lifespan=lifespan)
app.include_router(webhook.router)
app.include_router(zapsign_router.router)
```

#### [NEW] `app/routers/webhook.py`

```python
from fastapi import APIRouter, BackgroundTasks, Request
from app.schemas.evolution import EvolutionWebhookPayload
from app.services.buffer import processar_com_buffer
from langfuse.callback import CallbackHandler

router = APIRouter()


@router.post("/webhook/message")
async def receber_mensagem(
    payload: EvolutionWebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """
    Recebe mensagens da Evolution API.
    Retorna 200 imediatamente e processa em background.
    """
    background_tasks.add_task(
        processar_mensagem,
        payload=payload,
        graph=request.app.state.graph,
    )
    return {"status": "ok"}


async def processar_mensagem(payload, graph):
    telefone = payload.data.key.remoteJid.replace("@s.whatsapp.net", "")
    mensagem = payload.data.message.conversation

    # Langfuse: trace por conversa
    langfuse_handler = CallbackHandler(
        user_id=telefone,
        session_id=f"lead-{telefone}",
        tags=["auto-law", "whatsapp"],
    )

    config = {
        "configurable": {"thread_id": telefone},
        "callbacks": [langfuse_handler],
    }

    await graph.ainvoke(
        {"messages": [("user", mensagem)], "telefone": telefone},
        config=config,
    )
```

---

### FASE 4 — Integração Langfuse (Observabilidade Completa)

#### [NEW] `agent/nodes.py` (trecho com @observe)

```python
from langfuse import observe
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from agent.state import LeadState

gemini = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    google_api_key=os.getenv("GEMINI_API_KEY"),
)


@observe(name="triagem_lead")
async def triagem_node(state: LeadState) -> LeadState:
    """
    Nó de triagem: IA qualifica o lead trabalhista.
    Langfuse rastreia: tokens consumidos, latência, tool calls.
    """
    from agent.prompts import SYSTEM_PROMPT_TRIAGEM
    from agent.tools import atualizar_kommo, iniciar_coleta

    model_with_tools = gemini.bind_tools([atualizar_kommo, iniciar_coleta])

    response = await model_with_tools.ainvoke(
        [
            ("system", SYSTEM_PROMPT_TRIAGEM),
            *state["messages"],
        ]
    )

    # Verifica se a IA chamou alguma tool
    nova_fase = state["fase"]
    if response.tool_calls:
        for tc in response.tool_calls:
            if tc["name"] == "iniciar_coleta":
                nova_fase = "coleta"
            elif tc["name"] == "acionar_transbordo":
                nova_fase = "transbordo"

    return {
        "messages": [response],
        "fase": nova_fase,
    }
```

#### Langfuse Dashboard — O que você verá

Cada conversa aparece como um **trace** no Langfuse com:
- 🟢 Spans por nó do grafo (`triagem_lead`, `coleta_dados`, etc.)
- 🔵 Spans de cada chamada ao Gemini (tokens de entrada/saída, custo)
- 🟡 Spans de cada tool call (chamadas ao Kommo, ZapSign, ADVBOX)
- ⏱️ Latência de ponta a ponta por mensagem
- 💬 Input/output de cada etapa
- 🏷️ Tags por fase, por número de telefone, por etapa do funil

```python
# .env — Langfuse config
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com   # ou http://langfuse:3000 se self-hosted
```

---

### FASE 5 — Nó de Triagem (Agente IA)

#### [NEW] `agent/prompts.py`

```python
SYSTEM_PROMPT_TRIAGEM = """
Você é a assistente virtual do escritório de advocacia trabalhista da Dra. Lívia França.
Seu objetivo é qualificar leads que chegaram de anúncios sobre direitos trabalhistas.

## REGRAS DE TRIAGEM
Colete SEQUENCIALMENTE (uma pergunta por vez) as seguintes informações:
1. Confirme se a pessoa foi demitida ou tem outra situação trabalhista
2. Tempo de serviço na empresa (em anos/meses)
3. Tinha carteira assinada (CTPS)?
4. Qual o salário mensal aproximado?
5. Motivo da ação (demissão sem justa causa, horas extras, assédio moral, acidente de trabalho, etc.)
6. Possui alguma prova? (contracheques, mensagens, testemunhas, fotos)

## CRITÉRIOS DE QUALIFICAÇÃO
✅ QUALIFICADO → chame a tool `iniciar_coleta` quando:
   - Tem CTPS + tempo de serviço > 3 meses + valor da causa estimável

❌ NÃO QUALIFICADO → informe gentilmente quando:
   - Nunca teve registro formal em carteira
   - Caso muito antigo (> 2 anos sem ação judicial)

⚠️ TRANSBORDO → chame a tool `acionar_transbordo` imediatamente quando:
   - Acidente de trabalho grave ou morte
   - Assédio sexual
   - Processo judicial já em andamento
   - Lead pede explicitamente para falar com humano
   - Situação que você não sabe como classificar

## REGRAS DE COMPORTAMENTO
- Use linguagem simples, empática, nunca jargão jurídico
- Nunca mencione valores de indenização ou honorários
- Faça UMA pergunta por mensagem
- Se receber áudio: "Recebi seu áudio! Vou processá-lo em instantes."
"""

SYSTEM_PROMPT_COLETA = """
Você coletou as informações do caso. Agora precisa obter os dados pessoais para
preparar o contrato de honorários da Dra. Lívia França.

Colete nessa ordem exata, um dado por mensagem, confirmando cada um:

1. Nome completo (como no documento oficial)
2. CPF (formato: 000.000.000-00 — valide e confirme)
3. RG e órgão emissor (ex: 12.345.678-9 SSP/SP)
4. Data de nascimento (DD/MM/AAAA)
5. Estado civil (solteiro, casado, divorciado, viúvo)
6. Profissão (cargo que ocupava na empresa)
7. Endereço completo (Rua, nº, complemento, bairro, cidade, UF, CEP)
8. E-mail (para receber o contrato)

Quando todos os dados forem confirmados, diga:
"Perfeito! Estou preparando seu contrato agora. Em alguns instantes você receberá 
o link de assinatura por aqui mesmo. 📄✍️"

Então chame a tool `gerar_contrato_zapsign`.
"""
```

---

### FASE 6 — Integração ZapSign

#### [NEW] `integrations/zapsign.py`

```python
import httpx
import os
from langfuse import observe

BASE_URL = "https://api.zapsign.com.br/api/v1"


@observe(name="zapsign_criar_documento")
async def criar_documento(dados: dict) -> dict:
    """Cria documento via template ZapSign e retorna sign_url."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/models/create-doc/",
            headers={"Authorization": f"Bearer {os.getenv('ZAPSIGN_TOKEN')}"},
            json={
                "template_id": os.getenv("ZAPSIGN_TEMPLATE_ID"),
                "signer_name": dados["nome"],
                "signer_email": dados["email"],
                "signer_phone_country": "55",
                "signer_phone_number": dados["telefone"],
                "send_automatic_whatsapp": False,  # enviamos pelo Evolution (grátis)
                "data": [
                    {"de": "{{NOME}}", "para": dados["nome"]},
                    {"de": "{{CPF}}", "para": dados["cpf"]},
                    {"de": "{{RG}}", "para": dados["rg"]},
                    {"de": "{{ENDERECO}}", "para": dados["endereco"]},
                    {"de": "{{PROFISSAO}}", "para": dados["profissao"]},
                    {"de": "{{EMPRESA_RECLAMADA}}", "para": dados["empresa"]},
                    {"de": "{{DATA_HOJE}}", "para": dados["data_hoje"]},
                ],
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "doc_token": data["token"],
            "sign_url": data["open_id"],  # link de assinatura
        }
```

#### [NEW] `app/routers/zapsign.py`

```python
from fastapi import APIRouter, Request
from app.schemas.zapsign import ZapSignWebhookPayload

router = APIRouter()


@router.post("/webhook/zapsign")
async def zapsign_assinado(payload: ZapSignWebhookPayload, request: Request):
    """
    Recebido quando o contrato é assinado.
    Dispara: mover lead no Kommo + criar cliente+processo no ADVBOX.
    """
    if payload.event == "doc_signed":
        from agent.nodes import pos_assinatura_node

        # Busca o thread_id pelo doc_token no Redis/DB
        # e invoca o grafo no nó pos_assinatura
        ...
    return {"status": "ok"}
```

---

#### Por que apenas `webhook.py` e `zapsign.py` não são suficientes?

Os routers são as **"portas de entrada" HTTP** do sistema — cada um representa quem pode chamar a API externamente. O plano original omitiu 3 routers necessários:

```
Quem chama                   → Router              → O que dispara
─────────────────────────────────────────────────────────────────────
Evolution API (msg recebida) → webhook.py   ✅      → LangGraph Agent
ZapSign (doc assinado)       → zapsign.py   ✅      → pos_assinatura_node
Kommo CRM (evento do funil)  → kommo.py     ❌ novo → reativar bot / sincronizar
Docker healthcheck           → health.py    ❌ novo → verificar status dos serviços
Você (operações manuais)     → admin.py     ❌ novo → resetar estado, inspecionar
```

---

#### [NEW] `app/routers/kommo.py`

**Por que é crítico:** Quando um humano termina de atender um lead (transbordo), como o bot sabe que pode voltar a responder? Sem este router, o `humano_ativo=True` nunca voltaria para `False` automaticamente. O Kommo envia webhooks quando:
- Um lead muda de etapa (`status_lead`) — ex: humano move de "Transbordo" para "Em Negociação"
- Uma tarefa é concluída (`task_completed`) — humano marcou o atendimento como resolvido

```python
from fastapi import APIRouter, BackgroundTasks, Request, Header, HTTPException
import hashlib, hmac, os
from app.schemas.kommo import KommoWebhookPayload

router = APIRouter()


def verificar_assinatura_kommo(body: bytes, signature: str) -> bool:
    """Valida a assinatura HMAC-SHA1 enviada pelo Kommo."""
    secret = os.getenv("KOMMO_WEBHOOK_SECRET", "").encode()
    expected = hmac.new(secret, body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook/kommo")
async def kommo_evento(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature: str = Header(default=""),
):
    """
    Recebe eventos do Kommo CRM.
    Eventos de interesse:
      - status_lead: lead movido de etapa manualmente
      - task_completed: tarefa de atendimento humano concluída
    """
    body = await request.body()

    # Valida assinatura (se configurada no Kommo)
    if os.getenv("KOMMO_WEBHOOK_SECRET"):
        if not verificar_assinatura_kommo(body, x_signature):
            raise HTTPException(status_code=401, detail="Assinatura inválida")

    payload = await request.json()
    background_tasks.add_task(processar_evento_kommo, payload)
    return {"status": "ok"}


async def processar_evento_kommo(payload: dict):
    """
    Processa eventos do Kommo e reativa o bot quando apropriado.

    Cenário principal: humano conclui a tarefa de atendimento
    → define humano_ativo=False no estado LangGraph
    → bot volta a responder para aquele número
    """
    from app.main import app  # acessa o grafo compilado

    # Evento: tarefa concluída
    if "tasks" in payload and "complete" in payload["tasks"]:
        for tarefa in payload["tasks"]["complete"]:
            lead_id = str(tarefa.get("element_id", ""))
            if lead_id:
                await reativar_bot_para_lead(lead_id, app.state.graph)

    # Evento: lead movido de etapa (ex: de "Transbordo" para outra etapa)
    if "leads" in payload and "status" in payload["leads"]:
        for lead in payload["leads"]["status"]:
            nova_etapa = str(lead.get("status_id", ""))
            etapa_transbordo = os.getenv("KOMMO_STATUS_TRANSBORDO", "")
            # Se saiu da etapa de transbordo, reativa o bot
            if nova_etapa != etapa_transbordo:
                lead_id = str(lead.get("id", ""))
                if lead_id:
                    await reativar_bot_para_lead(lead_id, app.state.graph)


async def reativar_bot_para_lead(lead_id: str, graph):
    """Busca o telefone do lead no Kommo e reativa o bot via LangGraph."""
    from integrations import kommo
    from langfuse.callback import CallbackHandler

    contato = await kommo.buscar_contato_do_lead(lead_id)
    if not contato:
        return

    telefone = contato.get("telefone")
    if not telefone:
        return

    config = {
        "configurable": {"thread_id": telefone},
        "callbacks": [CallbackHandler(user_id=telefone, tags=["reativacao-bot"])],
    }

    # Atualiza o estado: humano_ativo → False
    await graph.aupdate_state(
        config,
        {"humano_ativo": False},
    )
```

**Schema Kommo:** `app/schemas/kommo.py`
```python
# O Kommo envia payloads com a estrutura:
# {"leads": {"status": [{"id": "123", "status_id": "456"}]}}
# {"tasks": {"complete": [{"id": "789", "element_id": "123"}]}}
# Não é necessário um modelo Pydantic rígido — processar como dict é mais robusto
```

---

#### [NEW] `app/routers/health.py`

**Por que é necessário:** O Docker usa este endpoint para o `healthcheck`, o Caddy pode usá-lo para verificar se o serviço está pronto, e você vai querer saber instantaneamente se o WhatsApp desconectou.

```python
from fastapi import APIRouter
from integrations import evolution
import os

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Verifica o status de todos os serviços críticos.
    Retorna 200 se tudo OK, 503 se algum serviço crítico estiver down.
    """
    whatsapp_status = await evolution.verificar_status()

    status = {
        "api": "ok",
        "whatsapp": whatsapp_status,  # "open" | "close" | "connecting"
        "whatsapp_conectado": whatsapp_status == "open",
        "instancia": os.getenv("EVOLUTION_INSTANCE"),
    }

    # 503 se WhatsApp desconectado (crítico para o sistema funcionar)
    http_status = 200 if whatsapp_status == "open" else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(content=status, status_code=http_status)


@router.get("/health/ping")
async def ping():
    """Endpoint mínimo — apenas verifica se a API está de pé."""
    return {"status": "pong"}
```

**No `docker-compose.local.yml`, adicionar ao serviço `api`:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/ping"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

#### [NEW] `app/routers/admin.py`

**Por que é necessário:** Durante desenvolvimento e operação, você vai precisar de operações manuais sem ter que acessar diretamente o banco de dados:

```python
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer
import os

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()


def verificar_admin_token(authorization: str = Header(...)):
    """Proteção simples via Bearer token — apenas para uso interno."""
    token = authorization.replace("Bearer ", "")
    if token != os.getenv("ADMIN_SECRET_TOKEN", ""):
        raise HTTPException(status_code=403, detail="Acesso negado")


@router.get("/conversation/{telefone}")
async def inspecionar_conversa(
    telefone: str,
    request: Request,
    _: None = Depends(verificar_admin_token),
):
    """
    Retorna o estado atual da conversa de um número.
    Útil para debug: ver em qual fase o lead está, quais dados foram coletados, etc.

    GET /admin/conversation/5511999999999
    → {"fase": "coleta", "humano_ativo": false, "dados_triagem": {...}}
    """
    config = {"configurable": {"thread_id": telefone}}
    state = await request.app.state.graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Nenhuma conversa encontrada")
    return state.values


@router.post("/conversation/{telefone}/reset")
async def resetar_conversa(
    telefone: str,
    request: Request,
    _: None = Depends(verificar_admin_token),
):
    """
    Reseta o estado da conversa — útil para retomar um fluxo travado.
    Coloca o lead de volta em 'triagem' com humano_ativo=False.

    POST /admin/conversation/5511999999999/reset
    """
    config = {"configurable": {"thread_id": telefone}}
    await request.app.state.graph.aupdate_state(
        config,
        {"fase": "triagem", "humano_ativo": False, "messages": []},
    )
    return {"status": "ok", "telefone": telefone, "nova_fase": "triagem"}


@router.post("/conversation/{telefone}/reativar-bot")
async def reativar_bot(
    telefone: str,
    request: Request,
    _: None = Depends(verificar_admin_token),
):
    """
    Reativa o bot para um número que está em modo transbordo humano.
    Equivalente ao que o webhook do Kommo faz automaticamente.

    POST /admin/conversation/5511999999999/reativar-bot
    """
    config = {"configurable": {"thread_id": telefone}}
    await request.app.state.graph.aupdate_state(
        config,
        {"humano_ativo": False},
    )
    return {"status": "ok", "bot_reativado": True}


@router.get("/whatsapp/status")
async def status_whatsapp(_: None = Depends(verificar_admin_token)):
    """Retorna status detalhado da instância Evolution API."""
    from integrations import evolution

    status = await evolution.verificar_status()
    return {"estado": status, "conectado": status == "open"}
```

**Adicionar ao `.env.local`:**
```env
ADMIN_SECRET_TOKEN=um_token_secreto_para_acesso_ao_admin
KOMMO_WEBHOOK_SECRET=opcional_validacao_hmac_kommo
```

---

#### [MODIFY] `app/main.py` — registrar todos os 5 routers

```python
from app.routers import webhook, zapsign, kommo, health, admin

app.include_router(webhook.router)
app.include_router(zapsign.router)
app.include_router(kommo.router)  # ← novo
app.include_router(health.router)  # ← novo
app.include_router(admin.router)  # ← novo
```

---

### FASE 7 — Pós-Assinatura (Kommo + ADVBOX)


#### [NEW] `agent/nodes.py` — `pos_assinatura_node`

```python
@observe(name="pos_assinatura")
async def pos_assinatura_node(state: LeadState) -> LeadState:
    dados = state["dados_contrato"]
    telefone = state["telefone"]

    # 1. Atualiza Kommo: move para "Ganho"
    await kommo.atualizar_lead(
        lead_id=state["lead_id"],
        status_id=os.getenv("KOMMO_STATUS_GANHO"),
        campo_status_ia="assinado",
    )

    # 2. Cria nota no Kommo com link do contrato
    await kommo.criar_nota(
        lead_id=state["lead_id"],
        texto=f"✅ Contrato assinado. Token ZapSign: {state['zapsign_doc_token']}",
    )

    # 3. Cria cliente no ADVBOX
    customer = await advbox.criar_cliente(
        {
            "name": dados["nome"],
            "email": dados["email"],
            "phone": telefone,
            "document": dados["cpf"],
        }
    )

    # 4. Cria processo no ADVBOX
    lawsuit = await advbox.criar_processo(
        {
            "customer_id": customer["id"],
            "type_lawsuit_id": int(os.getenv("ADVBOX_TYPE_LAWSUIT_ID")),
            "stage_id": int(os.getenv("ADVBOX_STAGE_ID")),
            "description": f"Ação Trabalhista — {dados.get('empresa', 'Empresa não identificada')}",
        }
    )

    # 5. Mensagem de boas-vindas ao cliente no WhatsApp
    await evolution.enviar_texto(
        telefone=telefone,
        texto=(
            "✅ *Contrato assinado com sucesso!*\n\n"
            f"Seja bem-vindo(a), {dados['nome'].split()[0]}! 🎉\n\n"
            "Seu processo já foi registrado em nosso sistema jurídico "
            "e em breve nossa equipe entrará em contato para as próximas etapas.\n\n"
            "Qualquer dúvida, é só me chamar. 😊"
        ),
    )

    return {
        "fase": "concluido",
        "advbox_customer_id": customer["id"],
        "advbox_lawsuit_id": lawsuit["id"],
    }
```

---

### FASE 8 — Transbordo Humano (interrupt nativo LangGraph)

```python
@observe(name="transbordo_humano")
async def transbordo_node(state: LeadState) -> LeadState:
    """Pausa o bot e notifica a equipe no Kommo."""
    lead_id = state["lead_id"]
    nome = state["dados_triagem"].get("nome_lead", "Lead")

    # Cria tarefa urgente no Kommo atribuída ao responsável
    await kommo.criar_tarefa(
        lead_id=lead_id,
        texto=f"⚠️ Atendimento humano necessário: {nome}\nMotivo: {state.get('motivo_transbordo', 'Solicitado pela IA')}",
        prazo_horas=2,
    )

    # Move lead para etapa "Transbordo" no funil
    await kommo.atualizar_lead(
        lead_id=lead_id,
        status_id=os.getenv("KOMMO_STATUS_TRANSBORDO"),
        campo_status_ia="transbordo",
    )

    # Mensagem ao lead
    await evolution.enviar_texto(
        telefone=state["telefone"],
        texto=(
            "Entendido! 👍 Vou chamar um de nossos especialistas para te atender.\n\n"
            "Em breve alguém da equipe da Dra. Lívia França entrará em contato. "
            "Tempo estimado: até 2 horas. ⏰"
        ),
    )

    return {
        "fase": "transbordo",
        "humano_ativo": True,  # Bot silenciado para este número
    }
```

---

### FASE 9 — Cron Jobs (APScheduler)

#### [NEW] `scheduler/jobs.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging


async def verificar_contratos_pendentes(graph):
    """
    Verifica contratos enviados há mais de 24h sem assinatura.
    Envia lembrete ou notifica equipe após 72h.
    """
    # Busca leads com status_ia = "contrato_enviado" no Kommo
    leads = await kommo.listar_leads(campo="status_ia", valor="contrato_enviado")
    for lead in leads:
        horas_sem_assinar = calcular_horas_desde_envio(lead)
        if horas_sem_assinar >= 72:
            await notificar_equipe_contrato_expirado(lead)
        elif horas_sem_assinar in [24, 48]:
            await enviar_lembrete_assinatura(lead)


async def limpar_checkpoints_antigos(pool):
    """Remove checkpoints de conversas finalizadas há mais de 30 dias."""
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM checkpoints WHERE created_at < NOW() - INTERVAL '30 days'")
    logging.info("Checkpoints antigos removidos.")


def registrar_jobs(scheduler: AsyncIOScheduler, graph, pool):
    scheduler.add_job(
        verificar_contratos_pendentes,
        "interval",
        hours=6,
        args=[graph],
        id="lembretes_contrato",
    )
    scheduler.add_job(
        limpar_checkpoints_antigos,
        "cron",
        hour=3,
        minute=0,  # 3h da madrugada
        args=[pool],
        id="cleanup_checkpoints",
    )
```

---

### FASE 10 — Docker Compose

> [!NOTE]
> **Sobre "seudominio.com"**: Em ambiente local, **não existe domínio**. Os serviços ficam acessíveis via `localhost:porta`. O domínio só é necessário em produção (VPS), onde o Caddy gera certificados HTTPS automaticamente apontando para o IP da VPS.
>
> **Sobre o banco do Langfuse**: Não é necessário um *container* PostgreSQL separado — apenas uma *database* separada dentro do mesmo container. Um processo PostgreSQL pode hospedar múltiplos bancos de dados. Separar em *database* (não container) evita conflito de schemas das migrations do Langfuse com as suas tabelas, sem custo de RAM adicional.

---

#### Estratégia de banco de dados — Um container, dois bancos

```
┌─────────────────────────────────────────────────┐
│  Container: postgres                             │
│  ├── Database: autolaw   ← LangGraph, app       │
│  └── Database: langfuse  ← Langfuse (Prisma)    │
└─────────────────────────────────────────────────┘
```

A criação do banco `langfuse` é feita automaticamente via script de inicialização (`init-db.sql`):

#### [NEW] `init-db.sql`
```sql
-- Executado automaticamente pelo PostgreSQL na primeira inicialização
CREATE DATABASE langfuse;
GRANT ALL PRIVILEGES ON DATABASE langfuse TO "user";
```

---

#### [NEW] `docker-compose.local.yml` — Ambiente de desenvolvimento local

Sem Caddy, sem domínio. Tudo acessível via `localhost`:

```yaml
version: "3.9"

networks:
  autolaw-net:
    driver: bridge

services:
  # ── Aplicação principal ──────────────────────────────────────
  api:
    build: .
    ports:
      - "8000:8000"          # FastAPI → http://localhost:8000
    env_file: .env.local
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks: [autolaw-net]
    # Sem restart — deixa cair para ver erros durante dev
    volumes:
      - .:/app               # Hot reload do código Python

  # ── Banco único com dois databases ───────────────────────────
  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"          # Acessível em localhost:5432 (DBeaver, etc.)
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: autolaw   # database principal
      TZ: UTC
    volumes:
      - pgdata_local:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql  # cria DB langfuse
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d autolaw"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks: [autolaw-net]

  # ── Redis ─────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"          # Acessível em localhost:6379 (redis-cli, etc.)
    networks: [autolaw-net]

  # ── WhatsApp Gateway (Baileys) ────────────────────────────────
  evolution-api:
    image: evoapicloud/evolution-api:v2.2.3
    ports:
      - "8080:8080"          # Evolution API → http://localhost:8080
    environment:
      SERVER_URL: http://localhost:8080
      AUTHENTICATION_API_KEY: ${EVOLUTION_API_KEY}
      DATABASE_PROVIDER: postgresql
      DATABASE_CONNECTION_URI: postgresql://user:password@postgres:5432/evolution_db
      CACHE_REDIS_ENABLED: "true"
      CACHE_REDIS_URI: redis://redis:6379/6
      QRCODE_LIMIT: "30"
      LOG_LEVEL: ERROR
    depends_on:
      postgres:
        condition: service_healthy
    volumes: ["evolution_instances_local:/evolution/instances"]
    networks: [autolaw-net]

  # ── Langfuse self-hosted ──────────────────────────────────────
  langfuse:
    image: ghcr.io/langfuse/langfuse:latest
    ports:
      - "3000:3000"          # Langfuse → http://localhost:3000
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      # Banco langfuse dentro do mesmo container postgres
      DATABASE_URL: postgresql://user:password@postgres:5432/langfuse
      NEXTAUTH_URL: http://localhost:3000   # ← sem domínio, só localhost
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      SALT: ${LANGFUSE_SALT}
      ENCRYPTION_KEY: ${LANGFUSE_ENCRYPTION_KEY}
      TELEMETRY_ENABLED: "false"
    networks: [autolaw-net]

volumes:
  pgdata_local:
  evolution_instances_local:
```

**Subir o ambiente local:**
```bash
docker compose -f docker-compose.local.yml up
```

**URLs de acesso local:**
```
FastAPI docs:    http://localhost:8000/docs
Langfuse:        http://localhost:3000
Evolution API:   http://localhost:8080
PostgreSQL:      localhost:5432  (user/password)
```

**Webhook Evolution → FastAPI (dentro da rede Docker):**
```bash
# O webhook aponta para o nome do serviço (não localhost)
curl -X POST http://localhost:8080/webhook/set/livia-franca \
  -H "apikey: SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://api:8000/webhook/message",
    "events": ["MESSAGES_UPSERT"]
  }'
# ↑ "api" é o nome do serviço no docker-compose — funciona dentro da rede
```

---

#### [NEW] `.env.local` — Variáveis para desenvolvimento local

```env
# ── Google Gemini ─────────────────────────────────
GEMINI_API_KEY=sua_chave_gemini
GOOGLE_API_KEY=sua_chave_gemini

# ── Kommo CRM (usar conta real de teste) ──────────
SUBDOMAIN=liviafranaadv
API_KEY=seu_token_kommo

# ── ZapSign (usar sandbox) ────────────────────────
ZAPSIGN_TOKEN=seu_token_sandbox_zapsign
ZAPSIGN_TEMPLATE_ID=id_template_contrato

# ── ADVBOX ────────────────────────────────────────
ADVBOX_TOKEN=seu_token_advbox

# ── Evolution API ─────────────────────────────────
EVOLUTION_API_KEY=chave_local_qualquer_string
EVOLUTION_INSTANCE=livia-franca

# ── Langfuse self-hosted local ────────────────────
# Gerar os 3 com:
#   openssl rand -base64 32   (para NEXTAUTH_SECRET e SALT)
#   openssl rand -hex 32      (para ENCRYPTION_KEY)
LANGFUSE_NEXTAUTH_SECRET=gere_aqui
LANGFUSE_SALT=gere_aqui
LANGFUSE_ENCRYPTION_KEY=gere_aqui_hex
#
# Após criar conta no Langfuse em http://localhost:3000,
# pegue as chaves em Settings → API Keys:
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://langfuse:3000   # nome do serviço docker

# ── Infraestrutura local ──────────────────────────
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/autolaw
REDIS_URL=redis://redis:6379
```

---

#### [NEW] `docker-compose.yml` — Produção (VPS com domínio real)

```yaml
version: "3.9"

networks:
  autolaw-net:
    driver: bridge

services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    networks: [autolaw-net]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: autolaw
      TZ: UTC
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d autolaw"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks: [autolaw-net]

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks: [autolaw-net]

  evolution-api:
    image: evoapicloud/evolution-api:v2.2.3
    ports: ["8080:8080"]
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes: ["evolution_instances:/evolution/instances"]
    restart: unless-stopped
    networks: [autolaw-net]

  langfuse:
    image: ghcr.io/langfuse/langfuse:latest
    ports: ["3000:3000"]
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://user:${DB_PASSWORD}@postgres:5432/langfuse
      NEXTAUTH_URL: https://langfuse.seudominio.com   # ← substituir pelo domínio real
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      SALT: ${LANGFUSE_SALT}
      ENCRYPTION_KEY: ${LANGFUSE_ENCRYPTION_KEY}
      TELEMETRY_ENABLED: "false"
    restart: unless-stopped
    networks: [autolaw-net]

  # ── Proxy reverso HTTPS (Caddy) ───────────────────────────────
  caddy:
    image: caddy:2-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    restart: unless-stopped
    networks: [autolaw-net]

volumes:
  pgdata:
  evolution_instances:
  caddy_data:
```

#### [NEW] `Caddyfile`

```
api.seudominio.com {
    reverse_proxy api:8000
}

whatsapp.seudominio.com {
    reverse_proxy evolution-api:8080
}

langfuse.seudominio.com {
    reverse_proxy langfuse:3000
}
```

---

### FASE 11 — `.env` Definitivo

```env
# ========================================
# Kommo CRM
# ========================================
SUBDOMAIN=liviafranaadv
API_KEY=seu_token_kommo

KOMMO_PIPELINE_ID=id_funil_trabalhista
KOMMO_STATUS_NOVO=id_etapa_novo_lead
KOMMO_STATUS_QUALIFICADO=id_etapa_qualificado
KOMMO_STATUS_CONTRATO_ENVIADO=id_etapa_contrato_enviado
KOMMO_STATUS_TRANSBORDO=id_etapa_transbordo
KOMMO_STATUS_GANHO=id_etapa_ganho

# ========================================
# Google Gemini
# ========================================
GEMINI_API_KEY=sua_chave_gemini
GOOGLE_API_KEY=sua_chave_gemini   # alias para langchain-google-genai

# ========================================
# ZapSign
# ========================================
ZAPSIGN_TOKEN=seu_token_zapsign
ZAPSIGN_TEMPLATE_ID=token_do_template_contrato

# ========================================
# ADVBOX
# ========================================
ADVBOX_TOKEN=seu_token_advbox
ADVBOX_TYPE_LAWSUIT_ID=id_tipo_trabalhista
ADVBOX_STAGE_ID=id_fase_inicial

# ========================================
# Evolution API (WhatsApp)
# ========================================
EVOLUTION_API_URL=https://whatsapp.seudominio.com
EVOLUTION_API_KEY=sua_chave_evolution
EVOLUTION_INSTANCE=livia-franca

# ========================================
# Langfuse (Observabilidade — self-hosted)
# ========================================
# URL do Langfuse rodando na mesma VPS
LANGFUSE_HOST=http://langfuse:3000          # interno (docker network)
# Ou para chamadas de fora da VPS:
# LANGFUSE_HOST=https://langfuse.seudominio.com

# Chaves geradas no painel do Langfuse após primeiro login em https://langfuse.seudominio.com
LANGFUSE_PUBLIC_KEY=pk-lf-...              # Settings → API Keys → Public Key
LANGFUSE_SECRET_KEY=sk-lf-...             # Settings → API Keys → Secret Key

# Segredos do container Langfuse (gerar uma vez com os comandos abaixo):
# NEXTAUTH_SECRET:   openssl rand -base64 32
# SALT:              openssl rand -base64 32
# ENCRYPTION_KEY:    openssl rand -hex 32
LANGFUSE_NEXTAUTH_SECRET=gerar_com_openssl
LANGFUSE_SALT=gerar_com_openssl
LANGFUSE_ENCRYPTION_KEY=gerar_com_openssl_hex

# ========================================
# Infraestrutura
# ========================================
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/autolaw
REDIS_URL=redis://redis:6379
```

---

## ✅ Plano de Verificação

### Testes Automatizados

```bash
# Instalar dependências de dev
pip install -r requirements.txt pytest pytest-asyncio

# Testes dos nós do grafo (sem APIs externas — usar mocks)
pytest tests/test_agent_nodes.py -v

# Testes de integração (com APIs reais — ambiente staging)
pytest tests/test_integrations.py -v -m integration

# Testes dos endpoints FastAPI
pytest tests/test_webhooks.py -v
```

### Verificação Manual por Fase

| Fase | O que verificar |
|---|---|
| 1 | `docker compose up` sem erros, `/docs` FastAPI acessível em HTTPS |
| 2 | Tabelas LangGraph criadas no PostgreSQL (`checkpoints`, `checkpoint_blobs`) |
| 3 | Enviar mensagem de teste → trace aparece no Langfuse com nós corretos |
| 4 | IA faz perguntas de triagem em sequência, uma por vez |
| 5 | Ao qualificar, muda de `fase: triagem` para `fase: coleta` |
| 6 | ZapSign cria documento com variáveis preenchidas, `sign_url` retornado |
| 7 | Link de assinatura chega no WhatsApp via Evolution API |
| 8 | Webhook ZapSign dispara `pos_assinatura_node` → Kommo atualizado + ADVBOX com cliente+processo |
| 9 | Gatilho de transbordo → `humano_ativo=True` + tarefa criada no Kommo + equipe notificada |
| 10 | APScheduler: lembrete enviado após 24h de contrato não assinado |

### Verificação Langfuse

Após cada teste, verificar no dashboard:
- [ ] Trace criado com `user_id = telefone`
- [ ] Spans de cada nó visíveis
- [ ] Custo de tokens registrado por invocação
- [ ] Nenhum span com erro inesperado

---

## 🗓️ Cronograma Estimado

| Fase | Descrição | Estimativa |
|---|---|---|
| 1 | Estrutura, Docker Compose, PostgreSQL, Redis | 1 dia |
| 2 | State + Graph LangGraph + Langfuse setup | 1 dia |
| 3 | FastAPI webhook + buffer Redis | 1 dia |
| 4 | Nó triagem + system prompt + tools Kommo | 2 dias |
| 5 | Nó coleta + validação Pydantic + ZapSign | 1-2 dias |
| 6 | Webhook ZapSign + nó pós-assinatura + ADVBOX | 1-2 dias |
| 7 | Nó transbordo + APScheduler (lembretes) | 1 dia |
| 8 | Testes de ponta a ponta + ajustes + Langfuse | 1-2 dias |
| **Total** | | **~10-13 dias úteis** |
