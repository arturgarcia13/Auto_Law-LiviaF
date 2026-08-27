# 🚀 Pipeline de Desenvolvimento — Auto_Law-LiviaF
## Abordagem: TDD · Docker Incremental · Dependências antes dos Dependentes

> [!NOTE]
> Plano arquitetural completo → [PLANO_AUTOMACAO.md](./PLANO_AUTOMACAO.md)

---

## Princípios

- **Dependência primeiro**: o banco existe antes de quem precisa dele (Langfuse e LangGraph)
- **TDD**: teste falha → implementação → teste passa → refatoração
- **Docker incremental**: cada sprint adiciona apenas os serviços que usa
- **Sem migrações**: LangGraph usa `AsyncPostgresSaver` desde o Sprint 5 — sem `InMemorySaver` intermediário

---

## ✅ Decisões confirmadas

| Questão | Decisão |
|---|---|
| Sistema jurídico | **ADVBOX** (`app.advbox.com.br`) |
| Padrão de código | **Boas práticas de engenharia de software** — type hints, Pydantic v2, testes, separação de responsabilidades, sem hardcode de secrets |

---

## 📊 Pipeline revisada

```mermaid
flowchart TD
    S1[Sprint 1\nEstrutura de Arquivos] --> S2
    S2[Sprint 2\nFastAPI Skeleton] --> S3
    S3[Sprint 3\nPostgreSQL + Redis\num container, dois bancos] --> S4 & S5b
    S4[Sprint 4\nLangfuse\nusa DB 'langfuse'] --> S5
    S5b[Sprint 5\nLangGraph + Gemini\nusa DB 'autolaw'\nAsyncPostgresSaver] --> S5
    S5[Sprint 5 OK: Agente rastreado\ncom persistência real] --> S6
    S6[Sprint 6\nEvolution API\nWhatsApp Baileys] --> S7
    S7[Sprint 7\nKommo CRM] --> S8
    S8[Sprint 8\nZapSign] --> S9
    S9[Sprint 9\nADVBOX]

    style S3 fill:#1565C0,color:#fff
    style S4 fill:#7B1FA2,color:#fff
    style S5b fill:#00897B,color:#fff
```

> [!NOTE]
> Sprints 4 e 5 (Langfuse e LangGraph) dependem do Sprint 3 mas são independentes entre si — podem ser desenvolvidos em paralelo se necessário. Ambos ficam prontos antes do Sprint 6.

---

## Sprint 1 — Estrutura de Arquivos

**Objetivo**: esqueleto completo do projeto Python com todas as pastas, dependências declaradas e pytest configurado.

### Docker neste sprint
```
Nenhum — ambiente Python local puro
```

### Entregáveis
```
Auto_Law-LiviaF/
├── .gitignore                  # Python, .env*, .venv/, __pycache__/, *.pyc
├── .env.local                  # template com placeholders (não commitar valores)
├── .env.example                # versão pública sem secrets
├── requirements.txt            # dependências de produção
├── requirements-dev.txt        # pytest, pytest-asyncio, httpx[mock], mypy
├── pyproject.toml              # pytest + mypy config
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # placeholder
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhook.py
│   │   ├── zapsign.py
│   │   ├── kommo.py
│   │   ├── health.py
│   │   └── admin.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── evolution.py
│   │   ├── lead.py
│   │   └── zapsign.py
│   └── services/
│       ├── __init__.py
│       └── buffer.py
│
├── agent/
│   ├── __init__.py
│   ├── graph.py
│   ├── state.py
│   ├── nodes.py
│   ├── prompts.py
│   └── tools.py
│
├── integrations/
│   ├── __init__.py
│   ├── kommo.py
│   ├── zapsign.py
│   ├── advbox.py
│   └── evolution.py
│
├── scheduler/
│   ├── __init__.py
│   └── jobs.py
│
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_webhooks.py
    ├── test_agent_nodes.py
    ├── test_persistence.py
    ├── test_evolution.py
    ├── test_kommo.py
    ├── test_zapsign.py
    └── test_advbox.py
```

### `pyproject.toml`
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
env_files = [".env.test"]     # env separado para testes

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
```

### Definition of Done ✅
- [ ] `python -m pytest --collect-only` roda sem erros
- [ ] Nenhum secret em arquivo versionável
- [ ] `mypy app/ agent/ integrations/` sem erros críticos

---

## Sprint 2 — FastAPI Skeleton

**Objetivo**: servidor HTTP com todos os 5 routers registrados, validação Pydantic ativa, sem lógica de negócio.

### Docker neste sprint
```
Ainda sem Docker — uvicorn local:
uvicorn app.main:app --reload --port 8000
```

### Entregáveis

**`app/main.py`** — lifespan placeholder (sem banco ainda):
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import webhook, zapsign, kommo, health, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Banco e grafo serão inicializados nos sprints 3 e 5
    yield


app = FastAPI(title="Auto Law — Dra. Lívia França", lifespan=lifespan)
app.include_router(webhook.router)
app.include_router(zapsign.router)
app.include_router(kommo.router)
app.include_router(health.router)
app.include_router(admin.router)
```

**Endpoints mínimos por router:**

| Router | Endpoint | Resposta |
|---|---|---|
| `health.py` | `GET /health/ping` | `{"status": "pong"}` |
| `health.py` | `GET /health` | `{"api": "ok", "whatsapp": "not_configured"}` |
| `webhook.py` | `POST /webhook/message` | `{"status": "ok"}` (sem lógica) |
| `zapsign.py` | `POST /webhook/zapsign` | `{"status": "ok"}` (sem lógica) |
| `kommo.py` | `POST /webhook/kommo` | `{"status": "ok"}` (sem lógica) |
| `admin.py` | `GET /admin/conversation/{tel}` | `501 Not Implemented` |
| `admin.py` | `POST /admin/conversation/{tel}/reset` | `501 Not Implemented` |

**Schemas Pydantic** em `app/schemas/evolution.py` (validação completa do payload Evolution API).

### Testes TDD — escrever ANTES de implementar
```python
# tests/test_health.py
async def test_ping_retorna_200():
    r = client.get("/health/ping")
    assert r.status_code == 200
    assert r.json() == {"status": "pong"}

async def test_health_tem_campos_obrigatorios():
    r = client.get("/health")
    assert "api" in r.json()
    assert "whatsapp" in r.json()

# tests/test_webhooks.py
async def test_webhook_aceita_payload_evolution_valido():
    r = client.post("/webhook/message", json=PAYLOAD_VALIDO)
    assert r.status_code == 200

async def test_webhook_rejeita_payload_invalido():
    r = client.post("/webhook/message", json={"campo_invalido": True})
    assert r.status_code == 422   # Pydantic ValidationError

async def test_webhook_zapsign_aceita_evento_doc_signed():
    r = client.post("/webhook/zapsign", json={"event": "doc_signed", ...})
    assert r.status_code == 200
```

### Definition of Done ✅
- [ ] `pytest tests/test_health.py tests/test_webhooks.py` → verde
- [ ] Payload inválido → 422 (Pydantic, não 500)
- [ ] `GET /docs` mostra todos os endpoints documentados
- [ ] Type hints em todas as funções

---

## Sprint 3 — PostgreSQL + Redis (Infraestrutura Unificada)

**Objetivo**: banco de dados único com duas databases isoladas (`autolaw` e `langfuse`) + Redis. Pronto para receber Langfuse (Sprint 4) e LangGraph (Sprint 5).

### Docker neste sprint — `docker-compose.local.yml` v1
```yaml
version: "3.9"

networks:
  autolaw-net:
    driver: bridge

services:
  # ── Banco unificado: databases 'autolaw' + 'langfuse' ─────────
  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"           # acessível em localhost:5432 (DBeaver, psql)
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: autolaw    # database principal
      TZ: UTC                 # obrigatório para Langfuse
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d autolaw"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks: [autolaw-net]

  # ── Cache e buffer ─────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"           # acessível em localhost:6379
    networks: [autolaw-net]

volumes:
  pgdata:
```

### `init-db.sql`
```sql
-- Executado automaticamente pelo PostgreSQL na primeira inicialização
-- Cria as databases isoladas para cada serviço

CREATE DATABASE langfuse;
GRANT ALL PRIVILEGES ON DATABASE langfuse TO "user";

-- 'autolaw' já existe (POSTGRES_DB) — não precisa criar
```

### Testes TDD
```python
# tests/test_persistence.py
async def test_postgres_conecta():
    """Verifica conexão básica com o banco autolaw."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(os.getenv("DATABASE_URL"))
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


async def test_database_langfuse_existe():
    """Verifica que o init-db.sql criou a database langfuse."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT datname FROM pg_database WHERE datname = 'langfuse'")
        )
        assert result.scalar() == "langfuse"


async def test_redis_conecta():
    import redis.asyncio as aioredis

    r = aioredis.from_url(os.getenv("REDIS_URL"))
    await r.ping()  # raises se não conectar
```

```bash
# Verificação manual
docker compose -f docker-compose.local.yml up -d
psql -h localhost -U user -d autolaw -c "\l"
# → deve listar: autolaw, langfuse
redis-cli -h localhost ping
# → PONG
```

### Definition of Done ✅
- [ ] `docker compose -f docker-compose.local.yml up -d` → containers saudáveis
- [ ] `psql` confirma databases `autolaw` e `langfuse` existem
- [ ] `redis-cli ping` → PONG
- [ ] `pytest tests/test_persistence.py::test_postgres_conecta` → verde

---

## Sprint 4 — Langfuse Self-hosted

**Objetivo**: dashboard de observabilidade rodando, SDK configurado, pronto para receber traces do LangGraph no Sprint 5.

### Docker neste sprint — `docker-compose.local.yml` v2
```yaml
# Adicionar ao v1:

  langfuse:
    image: ghcr.io/langfuse/langfuse:latest
    ports:
      - "3000:3000"             # dashboard em http://localhost:3000
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/langfuse
      NEXTAUTH_URL: http://localhost:3000
      NEXTAUTH_SECRET: ${LANGFUSE_NEXTAUTH_SECRET}
      SALT: ${LANGFUSE_SALT}
      ENCRYPTION_KEY: ${LANGFUSE_ENCRYPTION_KEY}
      TELEMETRY_ENABLED: "false"
    networks: [autolaw-net]
```

### Gerar os secrets (executar uma vez)
```bash
# PowerShell equivalente:
python -c "import secrets; print(secrets.token_urlsafe(32))"  # NEXTAUTH_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"  # SALT
python -c "import secrets; print(secrets.token_hex(32))"      # ENCRYPTION_KEY
# → copiar para .env.local
```

### Testes TDD
```python
# tests/test_langfuse.py
def test_langfuse_ui_acessivel():
    """Verifica que o Langfuse está rodando e acessível."""
    import httpx

    r = httpx.get("http://localhost:3000/api/health", timeout=10)
    assert r.status_code == 200


def test_sdk_envia_trace():
    """Verifica que o SDK consegue enviar uma trace ao Langfuse local."""
    from langfuse import Langfuse

    lf = Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST"),
    )
    trace = lf.trace(name="test-sprint-4", input={"test": True})
    trace.update(output={"status": "ok"})
    lf.flush()
    # → verificar no dashboard http://localhost:3000 que a trace aparece
```

### Passos manuais após subir
1. Acessar `http://localhost:3000`
2. Criar conta de admin
3. Gerar API Keys em `Settings → API Keys`
4. Copiar `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` para `.env.local`

### Definition of Done ✅
- [ ] `http://localhost:3000` carrega o dashboard
- [ ] API Keys geradas e salvas no `.env.local`
- [ ] `pytest tests/test_langfuse.py` → verde
- [ ] Trace de teste visível no dashboard

---

## Sprint 5 — LangGraph + Google Gemini

**Objetivo**: agente conversacional com estado persistente (PostgreSQL, sem InMemorySaver), rastreado no Langfuse desde o primeiro dia.

### Docker neste sprint
```
Sem mudanças no docker-compose.local.yml
FastAPI roda em uvicorn local conectando ao postgres e langfuse do Docker
```

### Entregáveis
- `agent/state.py` — `LeadState` TypedDict completo
- `agent/graph.py` — `StateGraph` com `AsyncPostgresSaver`
- `agent/nodes.py` — nós com `@observe` Langfuse, lógica básica de triagem
- `agent/prompts.py` — system prompts de triagem e coleta
- `agent/tools.py` — tools stub (sem chamadas reais a APIs externas ainda)
- `app/main.py` atualizado — grafo compilado com `AsyncPostgresSaver` no lifespan
- `app/routers/webhook.py` atualizado — chama `graph.ainvoke` com `CallbackHandler`

### `app/main.py` — lifespan com banco
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncConnectionPool(os.environ["DATABASE_URL"]) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()  # cria tabelas LangGraph no banco
        app.state.graph = build_graph(checkpointer)
        yield
```

### Testes TDD
```python
# tests/test_agent_nodes.py
async def test_triagem_node_responde_mensagem(postgres_checkpointer):
    state = LeadState(
        messages=[HumanMessage("fui demitido sem justa causa")],
        telefone="5511999999999",
        fase="triagem",
        humano_ativo=False,
        dados_triagem={},
        dados_contrato={},
        lead_id=None,
        contato_id=None,
        zapsign_doc_token=None,
        zapsign_sign_url=None,
        advbox_customer_id=None,
        advbox_lawsuit_id=None,
        motivo_transbordo=None,
    )
    resultado = await triagem_node(state)
    assert "messages" in resultado
    assert len(resultado["messages"]) > 0


async def test_triagem_qualifica_para_coleta(postgres_checkpointer):
    # Simula lead com CTPS + > 3 meses
    # → fase deve mudar para "coleta"
    ...


async def test_triagem_aciona_transbordo_acidente_grave(postgres_checkpointer):
    # Mensagem sobre acidente de trabalho grave
    # → fase deve mudar para "transbordo"
    ...


async def test_estado_persiste_entre_invocacoes(postgres_checkpointer, graph):
    # Envia 1ª mensagem, depois 2ª com nova invocação do grafo
    # → histórico da 1ª mensagem deve estar presente na 2ª
    telefone = "5511000000001"
    config = {"configurable": {"thread_id": telefone}}

    await graph.ainvoke(
        {"messages": [("user", "fui demitido")], "telefone": telefone},
        config=config,
    )
    state_apos = await graph.aget_state(config)
    assert len(state_apos.values["messages"]) >= 2  # user + assistant


async def test_langfuse_trace_criada_por_invocacao(langfuse_mock):
    # Verifica que CallbackHandler é chamado durante ainvoke
    ...
```

### Verificação manual
```bash
# Teste de conversa via curl
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "livia-franca",
    "data": {
      "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": false, "id": "abc"},
      "message": {"conversation": "olá, fui demitido sem justa causa"},
      "messageType": "conversation",
      "messageTimestamp": 1234567890
    }
  }'
# → resposta do bot no JSON + trace no Langfuse em http://localhost:3000
```

### Definition of Done ✅
- [ ] Tabelas `checkpoints` e `checkpoint_blobs` criadas no PostgreSQL
- [ ] Bot mantém contexto em múltiplos turnos (estado persiste no banco)
- [ ] Trace com nós, tokens e latência visível no Langfuse
- [ ] `pytest tests/test_agent_nodes.py` → verde
- [ ] Fase muda corretamente: `triagem → coleta`, `triagem → transbordo`
- [ ] `GET /admin/conversation/{tel}` retorna estado real (não mais 501)

---

## Sprint 6 — Evolution API (WhatsApp Baileys)

**Objetivo**: bot recebe e responde mensagens reais via QR Code.

### Docker neste sprint — `docker-compose.local.yml` v3
```yaml
# Adicionar ao v2:

  evolution-api:
    image: evoapicloud/evolution-api:v2.2.3   # versão fixada
    ports:
      - "8080:8080"
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
    volumes: ["evolution_instances:/evolution/instances"]
    networks: [autolaw-net]

volumes:
  pgdata:
  evolution_instances:   # ← novo
```

> [!NOTE]
> O Evolution API precisa de uma terceira database no PostgreSQL (`evolution_db`). Adicionar ao `init-db.sql`:
> ```sql
> CREATE DATABASE evolution_db;
> GRANT ALL PRIVILEGES ON DATABASE evolution_db TO "user";
> ```

### Entregáveis
- `integrations/evolution.py` — `enviar_texto()`, `verificar_status()`
- `app/services/buffer.py` — Redis buffer (agrupa msgs do mesmo número em 3s)
- `app/routers/health.py` finalizado — verifica `state == "open"`
- `app/routers/webhook.py` finalizado — filtro `fromMe`, buffer Redis
- Script de setup da instância (executar uma vez)

### Testes TDD
```python
# tests/test_evolution.py
async def test_enviar_texto_monta_payload_correto(httpx_mock):
    httpx_mock.add_response(url=..., json={"key": {...}})
    await evolution.enviar_texto("5511999999999", "Olá!")
    req = httpx_mock.get_requests()[0]
    body = req.read()
    assert b"5511999999999" in body
    assert b"delay" in body                     # simula digitação

async def test_webhook_ignora_mensagens_proprias():
    payload_from_me = {..., "fromMe": True}
    r = client.post("/webhook/message", json=payload_from_me)
    assert r.status_code == 200
    # grafo NÃO deve ser invocado

async def test_health_503_quando_whatsapp_desconectado(httpx_mock):
    httpx_mock.add_response(json={"instance": {"state": "close"}})
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["whatsapp_conectado"] == False
```

### Definition of Done ✅
- [ ] QR Code escaneado, sessão ativa (`state: open`)
- [ ] Mensagem enviada pelo celular → bot responde no WhatsApp
- [ ] Trace aparece no Langfuse com conteúdo real da conversa
- [ ] `GET /health` → `"whatsapp": "open"`
- [ ] `pytest tests/test_evolution.py` → verde

---

## Sprint 7 — Kommo CRM

**Objetivo**: leads criados automaticamente no Kommo, movidos entre etapas conforme o fluxo.

### Docker neste sprint
```
Sem mudanças no docker-compose.local.yml
Kommo é uma API externa — sem container local
```

### Entregáveis
- `integrations/kommo.py` — funções completas:
  - `criar_lead()` + `criar_contato()` — primeira mensagem
  - `atualizar_lead()` — move etapa + campo `status_ia`
  - `criar_nota()` — registra eventos no timeline
  - `criar_tarefa()` — transbordo humano (prazo 2h)
  - `buscar_contato_do_lead()` — reativação do bot
- `agent/tools.py` atualizado — tools Kommo reais (sem stubs)
- `app/routers/kommo.py` finalizado — reativação automática do bot
- Utilitário: `python -m scripts.mapear_kommo` → imprime todos os IDs de pipeline e etapas

### Testes TDD
```python
# tests/test_kommo.py
async def test_criar_lead_retorna_id(httpx_mock):
    httpx_mock.add_response(json={"_embedded": {"leads": [{"id": 123}]}})
    lead_id = await kommo.criar_lead("5511999999999", "João Silva", pipeline_id="456")
    assert lead_id == 123


async def test_atualizar_lead_envia_status_correto(httpx_mock):
    httpx_mock.add_response(json={})
    await kommo.atualizar_lead("123", status_id="789")
    req_body = json.loads(httpx_mock.get_requests()[0].content)
    assert req_body[0]["status_id"] == 789


async def test_webhook_kommo_reativa_bot(graph, redis_client):
    # Simula tarefa concluída → humano_ativo deve voltar False
    ...
```

### Definition of Done ✅
- [ ] Primeira mensagem de novo número → lead criado no Kommo
- [ ] Etapas movidas conforme tabela do PLANO_AUTOMACAO.md
- [ ] Notas criadas em cada transição
- [ ] Transbordo → tarefa urgente criada (prazo 2h)
- [ ] `pytest tests/test_kommo.py` → verde

---

## Sprint 8 — ZapSign

**Objetivo**: contrato gerado e link de assinatura enviado pelo WhatsApp automaticamente.

### Docker neste sprint
```
Sem mudanças no docker-compose.local.yml
ZapSign é API externa — sem container local
```

### Entregáveis
- `integrations/zapsign.py` — `criar_documento()` com variáveis do contrato
- `agent/nodes.py` — `gerar_contrato_node` completo
- `app/routers/zapsign.py` finalizado — `doc_signed` → `pos_assinatura_node`
- Mapeamento `doc_token → telefone` no Redis (TTL 7 dias)

### Testes TDD
```python
# tests/test_zapsign.py
async def test_criar_documento_preenche_todas_variaveis(httpx_mock):
    httpx_mock.add_response(json={"token": "abc", "open_id": "https://sign.url"})
    r = await zapsign.criar_documento(dados_contrato_completo)
    assert r["doc_token"] == "abc"
    assert "sign_url" in r
    req_body = json.loads(httpx_mock.get_requests()[0].content)
    assert req_body["send_automatic_whatsapp"] == False  # grátis via Evolution


async def test_webhook_doc_signed_dispara_pos_assinatura(graph, redis_client):
    await redis_client.set("zapsign:abc", "5511999999999", ex=604800)
    r = client.post("/webhook/zapsign", json={"event": "doc_signed", "document": {"token": "abc"}})
    assert r.status_code == 200
    state = await graph.aget_state({"configurable": {"thread_id": "5511999999999"}})
    assert state.values["fase"] == "concluido"
```

### Definition of Done ✅
- [ ] Dados do contrato preenchidos corretamente nas variáveis do template
- [ ] Link de assinatura enviado via Evolution API (não via ZapSign `send_whatsapp`)
- [ ] Webhook `doc_signed` → estado muda para `"concluido"` + ações pós-assinatura
- [ ] `pytest tests/test_zapsign.py` → verde

---

## Sprint 9 — ADVBOX

**Objetivo**: pós-assinatura cria cliente e processo no sistema jurídico automaticamente.

Sistema: **ADVBOX** (`app.advbox.com.br`) ✅

### Docker neste sprint
```
Sem mudanças no docker-compose.local.yml
ADVBOX é API externa — sem container local
```

### Entregáveis
- `integrations/advbox.py` — `criar_cliente()`, `criar_processo()`
- `agent/nodes.py` — `pos_assinatura_node` completo (Kommo + ADVBOX + WhatsApp)
- Utilitário: `python -m scripts.mapear_advbox` → imprime `type_lawsuit_id` e `stage_id`

### Testes TDD
```python
# tests/test_advbox.py
async def test_criar_cliente_retorna_id(httpx_mock):
    httpx_mock.add_response(json={"id": 456})
    cid = await advbox.criar_cliente({"name": "João", "document": "000.000.000-00", ...})
    assert cid == 456

async def test_criar_processo_usa_env_ids(httpx_mock):
    httpx_mock.add_response(json={"id": 789})
    await advbox.criar_processo({"customer_id": 456, ...})
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["type_lawsuit_id"] == int(os.getenv("ADVBOX_TYPE_LAWSUIT_ID"))

async def test_fluxo_completo_ponta_a_ponta(httpx_mock, graph, redis_client):
    # 1. Simula webhook ZapSign doc_signed
    # 2. Verifica: Kommo → "Ganho"
    # 3. Verifica: ADVBOX → cliente + processo criados
    # 4. Verifica: WhatsApp → mensagem de boas-vindas enviada
    ...
```

### Definition of Done ✅
- [ ] Contrato assinado → cliente criado no ADVBOX
- [ ] Processo trabalhista criado com `type_lawsuit_id` correto
- [ ] Lead movido para "Ganho" no Kommo
- [ ] Mensagem de boas-vindas enviada ao lead
- [ ] `pytest tests/test_advbox.py` → verde
- [ ] **Teste de ponta a ponta completo**: novo lead → triagem → coleta → ZapSign → assinatura → ADVBOX → "Ganho"

---

## 📋 Boas Práticas (todos os sprints)

| Prática | Aplicação |
|---|---|
| Type hints | Todas as funções: `async def foo(x: str) -> dict` |
| Pydantic v2 | Validar todos os inputs externos (webhooks, respostas de API) |
| `httpx.AsyncClient` | Com `timeout` explícito em todas as chamadas HTTP |
| `@observe` Langfuse | Todos os nós do grafo e funções de integração |
| `try/except` | Com log estruturado em todas as chamadas a APIs externas |
| Sem hardcode | Zero valores secretos no código — tudo via `.env.local` |
| `fromMe=True` ignorado | Evita loop infinito no webhook |
| `BackgroundTasks` | Webhook retorna 200 imediatamente, processa em background |
| `pytest-asyncio` | Todos os testes assíncronos |
| `httpx_mock` / `respx` | Mockar APIs externas nos testes unitários |

---

## 📊 Resumo dos sprints e Docker

| Sprint | Novo no Docker | Estado do sistema ao final |
|---|---|---|
| 1 | — | Estrutura de arquivos |
| 2 | — | FastAPI rodando localmente |
| 3 | `postgres` + `redis` | Banco pronto para os próximos |
| 4 | `langfuse` | Dashboard de observabilidade ativo |
| 5 | — | Agente IA conversacional com persistência + tracing |
| 6 | `evolution-api` | Bot respondendo no WhatsApp real |
| 7 | — | Leads criados e movidos no Kommo |
| 8 | — | Contratos enviados e assinados via ZapSign |
| 9 | — | Sistema completo ponta a ponta |
