# ADR-001: Escolha do Orquestrador de Agente de IA (LangGraph vs. n8n)

* **Status**: Aceito
* **Data**: 2026-08-27
* **Decisores**: Desenvolvedor / Arquiteto do Projeto
* **Contexto Técnico**: Automação Comercial e Contratual — Advocacia Trabalhista (Dra. Lívia França)

---

## 1. Contexto e Problema

O projeto tem como objetivo automatizar o fluxo comercial e contratual de um escritório de advocacia trabalhista, atendendo leads que chegam via anúncios no WhatsApp, qualificando os casos (tempo de serviço, vínculo de emprego, carteira assinada, motivos da rescisão, provas), coletando dados pessoais para o contrato de honorários, gerando a minuta no ZapSign para assinatura eletrônica e, após assinatura, cadastrando o cliente e o processo no ADVBOX e no Kommo CRM.

O fluxo conversacional é **altamente dependente de estado (stateful)** e não linear:
- O agente precisa saber em qual estágio da triagem o lead está.
- Precisa pausar ou mudar de rota caso o lead traga um caso atípico ou urgente (acidente grave, assédio).
- Precisa pausar o atendimento automático quando um advogado humano assume (transbordo) e poder retomar se necessário.
- O desenvolvedor responsável domina a linguagem Python e precisa de rastreabilidade e observabilidade detalhada (Langfuse) para analisar custos de tokens, latência e comportamento do modelo (Google Gemini).

Inicialmente, a proposta arquitetural previa o **n8n** como orquestrador geral (low-code). Entretanto, questionou-se a viabilidade e conveniência de utilizar **LangGraph + FastAPI** em Python puro.

---

## 2. Alternativas Consideradas

### Opção A: n8n Puro
- Utilizar nós do n8n (AI Agent Node, Webhooks, Community Nodes de Kommo e ADVBOX).
- **Prós**: Interface visual drag-and-drop; rápida prototipagem de integrações simples; acessível para manutenções superficiais por equipes não-técnicas.
- **Contras**: Abstração opaca do AI Agent (caixa preta); persistência de estado conversacional complexa (workarounds com Redis/variáveis); difícil implementação de interrupções condicionais e controle fino de loops; observabilidade limitada de spans internos de LLM no Langfuse.

### Opção B: LangGraph + FastAPI (Puro Python)
- Desenvolver a aplicação sobre FastAPI com motor de agente baseado em LangGraph (`StateGraph`), checkpoints no PostgreSQL (`AsyncPostgresSaver`) e integração direta com o Google Gemini.
- **Prós**:
  - Controle determinístico e total sobre a máquina de estados e transições (`triagem` -> `coleta` -> `gerar_contrato` -> `pos_assinatura`).
  - Suporte nativo a interrupções (`interrupt_before`) e flags de transbordo humano (`humano_ativo`).
  - Integração nativa e profunda com **Langfuse** via `CallbackHandler` e decorators `@observe` (tracing de cada nó, prompt, resposta e tool call).
  - Versionamento completo de código no Git, facilidade de testes unitários automatizados (TDD com `pytest-asyncio`).
  - Eliminação de dependência e custos de licença/hospedagem de uma plataforma low-code de terceiros.
- **Contras**: Requer codificação manual dos endpoints e wrappers HTTP das APIs (Kommo, ZapSign, ADVBOX, Evolution API); requer gerenciamento de tarefas assíncronas/scheduler via Python (APScheduler).

### Opção C: Abordagem Híbrida (LangGraph como motor de IA + n8n para integrações)
- LangGraph exposto como API HTTP para raciocínio do agente, e n8n consumindo essa API para disparar integrações com CRM, ZapSign e WhatsApp.
- **Prós**: Junção de IA controlada com integrações visuais.
- **Contras**: Latência adicional de rede (WhatsApp -> Evolution -> n8n -> FastAPI -> LangGraph -> FastAPI -> n8n -> WhatsApp); dois ambientes operacionais complexos para manter em infraestrutura; ganho nulo dado que o time de desenvolvimento é 100% técnico.

---

## 3. Decisão

Adotou-se a **Opção B: LangGraph + FastAPI (Python puro)**.

A escolha fundamenta-se no fato de que o núcleo deste projeto não é uma simples automação de disparos, mas sim uma **gestão complexa de estado conversacional e decisão jurídica**. Como o mantenedor é programador Python e exige observabilidade de ponta com Langfuse, o LangGraph entrega controle fino, tipagem com Pydantic/TypedDict, testabilidade com mocks e zero custo de licença de terceiros.

---

## 4. Consequências

### Positivas
- **Controle Fino de Fluxo**: Mapeamento explícito de estados (`LeadState`) com transições condicionais puras.
- **Observabilidade Completa**: Cada mensagem, chamada de LLM, custo e execução de tool é monitorada diretamente no Langfuse.
- **Testabilidade**: Cada nó do grafo e cada router da API podem ser testados de forma determinística e isolada com `pytest`.
- **Arquitetura Enxuta**: Menos componentes de software rodando na VPS/ambiente local.

### Negativas / Riscos Mitigados
- **Boilerplate Inicial**: Necessidade de criar schemas Pydantic e clientes assíncronos (`httpx`) para Kommo, ZapSign, ADVBOX e Evolution API. *Mitigação*: Desenvolvimento orientado a testes (TDD) em sprints incrementais.
- **Scheduler**: Necessidade de agendador interno para lembretes de contratos não assinados. *Mitigação*: Utilização do `APScheduler` acoplado ao lifespan do FastAPI.
