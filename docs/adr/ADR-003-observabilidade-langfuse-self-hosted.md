# ADR-003: Observabilidade e Tracing LLM — Langfuse Self-Hosted

* **Status**: Aceito
* **Data**: 2026-08-27
* **Decisores**: Desenvolvedor / Arquiteto do Projeto
* **Contexto Técnico**: Observabilidade, Auditoria e Tracing de Agentes de IA

---

## 1. Contexto e Problema

O agente conversacional atuará na triagem de potenciais clientes e na coleta de dados pessoais sensíveis (CPF, RG, endereço, salário, relatos trabalhistas). Para garantir confiabilidade, controle de custos e governança sobre o modelo (Google Gemini), é mandatório dispor de:
- Tracing detalhado de cada execução do grafo (cada nó percorrido, latência de cada etapa).
- Monitoramento de consumo e custo de tokens por conversa.
- Inspeção de entradas, saídas e eventuais alucinações da LLM.
- Auditoria do histórico de tool calls (atualizações no Kommo, chamadas ao ZapSign e ADVBOX).
- Privacidade e sigilo advocatício rigoroso (conformidade com LGPD e normas da OAB).

Avaliamos o uso do **Langfuse Cloud** (SaaS) versus o **Langfuse Self-Hosted** (hospedado na própria infraestrutura do projeto).

---

## 2. Alternativas Consideradas

### Opção A: Langfuse Cloud (SaaS)
- Utilizar a plataforma gerenciada em `cloud.langfuse.com`.
- **Prós**: Zero consumo de memória ou processamento no servidor local/VPS; sem necessidade de configurar containers adicionais.
- **Contras**:
  - Envio de dados sensíveis de leads trabalhistas para servidores de terceiros no exterior.
  - Limite gratuito de 50.000 observações por mês; custos recorrentes em escala.
  - Dependência de conectividade externa de saída para registro de cada span.

### Opção B: Langfuse Self-Hosted (Docker)
- Executar a imagem oficial `ghcr.io/langfuse/langfuse:latest` localmente via Docker Compose e na VPS de produção.
- **Prós**:
  - **Soberania Absoluta dos Dados**: Nenhuma informação dos leads ou prompts trafega para serviços SaaS de observabilidade.
  - **Sem Limites de Volume**: Sem teto de observações ou cobranças adicionais por tráfego.
  - **Comunicação Local de Baixa Latência**: A API FastAPI comunica-se diretamente pela rede interna Docker (`http://langfuse:3000`).
  - **Auditoria Interna**: Banco de dados sob controle exclusivo do projeto.
- **Contras**:
  - Requer alocação de aproximadamente 1 GB de memória RAM na infraestrutura.
  - Necessidade de gerenciar chaves de criptografia (`NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY`) e backup da base.

---

## 3. Decisão

Adotou-se a **Opção B: Langfuse Self-Hosted**, rodando em container Docker dedicado tanto no ambiente local (`docker-compose.local.yml`) quanto na VPS de produção.

A base de dados do Langfuse utilizará uma database dedicada (`langfuse`) dentro do mesmo container PostgreSQL do projeto (conforme ADR-004), com timezone padronizado em `UTC`.

A integração no código Python será feita através do `langfuse.callback.CallbackHandler` passado na configuração de cada invocação do LangGraph (`config={"callbacks": [handler]}`), associado aos decorators `@observe` nas funções de nó e de integração externa.

---

## 4. Consequências

### Positivas
- **Privacidade e Conformidade Legal**: Adequação estrita às exigências de sigilo profissional e proteção de dados de clientes advocatícios.
- **Transparência Operacional Total**: Visualização gráfica de todo o raciocínio do agente, histórico de conversas e parâmetros das ferramentas acionadas.
- **Facilidade de Depuração**: Identificação imediata de gargalos de latência, prompts ineficientes ou falhas em tool calls.

### Negativas / Riscos Mitigados
- **Demanda de Recursos**: A VPS em produção deverá dispor de no mínimo 6 GB de RAM para comportar a API, PostgreSQL, Redis, Evolution API e Langfuse. *Mitigação*: Dimensionamento adequado da máquina e unificação do container PostgreSQL.
