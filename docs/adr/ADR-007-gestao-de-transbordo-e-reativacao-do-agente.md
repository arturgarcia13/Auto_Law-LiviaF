# ADR-007: Gestão de Transbordo Humano e Ciclo de Reativação do Agente

* **Status**: Aceito
* **Data**: 2026-08-27
* **Decisores**: Desenvolvedor / Arquiteto do Projeto
* **Contexto Técnico**: Gestão de Exceções, Intervenção Humana e Sincronização CRM

---

## 1. Contexto e Problema

Na advocacia trabalhista, existem situações delicadas e de elevado risco jurídico que exigem intervenção humana imediata e sensibilidade jurídica que não devem ser delegadas integralmente à IA. Exemplos:
- Acidente de trabalho com lesão grave ou morte.
- Assédio moral grave ou assédio sexual.
- Casos com processo judicial já ajuizado por outro patrono.
- Lead solicitando explicitamente atendimento com advogado humano.
- Cenários atípicos que fogem do escopo de triagem padrão.

Quando um lead se enquadra em tais condições, o sistema deve:
1. Notificar a equipe jurídica com urgência.
2. Silenciar o bot imediatamente para evitar que a IA continue respondendo enquanto um humano conversa com o cliente no WhatsApp.
3. Permitir que o bot volte a atender aquele número caso o atendimento humano seja concluído ou o lead retorne no futuro.

---

## 2. Alternativas Consideradas

### Opção A: Desconexão da Instância WhatsApp
- Desconectar a instância do WhatsApp para que o advogado utilize o WhatsApp Web tradicional.
- **Prós**: O bot é forçadamente desligado.
- **Contras**: Inviável operacionalmente, pois paralisa o atendimento automático de todos os outros leads simultâneos do escritório.

### Opção B: Flag no Banco Redis sem Integração com o Grafo
- Gravar uma chave temporária no Redis com TTL para ignorar mensagens daquele número.
- **Prós**: Simples de implementar no webhook inicial.
- **Contras**: Desacoplado do estado histórico do lead; difícil controle de reativação sem expiração arbitrária de tempo.

### Opção C: Estado de Transbordo no LangGraph + Webhook Bidirecional no CRM
- Implementar o controle de transbordo diretamente no `LeadState` do LangGraph através da flag `humano_ativo: bool`.
- O roteador principal do grafo verifica a flag e desvia a execução para `END` (sem resposta) caso esteja ativa.
- A reativação é orientada a eventos: o Kommo CRM envia um webhook quando o advogado conclui a tarefa ou move o lead de etapa, sinalizando à API para reativar o bot.
- Disponibilizar rota administrativa segura (`POST /admin/conversation/{tel}/reativar-bot`) para liberação manual.

---

## 3. Decisão

Adotou-se a **Opção C: Estado no LangGraph + Tarefa no Kommo + Webhook de Reativação**.

### Fluxo de Transbordo (Bot -> Humano)
1. A LLM identifica o gatilho de transbordo e aciona a tool `acionar_transbordo`.
2. O nó `transbordo_node` executa:
   - Criação de tarefa urgente no Kommo com prazo de 2 horas e descrição do motivo.
   - Atualização da etapa do lead no Kommo para `"Transbordo"`.
   - Envio de mensagem empática ao lead avisando que um especialista do escritório assumirá o atendimento em breve.
   - Atualização do estado com `humano_ativo: True`.
3. A partir desse instante, qualquer nova mensagem enviada pelo lead é interceptada pelo roteador do LangGraph e descartada (o bot permanece em silêncio).

### Fluxo de Reativação (Humano -> Bot)
1. O advogado atende o lead e finaliza a tarefa no Kommo CRM ou move o lead para outra etapa do funil.
2. O Kommo dispara webhook para `POST /webhook/kommo`.
3. O endpoint valida o evento (`task_completed` ou `status_lead`) e invoca `graph.aupdate_state(config, {"humano_ativo": False})`.
4. O bot volta a estar habilitado para dialogar com o lead caso este envie novas interações.

---

## 4. Consequências

### Positivas
- **Segurança Jurídica**: Nenhuma resposta inapropriada é gerada em situações de vulnerabilidade ou litígio complexo.
- **Não Concorrência**: O advogado tem liberdade para conversar no mesmo WhatsApp sem disputa de mensagens com a IA.
- **Fechamento do Ciclo**: A reativação do bot é automática após o término do trabalho do advogado, sem necessidade de suporte técnico.

### Negativas / Riscos Mitigados
- **Dependência de Webhook do CRM**: Exige que o plano do Kommo CRM suporte webhooks globais (plano Advanced+). *Mitigação*: Criação de rota administrativa manual (`POST /admin/conversation/{tel}/reativar-bot`) para reativação imediata via painel ou chamada HTTP.
