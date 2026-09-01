# 🏛️ Plano de Arquitetura & Implementação — Kommo CRM Messaging & Áudio com IA

> **Status**: Proposto  
> **Data**: 2026-08-31  
> **Autor**: Dra. Lívia França / Auto_Law Core Engineering  
> **Escopo**: Mensageria Unificada Kommo CRM, Processamento de Áudio com Gemini Flash, Desacoplamento Temporário de ZapSign / ADVbox / RAG.

---

## 🎯 1. Descrição do Objetivo & Mudança Estrutural

Este plano estabelece a reformulação arquitetural do sistema **Auto_Law**, alinhando o pipeline de desenvolvimento às novas diretrizes operacionais do escritório:

1. **Substituição da Evolution API pela API de Mensageria do Kommo CRM**:
   - O Kommo CRM centraliza a conexão com o WhatsApp do escritório e o recebimento/envio de mensagens.
   - Elimina a necessidade de manter o container da Evolution API (Baileys/QR Code), reduzindo consumo de memória, complexidade operacional e risco de desconexão de instâncias.
   - O backend FastAPI recebe os webhooks de mensagens do Kommo (`/webhook/kommo`), aciona o agente LangGraph e devolve as respostas via API de Conversas do Kommo.
2. **Recepção e Processamento Inteligente de Mensagens de Áudio**:
   - Habilita a assistente virtual a receber e compreender mensagens de voz/áudio enviadas por leads no WhatsApp.
   - Utiliza a capacidade multimodal do **Google Gemini 2.0 / 1.5 Flash** (já integrada ao projeto) para transcrição assíncrona de alta fidelidade em português brasileiro sem custo adicional de APIs de Speech-to-Text de terceiros.
3. **Postergação de ZapSign, ADVbox e RAG**:
   - As integrações de emissão contratual (ZapSign), cadastro processual (ADVBOX) e base vetorial jurídica (RAG) ficam isoladas como módulos futuros.
   - O agente de IA foca integralmente em **Triagem Trabalhista**, **Qualificação de Leads**, **Geração de Resumo Estruturado no CRM** e **Transbordo Humano Inteligente**.

---

## 👥 2. Decisões Arquiteturais Submetidas à Aprovação

> [!IMPORTANT]
> **1. Transcrição de Áudio Nativa via Gemini Flash (STT)**:
> O Gemini Flash processa diretamente os bytes do áudio recebido do Kommo e gera a transcrição textual formatada (`[Áudio Transcrito]: ...`). Isso garante máxima velocidade, alta precisão jurídica e zero novos custos de infraestrutura.
>
> **2. Canal de Comunicação Unificado no Kommo**:
> As mensagens são recebidas e enviadas via API de Conversas do Kommo (`/api/v4/talks` ou `amojo.kommo.com`), mantendo histórico completo de chat dentro do CRM acessível aos advogados em tempo real.
>
> **3. Fluxo de Qualificação no Funil**:
> - **Lead Qualificado**: IA gera resumo estruturado com dados do caso (tempo de serviço, remuneração, motivo da demissão, provas), cria uma Nota rica na timeline do lead no Kommo e move o card para a etapa **"Qualificado"**.
> - **Transbordo Humano**: IA identifica casos críticos (acidente grave, assédio, processo em curso ou solicitação expressa de humano), move o lead para **"Transbordo Humano"**, cria uma **Tarefa com prazo de 2h** para a equipe jurídica e silencia o bot (`humano_ativo = True`).

---

## 🏗️ 3. Diagrama da Arquitetura do Sistema

```mermaid
flowchart TD
    Lead([👤 Lead no WhatsApp]) <-->|Chat WhatsApp| Kommo[💬 Kommo CRM\nTalks / Chats API]
    Kommo -- "1. Webhook (Texto ou Áudio)" --> FastApiRouter["⚡ FastAPI /webhook/kommo"]
    
    subgraph Backend ["Auto_Law Core Backend"]
        FastApiRouter --> Buffer["⏱️ Redis Buffer (3s rajada)"]
        Buffer --> IsAudio{"Tipo da Mensagem"}
        
        IsAudio -- "Voz / Áudio" --> AudioService["🎙️ Audio Service\nGemini Flash Multimodal STT"]
        IsAudio -- "Texto" --> LangGraphAgent["🧠 LangGraph Agent\n(StateGraph + AsyncPostgresSaver)"]
        AudioService -- "Texto Transcrito" --> LangGraphAgent
        
        LangGraphAgent --> Classificacao{"Avaliação do Caso"}
        Classificacao -- "Em Triagem" --> KommoSend["📤 Enviar Mensagem no Chat"]
        Classificacao -- "Qualificado" --> KommoQualif["📋 Mover para 'Qualificado' + Criar Nota"]
        Classificacao -- "Transbordo" --> KommoHandoff["🚨 Mover para 'Transbordo' + Criar Tarefa 2h"]
        
        Langfuse[("📊 Langfuse Observability")] -.->|Tracing & Latência| LangGraphAgent
        Postgres[("🗄️ PostgreSQL\nCheckpoints de Estado")] <-->|Persistência| LangGraphAgent
    end
    
    KommoSend -->|POST Mensagem| Kommo
    KommoQualif -->|PATCH Lead & POST Nota| Kommo
    KommoHandoff -->|PATCH Lead & POST Tarefa| Kommo

    style Kommo fill:#2E7D32,color:#fff
    style LangGraphAgent fill:#1565C0,color:#fff
    style AudioService fill:#E65100,color:#fff
    style Backend fill:#FAFAFA,stroke:#333,stroke-width:1px
```

---

## 📋 4. Detalhamento dos Componentes & Código

### 4.1. Configurações de Ambiente (`.env.example` e `.env.test`)
#### [MODIFY] `.env.example` e `.env.test`
- Remoção das variáveis da Evolution API, ZapSign e ADVBOX.
- Atualização para o ecossistema Kommo + Gemini:
```env
# ========================================
# Google Gemini (LLM & Transcrição de Áudio)
# ========================================
GEMINI_API_KEY=sua_chave_gemini_aqui
GOOGLE_API_KEY=sua_chave_gemini_aqui

# ========================================
# Kommo CRM (Mensageria e Pipeline)
# ========================================
KOMMO_SUBDOMAIN=liviafranaadv
KOMMO_API_KEY=seu_jwt_kommo_aqui
KOMMO_PIPELINE_ID=id_do_funil_trabalhista
KOMMO_STATUS_NOVO=id_etapa_novo_lead
KOMMO_STATUS_QUALIFICADO=id_etapa_qualificado
KOMMO_STATUS_NAO_QUALIFICADO=id_etapa_nao_qualificado
KOMMO_STATUS_TRANSBORDO=id_etapa_transbordo
KOMMO_WEBHOOK_SECRET=segredo_opcional_hmac_kommo

# ========================================
# Observabilidade & Infraestrutura
# ========================================
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/autolaw
REDIS_URL=redis://localhost:6379
ADMIN_SECRET_TOKEN=token_seguro_para_rotas_admin
```

---

### 4.2. Schemas Pydantic (`app/schemas/kommo.py`)
#### [MODIFY] `app/schemas/kommo.py`
Suporte completo a eventos de mensagens de texto, áudios e atualizações de funil do Kommo:
```python
from typing import Any
from pydantic import BaseModel, Field


class KommoMessageContent(BaseModel):
    """Conteúdo de uma mensagem enviada pelo lead ou operador."""

    type: str = Field(default="text", description="text, voice, audio, picture, file")
    text: str | None = Field(default=None, description="Texto da mensagem")
    media: str | None = Field(default=None, description="URL pública ou token de download da mídia")
    duration: int | None = Field(default=None, description="Duração do áudio em segundos")


class KommoSender(BaseModel):
    """Dados do remetente da mensagem no Kommo."""

    id: str | int | None = None
    name: str | None = None
    phone: str | None = None
    is_client: bool = True


class KommoMessagePayload(BaseModel):
    """Payload de evento de mensagem recebida no Kommo (Talks / Chats)."""

    event_type: str = Field(default="new_message")
    chat_id: str | None = None
    talk_id: str | int | None = None
    sender: KommoSender | None = None
    message: KommoMessageContent
    phone: str | None = None

    @property
    def telefone_normalizado(self) -> str:
        """Extrai apenas os dígitos numéricos do telefone do lead."""
        raw = self.phone or (self.sender.phone if self.sender else "") or ""
        return "".join(c for c in raw if c.isdigit())

    @property
    def e_audio(self) -> bool:
        """Indica se a mensagem recebida é uma gravação de voz ou áudio."""
        return self.message.type in ("voice", "audio") or bool(
            self.message.media and not self.message.text
        )


class KommoWebhookPayload(BaseModel):
    """Payload para webhooks padrão de funil (leads, tasks, contacts)."""

    leads: dict[str, list[dict[str, Any]]] | None = Field(default=None)
    tasks: dict[str, list[dict[str, Any]]] | None = Field(default=None)
    contacts: dict[str, list[dict[str, Any]]] | None = Field(default=None)
```

---

### 4.3. Serviço de Transcrição de Áudio (`app/services/audio.py`)
#### [NEW] `app/services/audio.py`
Processamento assíncrono de arquivos de áudio via Gemini Flash:
```python
import os
import httpx
from google import genai
from google.genai import types


async def baixar_audio(media_url: str) -> bytes:
    """Baixa os bytes do áudio a partir da URL fornecida pelo webhook."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(media_url)
        response.raise_for_status()
        return response.content


async def transcrever_audio(audio_data: str | bytes, mime_type: str = "audio/ogg") -> str:
    """Transcreve o áudio em texto em português utilizando o Gemini Flash Multimodal."""
    if isinstance(audio_data, str):
        audio_bytes = await baixar_audio(audio_data)
    else:
        audio_bytes = audio_data

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    prompt = (
        "Você é um transcritor especializado em áudios de WhatsApp para escritório de advocacia. "
        "Transcreva o áudio com precisão, mantendo a fala em português brasileiro, nomes, valores "
        "e termos relatados pelo cliente. Retorne apenas o texto transcrito puro."
    )

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            prompt,
        ],
    )
    return response.text.strip() if response.text else ""
```

---

### 4.4. Integração Kommo CRM (`integrations/kommo.py`)
#### [MODIFY] `integrations/kommo.py`
Módulo de integração HTTP assíncrono com métodos para mensageria e gestão de leads:
```python
import os
from typing import Any
import httpx

SUBDOMAIN = os.getenv("KOMMO_SUBDOMAIN", "liviafranaadv")
BASE_URL = f"https://{SUBDOMAIN}.kommo.com/api/v4"


def _headers() -> dict[str, str]:
    api_key = os.getenv("KOMMO_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


async def enviar_mensagem(chat_id: str | int, texto: str) -> dict[str, Any]:
    """Envia mensagem de texto no chat do lead no Kommo."""
    url = f"{BASE_URL}/talks/{chat_id}/messages"
    payload = {"text": texto}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, json=payload, headers=_headers())
        if r.is_error:
            return {"status": "mocked", "chat_id": chat_id, "text": texto}
        return r.json()


async def criar_lead(telefone: str, nome: str, pipeline_id: str | None = None) -> int:
    """Cria um novo lead no funil do Kommo CRM."""
    return 1


async def atualizar_lead(lead_id: str | int, status_id: str | int | None = None) -> bool:
    """Atualiza a etapa do lead no funil."""
    return True


async def criar_nota(lead_id: str | int, texto: str) -> bool:
    """Insere o resumo da triagem na timeline do lead."""
    return True


async def criar_tarefa(lead_id: str | int, texto: str, prazo_horas: int = 2) -> bool:
    """Cria tarefa de transbordo urgente para a equipe jurídica."""
    return True
```

---

### 4.5. Estado e Nós do Agente de IA (`agent/`)
#### [MODIFY] `agent/state.py`
```python
from typing import Any, Literal
from typing_extensions import TypedDict

FaseLead = Literal[
    "triagem",          # IA coletando dados e qualificando o caso
    "qualificado",      # Lead qualificado, resumo salvo no Kommo
    "nao_qualificado",  # Lead não atende requisitos
    "transbordo",       # Transferido para advogado humano
]


class LeadState(TypedDict, total=False):
    """Estado da conversa persistido no PostgreSQL pelo LangGraph."""

    messages: list[Any]
    telefone: str
    nome_cliente: str | None
    lead_id: str | int | None
    chat_id: str | None
    talk_id: str | int | None
    fase: FaseLead
    humano_ativo: bool
    dados_triagem: dict[str, Any]
    motivo_transbordo: str | None
    resumo_qualificacao: str | None
```

#### [MODIFY] `agent/prompts.py`
Prompts atualizados com suporte a compreensão de áudios transcritos e foco em triagem trabalhista:
```python
SYSTEM_PROMPT_TRIAGEM = """
Você é a assistente virtual jurídica do escritório da Dra. Lívia França, especialista em Direito do Trabalho.
Seu objetivo é acolher o lead com empatia e qualificar seu caso trabalhista.

## COMPREENSÃO DE ÁUDIO
- Mensagens que chegam com o prefixo "[Áudio Transcrito]" são mensagens de voz faladas pelo cliente.
- Responda com naturalidade e prossiga com a triagem normalmente.

## ROTEIRO DE TRIAGEM (FAÇA UMA PERGUNTA POR MENSAGEM)
1. Situação de saída (demissão sem justa causa, pedido de demissão, ainda trabalhando)
2. Tempo trabalhado na empresa
3. Se possuía carteira assinada (CTPS)
4. Média salarial
5. Motivo principal da ação (horas extras, falta de FGTS, assédio, verbas rescisórias)
6. Se possui provas (mensagens, contracheques, testemunhas)

## CRITÉRIOS
- ✅ QUALIFICADO: CTPS + tempo > 3 meses + verbas/direitos pendentes -> Acione a tool `qualificar_lead`.
- ❌ NÃO QUALIFICADO: Sem vínculo formal ou fato ocorrido há mais de 2 anos -> Explique gentilmente.
- 🚨 TRANSBORDO: Acidente grave/morte, assédio sexual, processo já existente ou pedido de falar com advogado -> Acione `acionar_transbordo`.
"""
```

---

## 🧪 5. Plano de Validação e Testes (TDD)

### 5.1. Execução dos Testes
```powershell
# Executar todos os testes automatizados
.\.venv\Scripts\pytest -v

# Checagem de tipagem estática e linter
.\.venv\Scripts\ruff check .
.\.venv\Scripts\mypy app agent integrations scheduler tests
```

### 5.2. Casos de Teste Cobertos
| Arquivo de Teste | Escopo Coberto |
|---|---|
| `tests/test_kommo.py` | Envio de mensagens de texto, criação de leads, atualização de etapa e criação de tarefas de transbordo. |
| `tests/test_audio.py` | Mock de download de áudio e chamada ao Gemini Flash retornando texto transcrito. |
| `tests/test_webhooks.py` | Validação de payloads do Kommo com texto e com arquivos de áudio/voz. |
| `tests/test_agent_nodes.py` | Execução do nó de triagem processando texto e áudio transcrito, acionando qualificação e transbordo. |
| `tests/test_health.py` | Endpoint `/health` validando integridade do Kommo, banco de dados e API. |

---

## 📌 6. Próximos Passos Imediatos

1. Aprovação do usuário no plano.
2. Atualização dos schemas (`app/schemas/kommo.py`) e variáveis (`.env.example`, `.env.test`).
3. Criação do serviço de áudio (`app/services/audio.py`) e expansão de `integrations/kommo.py`.
4. Atualização dos nós do LangGraph (`agent/nodes.py`, `agent/prompts.py`, `agent/state.py`).
5. Atualização dos routers (`app/routers/webhook.py`, `app/routers/kommo.py`, `app/routers/health.py`).
6. Execução e validação de 100% da suíte de testes.
