# ADR-008: Gateway WhatsApp via API de Conversas do Kommo CRM (em substituição à Evolution API)

## 📌 Status
**Aceito** (2026-08-31) — Substitui [ADR-002](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-002-gateway-whatsapp-evolution-baileys.md)

---

## 🏛️ Contexto e Problema
Inicialmente, o projeto planejava utilizar a **Evolution API (Baileys/QR Code)** rodando em container Docker local para recepcionar e enviar mensagens de WhatsApp.

No entanto, com a evolução da operação comercial da Dra. Lívia França:
1. O **Kommo CRM** já possui canais de mensageria conectados e integrados diretamente ao WhatsApp.
2. Manter uma instância separada da Evolution API adiciona complexidade operacional (gerenciamento de sessão, reconexão de QR Code, consumo extra de RAM e monitoramento de container).
3. Centralizar todas as conversas nativamente dentro do Kommo permite que a equipe jurídica acompanhe o histórico em tempo real na interface do CRM, intervindo diretamente quando necessário sem dessincronização de mensagens.

---

## ⚖️ Alternativas Consideradas

| Alternativa | Prós | Contras |
|---|---|---|
| **A. Evolution API (Baileys)** | Controle de baixo nível sobre a conexão WhatsApp. | Sobrecarga de infraestrutura (container adicional, banco `evolution_db`, risco de desconexão de QR Code). |
| **B. Kommo CRM (Chats / Talks API)** | ✅ Zero infraestrutura extra de WhatsApp.<br>✅ Histórico nativo no CRM para visualização dos advogados.<br>✅ Transbordo humano perfeito dentro da mesma janela de chat. | Depende da API do Kommo para entrega de mensagens. |

---

## 🎯 Decisão
Adotar a **API de Conversas do Kommo CRM (Talks / Chats API)** como canal unificado de recepção e envio de mensagens WhatsApp.
- O endpoint `/webhook/kommo` passa a ser o ponto único de entrada para eventos de mensagens e funil.
- As respostas geradas pelo agente LangGraph são enviadas através de requisições autenticadas para o endpoint de mensagens do Kommo.
- A dependência e o container da Evolution API são descontinuados da stack principal.

---

## 🚀 Consequências

### Benefícios
- **Redução de Custo e Complexidade**: Menos 1 container e 1 base de dados na infraestrutura local/produção.
- **Unificação Operacional**: Todas as mensagens, notas, dados do lead e tarefas ficam agrupadas na mesma timeline no Kommo CRM.
- **Transbordo Fluido**: O advogado pode assumir o atendimento diretamente na tela do Kommo.

### Riscos e Mitigações
- **Taxa de Limite de Requisições (Rate Limits) do Kommo**: Implementação de retry exponencial assíncrono com `httpx` e `tenacity`.
