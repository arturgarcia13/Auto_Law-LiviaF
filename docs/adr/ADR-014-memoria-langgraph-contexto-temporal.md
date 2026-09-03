# ADR-014: Persistência de Memória Conversacional do LangGraph e Injeção de Contexto Temporal

## 📌 Status
**Aceito** (2026-09-02)

---

## 🏛️ Contexto e Problema
Na análise das respostas geradas pelo agente inteligente durante conversas no WhatsApp, observou-se:
1. **Amnésia entre Turnos Conversacionais**: A cada nova mensagem enviada pelo usuário, o agente recebia apenas a mensagem mais recente (`Enviando histórico de 1 mensagens...`), perdendo o contexto do que fora conversado anteriormente. Isso impedia a condução lógica da qualificação jurídica (17 campos da ficha trabalhista).
2. **Ausência de Checkpointer Ativo**: Em ambientes de desenvolvimento sem PostgreSQL rodando, o checkpointer padrão ficava `None`, impedindo o StateGraph de acumular estados entre turnos.
3. **Substituição Destrutiva de Mensagens**: No `LeadState`, o campo `messages: list[Any]` sofria sobrescrita direta a cada ciclo em vez de acúmulo (append).
4. **Alucinação Temporal do Modelo**: Ao ser questionado sobre datas (*"Sabe me dizer que dia é hoje?"*), o Gemini emitia placeholders como `[inserir data de hoje]` ou inferia datas erradas do passado (2025).

---

## 🎯 Decisão
1. **Acúmulo Determinístico de Mensagens via `add_messages`**:
   - Atualização da tipagem em [`agent/state.py`](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/agent/state.py):
     ```python
     from typing import Annotated
     from langgraph.graph.message import add_messages

     class LeadState(TypedDict, total=False):
         messages: Annotated[list[Any], add_messages]
         ...
     ```
2. **Checkpointer Persistente em Disco (`AsyncSqliteSaver` / SQLite)**:
   - Configuração no ciclo de vida assíncrono da aplicação ([`app/main.py`](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/app/main.py)): sempre que PostgreSQL não estiver conectado, instancia `AsyncSqliteSaver.from_conn_string("data/checkpoints.sqlite")` (com fallback seguro para `MemorySaver`).
   - Armazena as threads, snapshots e mensagens diretamente no arquivo SQLite `data/checkpoints.sqlite`.
   - Garante que a conversa **não seja esquecida** mesmo se o Uvicorn sofrer reload de código ou se o servidor for reiniciado.
3. **Injeção Dinâmica de Data/Hora no Prompt do Gemini ([`agent/nodes.py`](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/agent/nodes.py))**:
   - Criação da função `formatar_data_brasil()` gerando data/hora real no fuso de Brasília (`America/Sao_Paulo`), ex: *"quarta-feira, 02 de setembro de 2026, às 22:15"*.
   - Injeção dessa string na instrução de sistema (`system_instruction`) do Gemini Flash.
   - Proibição terminante de emissão de placeholders entre colchetes (`[data]`, `[inserir data de hoje]`).

---

## 🚀 Consequências

### Benefícios
- **Continuidade Conversacional Completa e Persistente**: O agente lembra de todas as respostas e dados fornecidos pelo cliente em turnos anteriores, permitindo avançar naturalmente pelos 17 campos da triagem trabalhista sem perda de contexto entre reloads.
- **Precisão Temporal**: O agente tem consciência do dia da semana, mês, ano e hora exatos, respondendo perguntas temporais sem alucinações.
- **Independência e Sobrevivência a Falhas**: O `AsyncSqliteSaver` mantém a persistência integral do histórico em arquivo local sem necessidade de levantar container Docker do PostgreSQL.
- **Transição Transparente para Produção**: Quando o PostgreSQL estiver conectado via `DATABASE_URL`, o sistema conecta-se ao `AsyncPostgresSaver` sem alteração de contratos no código do agente.
