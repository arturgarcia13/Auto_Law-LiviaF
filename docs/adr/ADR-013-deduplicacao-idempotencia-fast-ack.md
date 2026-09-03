# ADR-013: Deduplicação de Mensagens (Idempotência) e Fast ACK para Webhooks de CRM

## 📌 Status
**Aceito** (2026-09-02)

---

## 🏛️ Contexto e Problema
Durante a operação de integração com a Kommo CRM e WhatsApp em tempo real, constatou-se um problema grave de **mensagens duplicadas/em rajada**:
1. **Retentativas por Timeout**: O webhook da Kommo possui um timeout restrito (de aproximadamente 2 a 4 segundos). Como a aplicação executava o fluxo de forma síncrona (consulta de contato no CRM + LangGraph + inferência do Gemini + envio via Meta API + registro de nota no lead = 6 a 8 segundos), a Kommo considerava a entrega como falha ou sem resposta.
2. **Avalanche de Retentativas de Múltiplos IPs**: A fila da Kommo redisparava as mensagens pendentes a partir de outros IPs de workers (`142.0.204.92`, `173.233.147.83`, `204.74.253.164`), acumulando eventos de turnos anteriores.
3. **Falta de Idempotência**: O backend processava cada requisição recebida como um novo evento, chamando a IA e enviando 4 a 5 respostas consecutivas para o mesmo cliente no WhatsApp.
4. **Disparo Concorrente de Eventos**: Cada interação no CRM dispara simultaneamente eventos de `message.add`, `leads.update` e `unsorted.update`.

---

## 🎯 Decisão
1. **Idempotência em Dois Níveis (L1 RAM + L2 SQLite)**:
   - Criação do serviço singleton [`MessageDeduplicator`](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/app/services/deduplication.py) combinando cache em memória RAM (**L1**) e banco SQLite persistente em disco em `data/deduplication.sqlite` (**L2**) em modo WAL.
   - Mesmo que o servidor sofra *reloads* de desenvolvimento (`--reload`) ou seja reiniciado, o banco SQLite preserva o histórico de IDs processados e seus prazos de expiração TTL (15 minutos).
   - Extração do identificador oficial da mensagem no Kommo (`message_id = item.get("id")`) e cálculo de hash SHA-256 sobre a tupla `(chat_id, texto, timestamp)`.
   - Mensagens com ID já registrado ou em processamento são descartadas imediatamente com status `duplicate_message` e log explicativo `⏭️ [MENSAGEM DUPLICADA IGNORADA]`.
2. **Dupla Barreira de Proteção**:
   - **Barreira Externa (`POST /kommo/webhook`)**: Validação de duplicidade antecipada com reserva imediata no SQLite antes de agendar a tarefa de background.
   - **Barreira Interna (`processar_mensagem_kommo`)**: Nova verificação atômica no início da execução para interceptar chamadas diretas ou retries disparados fora da rota principal.
3. **Fast ACK (Resposta HTTP 200 Imediata)**:
   - No endpoint `POST /kommo/webhook`, a aplicação valida o token de segurança, executa o filtro de duplicidade e devolve `HTTP 200 OK` para a Kommo em **menos de 50 milissegundos**.
   - O processamento da IA (LangGraph + Gemini) e o disparo da mensagem no WhatsApp (Meta Cloud API) são despachados de forma assíncrona em segundo plano via `asyncio.create_task`.
   - A Kommo recebe confirmação instantânea de entrega com sucesso, eliminando os gatilhos de retentativa da fila de CRM.

---

## 🚀 Consequências

### Benefícios
- **Fim Definitivo das Mensagens Repetidas**: Apenas a primeira ocorrência de uma mensagem é processada; clones e retentativas tardias de IPs de retry (ex: `173.233.147.83`) são sumariamente silenciados pelo banco SQLite.
- **Imunidade a Reloads e Reinicializações**: O estado de deduplicação não se perde quando arquivos são alterados ou quando o Uvicorn reinicia seus workers.
- **Resiliência a Picos e Conexões Lentas**: O servidor nunca sofre timeout da Kommo, garantindo que o webhook permaneça verde e saudável.
- **Isolamento de Falhas**: Exceções no envio para a Meta API ou na geração da IA não quebram o handshake HTTP com o CRM.
- **Auditoria Transparente**: Logs claros identificam mensagens genuínas versus descartadas por deduplicação.

### Riscos e Mitigações
- **Concorrência em Arquivo SQLite**:
  - *Mitigação*: Ativação do modo WAL (`PRAGMA journal_mode=WAL;`), timeout de 10s e sincronização por `threading.Lock` para garantir consistência entre múltiplos acessos assíncronos.
- **Crescimento do Arquivo de Deduplicação**:
  - *Mitigação*: Limpeza automática e periódica (`DELETE FROM processed_keys WHERE expires_at <= ?`) a cada operação.
