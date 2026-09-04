# ADR-015: Migração da Camada de Inteligência Conversacional para ChatOllama (Cluster AtLab UFC)

## 📌 Status
**Aceito** (2026-09-03)

---

## 🏛️ Contexto e Problema
Originalmente, o agente conversacional de triagem e qualificação jurídica da Dra. Lívia França utilizava a API pública do Google Gemini (`google.genai` Client). Embora funcional, essa dependência apresentava pontos de atenção:
1. **Soberania de Dados e Privacidade Jurídica**: Conversas contendo relatos trabalhistas sensíveis eram enviadas para servidores de terceiros (Google).
2. **Instabilidade de Ciclo de Vida de Modelos Cloud**: Versões de modelos são frequentemente depreciadas sem aviso prévio (ex: descontinuação de `gemini-2.5-flash-lite`).
3. **Disponibilidade de Infraestrutura Própria de Alto Desempenho**: O laboratório AtLab/UFC disponibilizou um cluster institucional com GPUs dedicadas e servidor Ollama (`https://cumbuco.ollama.atlab.ufc.br/ollama`), autenticado via Bearer Token e com modelos de última geração em português brasileiro (`llama3.1:8b`, `qwen2.5:14b`, `llama3.2:latest`, etc.).
4. **Alinhamento com LangChain e Langfuse**: A integração via `google.genai` exigia tratamento manual de histórico e formatos de mensagens, enquanto o ecossistema LangChain (`ChatOllama` / `langchain-ollama`) oferece integração nativa com callbacks do Langfuse e interfaces `ainvoke` assíncronas padrão.

---

## 🎯 Decisão
1. **Adoção do `langchain-ollama` com `ChatOllama`**:
   - Integração da classe oficial `ChatOllama` no nó conversacional `agent/nodes.py`.
   - Criação da factory `_build_chat_model()` que lê as credenciais e parâmetros dedicados do `.env`:
     - `OLLAMA_BASE_URL`: Endpoint do cluster (`https://cumbuco.ollama.atlab.ufc.br/ollama`).
     - `OLLAMA_API_KEY`: Token de autorização Bearer (`sk-...`).
     - `OLLAMA_MODEL`: Modelo padrão selecionado (`llama3.1:8b`).
     - `OLLAMA_TEMPERATURE`: `0.4` (equilíbrio ideal entre empatia e precisão jurídica).
     - `OLLAMA_TOP_K`: `40`.
     - `OLLAMA_KEEP_ALIVE`: `10m` (mantém o modelo aquecido na VRAM do cluster).
2. **Mensagens Nativas LangChain**:
   - Utilização das classes `SystemMessage`, `HumanMessage` e `AIMessage` de `langchain_core.messages` para alimentar o modelo.
   - Preservação da injeção dinâmica de data/hora oficial de Brasília (`formatar_data_brasil()`) para garantir rigor temporal no atendimento.
3. **Resiliência e Degradação Graciosa**:
   - Se o Ollama estiver indisponível ou sofrer timeout, o sistema tenta o cliente Gemini como fallback secundário.
   - Caso ambos estejam inacessíveis, emite a mensagem de acolhimento padrão da Dra. Lívia França, garantindo que o lead nunca fique sem resposta.
4. **Isolamento de Áudio (STT)**:
   - A rota de transcrição de áudio do WhatsApp (`app/services/audio.py`) é mantida no Google Gemini multimodal até a eventual incorporação de um serviço Whisper local.

---

## 🚀 Consequências

### Benefícios
- **Soberania e Privacidade Total**: O tráfego de mensagens passa pelo cluster institucional, sem compartilhamento com APIs comerciais externas de terceiros.
- **Desempenho e Latência**: Respostas em ~2 segundos com o modelo `llama3.1:8b`.
- **Flexibilidade de Modelos**: Permite alternar entre `llama3.1:8b`, `qwen2.5:14b` ou `llama3.2:latest` apenas alterando `OLLAMA_MODEL` no `.env`, sem alterar código.
- **Observabilidade Transparente**: `ChatOllama` se integra nativamente ao Langfuse via LangChain Callbacks sem necessidade de código extra de instrumentação.

### Riscos e Mitigações
- **Dependência de Conexão com o Cluster UFC**: O endpoint requer conectividade com a rede institucional.
  - *Mitigação*: Implementado fallback em camadas (Ollama -> Gemini -> Mensagem padrão acolhedora de contingência).
