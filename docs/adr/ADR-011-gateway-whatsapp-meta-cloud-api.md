# ADR-011: Gateway WhatsApp via Meta Cloud API e Sincronização Kommo CRM

## 📌 Status
**Aceito** (2026-09-02) — Substitui [ADR-008](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-008-gateway-kommo-chats.md) e [ADR-010](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/docs/adr/ADR-010-lista-permissao-ambiente-testes-allowed-chat-ids.md)

---

## 🏛️ Contexto e Problema
A arquitetura anterior dependia da API de Conversas do Kommo (*Chats/Talks API - amojo*) para envio de mensagens, o que apresentava limitações na emissão de mensagens ativas e templates HSM pré-aprovados pela Meta. Além disso, havia necessidade de:
1. Envio de alta performance e rastreabilidade com o identificador de mensagem (`wamid`) da Meta.
2. Manter o Kommo CRM como centro de operações jurídicas (leads, etapas, tarefas e timeline).
3. Proteção e simplicidade no controle de ambiente de testes por número de telefone (`ALLOWED_PHONES`).
4. Proteção contra exposição pública de rotas de disparo manual (`POST /send`).
5. Eliminação definitiva de serviços externos de assinatura digital (ex: ZapSign), priorizando a criação de tarefas no CRM para os advogados enviarem minutas personalizadas.

---

## 🎯 Decisão
1. **Gateway WhatsApp Oficial**: Adoção direta da **Meta WhatsApp Cloud API (Graph API)** para disparos de texto e templates HSM (`v21.0`/`v26.0`).
2. **Sincronização com Kommo CRM**: Toda mensagem enviada pela IA é registrada na timeline do lead no Kommo (`/api/v4/leads/{lead_id}/notes`) contendo o texto e o `wamid`.
3. **Segurança do Endpoint `/send`**: Protegido por autenticação via token (`KOMMO_WEBHOOK_SECRET` ou `ADMIN_SECRET_TOKEN`).
4. **Filtro Simplificado por Telefone (`ALLOWED_PHONES`)**: Substituição de regras mistas de chat/lead por validação única de números de telefone com DDI/DDD.
5. **Fluxo Contratual com Tarefas Humanas**: Ao término da qualificação e aceite de honorários, o sistema gera uma tarefa de urgência para a equipe de advogados no Kommo CRM e silencia o agente (`humano_ativo = True`).

---

## 🚀 Consequências

### Benefícios
- **Alta Disponibilidade e Velocidade**: Envio direto através da infraestrutura oficial da Meta com suporte a templates aprovados.
- **Rastreabilidade Ponta a Ponta**: Cada mensagem entregue possui `wamid` registrado na timeline do Kommo.
- **Segurança Reforçada**: Rotas de disparo e webhook protegidas por tokens de autenticação.
- **Facilidade de Testes**: Configuração direta de números em `ALLOWED_PHONES`.
- **Zero Custos Extras de Assinatura**: Gestão centralizada no Kommo CRM sem necessidade de ferramentas terceiras como ZapSign.
