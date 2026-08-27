# ADR-005: Integração ZapSign — Disparo de Link via Evolution API

* **Status**: Aceito
* **Data**: 2026-08-27
* **Decisores**: Desenvolvedor / Arquiteto do Projeto
* **Contexto Técnico**: Automação de Assinatura Eletrônica de Contratos de Honorários e Procurações

---

## 1. Contexto e Problema

Após o lead fornecer os dados pessoais (nome, CPF, RG, endereço, profissão, empresa reclamada) na fase de coleta pelo agente de IA, a aplicação deve preencher a minuta contratual de honorários advocatícios e procuração na plataforma **ZapSign**.

A API da ZapSign (`POST /api/v1/models/create-doc/`) disponibiliza o parâmetro booleano `send_automatic_whatsapp`.
- Quando configurado como `true`, a própria infraestrutura da ZapSign dispara a mensagem no WhatsApp do signatário.
- **Impacto Financeiro**: A ZapSign fatura uma tarifa adicional de **R$ 0,50 por disparo de WhatsApp** além do plano de assinaturas contratado.
- Além do custo financeiro, a mensagem enviada pela ZapSign segue um template genérico e rígido, impossibilitando personalização de tom de voz ou alinhamento com a identidade do escritório da Dra. Lívia França.

---

## 2. Alternativas Consideradas

### Opção A: Utilizar `send_automatic_whatsapp: true`
- Deixar a ZapSign gerenciar o envio do link de assinatura pelo WhatsApp.
- **Prós**: Uma linha a menos de código no backend.
- **Contras**: Custo financeiro cumulativo (R$ 0,50 por lead que recebe contrato); mensagem impessoal; perda de rastreabilidade unificada da conversa dentro da mesma sessão de WhatsApp.

### Opção B: `send_automatic_whatsapp: false` + Envio via Evolution API
- Criar o documento na ZapSign apenas para obter o token e o link do signatário (`sign_url` / `open_id`).
- A própria aplicação envia a mensagem no WhatsApp do cliente via Evolution API contendo o link de assinatura.
- **Prós**:
  - **Custo Zero Adicional**: Elimina a cobrança de R$ 0,50 por contrato enviado.
  - **Experiência do Cliente Fluida**: O link chega na mesma conversa onde o lead acabou de falar com a IA, sem troca de número ou estranhamento.
  - **Total Customização da Mensagem**: O escritório define a redação exata, emojis e instruções de assinatura.
  - **Rastreabilidade**: O envio do link vira um span rastreado no Langfuse.
- **Contras**: Requer que o nó do grafo execute duas chamadas encadeadas (`zapsign.criar_documento` -> `evolution.enviar_texto`).

---

## 3. Decisão

Adotou-se a **Opção B: `send_automatic_whatsapp: false` com envio do link via Evolution API**.

Fluxo implementado no nó `gerar_contrato_node`:
1. Valida os dados coletados com schema Pydantic.
2. Faz requisição à API ZapSign preenchendo as variáveis de template (`{{NOME}}`, `{{CPF}}`, `{{RG}}`, `{{ENDERECO}}`, etc.) com `send_automatic_whatsapp: false`.
3. Armazena o `token` do documento no Redis associado ao número do lead (`zapsign:{doc_token} -> telefone`).
4. Dispara mensagem via `evolution.enviar_texto` contendo o link de assinatura (`sign_url`).
5. Transiciona o estado do lead no LangGraph para `"aguardando_assinatura"`.

---

## 4. Consequências

### Positivas
- **Economia Recorrente**: Redução de despesas operacionais do escritório.
- **Humanização do Atendimento**: O contrato é entregue como uma continuação natural da conversa com a assistente jurídica virtual.
- **Governança**: Registro do link e token nos campos customizados do Kommo CRM.

### Negativas / Riscos Mitigados
- **Tratamento de Falha de Envio**: Se a Evolution API falhar no momento do envio, o documento já terá sido criado na ZapSign. *Mitigação*: Tratamento de exceção com retry e registro de erro auditável no Langfuse.
