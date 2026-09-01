# ADR-010: Lista de Permissão de Mensageria em Ambientes de Teste (`ALLOWED_CHAT_IDS`)

> **Status**: Aceito  
> **Data**: 2026-08-31  
> **Autor**: Dra. Lívia França / Auto_Law Core Engineering  
> **Contexto**: Segurança Operacional, Homologação e Isolamento de Tráfego no WhatsApp do Kommo CRM.

---

## 1. Contexto e Problema

Durante as etapas de desenvolvimento, testes de integração e homologação de novas personas conversacionais, o webhook do Kommo CRM (`/webhook/kommo`) fica conectado ao ambiente do escritório de advocacia da **Dra. Lívia França**.

Nesse cenário, leads e clientes reais continuam enviando mensagens no WhatsApp do escritório diariamente. Caso o backend de testes processe todas as mensagens indiscriminadamente, clientes reais poderiam receber respostas automáticas de versões experimentais da IA, gerando:
1. Risco ético e constrangimento com clientes reais do escritório.
2. Consumo desnecessário de tokens de LLM (Gemini Flash) e infraestrutura.
3. Poluição do banco de dados de checkpoints de estado com threads de pessoas reais.

Era necessário um mecanismo simples, seguro, desacoplado e de fácil ativação para **garantir que apenas os chats ou números de telefone autorizados para testes sejam respondidos pela automação**.

---

## 2. Alternativas Consideradas

### Alternativa 1: Desconectar o Webhook da Kommo durante os testes
- ❌ **Desvantagem**: Impede a realização de testes ponta a ponta (E2E) com o tráfego real emitido pela API de conversas do Kommo CRM.

### Alternativa 2: Criar uma conta de teste secundária no Kommo CRM
- ❌ **Desvantagem**: Custo financeiro adicional de licenciamento no CRM e necessidade de duplicar todas as configurações de pipeline (`14107071`) e modelos de mensagens.

### Alternativa 3: Filtro de Lista de Permissão via Variável de Ambiente (`ALLOWED_CHAT_IDS`)
- ✅ **Vantagem**: Descarte precoce logo na entrada do router FastAPI (`/webhook/kommo` e `/webhook/message`).
- ✅ **Vantagem**: Permite configurar um único ID de chat (ex: `20429066`), uma lista de múltiplos IDs ou números de telefone separados por vírgula (`20429066,20429067,5511999999999`).
- ✅ **Vantagem**: Para liberação total em ambiente de produção, basta deixar a variável vazia ou como `*`.
- ✅ **Vantagem**: Zero impacto de performance (checagem em $O(1)$ via `set` em memória).

---

## 3. Decisão

Adotamos a **Alternativa 3** como padrão arquitetural do projeto Auto_Law.

### Regras de Funcionamento do Filtro:
1. **Configuração no `.env`**:
   ```env
   # Para limitar a um único chat de teste:
   ALLOWED_CHAT_IDS=20429066

   # Para lista de permissão com múltiplos chats e telefones:
   ALLOWED_CHAT_IDS=20429066,20429067,5511999999999

   # Para ambiente de produção (permite todos os clientes):
   ALLOWED_CHAT_IDS=*
   ```

2. **Interceptação no Router (`app/schemas/kommo.py` e `app/routers/kommo.py`)**:
   - A função `is_chat_permitido(chat_id, talk_id, telefone)` é executada antes de qualquer processamento de áudio, agregação em Redis ou chamada ao LangGraph.
   - Caso o identificador não pertença à lista de permissão, o evento é descartado imediatamente:
     ```json
     {
       "status": "ignored",
       "reason": "chat_not_in_allowlist",
       "chat_id": "999999",
       "telefone": "5585999999999"
     }
     ```
   - Um log informativo em nível `INFO` é registrado para auditoria sem gerar ruído ou erros.

---

## 4. Consequências

### Positivas:
- **Blindagem Operacional**: Impossibilidade de o bot responder acidentalmente a clientes reais durante homologação local.
- **Economia de Recursos**: Requisições de clientes fora da lista são descartadas antes de chamar APIs externas (Gemini STT e LLM).
- **Flexibilidade**: Facilidade de adicionar desenvolvedores e advogados à lista de teste apenas editando o arquivo `.env`.

### Negativas / Riscos Mitigados:
- **Risco de Esquecimento em Produção**: Ao realizar o deploy final em produção, o operador poderia esquecer de alterar `ALLOWED_CHAT_IDS`.
  - *Mitigação*: Logs explícitos na inicialização e template padrão no `.env.example` com comentários instruindo a desativação do filtro para produção (`ALLOWED_CHAT_IDS=*`).
