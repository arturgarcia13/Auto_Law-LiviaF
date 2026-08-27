# ADR-006: Metodologia de Desenvolvimento — TDD e Docker Compose Incremental

* **Status**: Aceito
* **Data**: 2026-08-27
* **Decisores**: Desenvolvedor / Arquiteto do Projeto
* **Contexto Técnico**: Estratégia de Engenharia de Software e Ciclo de Vida de Desenvolvimento

---

## 1. Contexto e Problema

O projeto Auto_Law-LiviaF integra múltiplas tecnologias interdependentes:
- Framework web assíncrono (FastAPI).
- Agente de IA com grafo de estados (LangGraph).
- Três bancos de dados relacionais e cache (PostgreSQL Multi-DB e Redis).
- Plataforma de observabilidade conteinerizada (Langfuse).
- Gateway de mensageria WhatsApp (Evolution API).
- Três APIs de negócio externas (Kommo CRM, ZapSign, ADVBOX).

A abordagem tradicional de configurar todos os serviços simultaneamente em um `docker-compose.yml` abrangente ("big bang") costuma gerar sobrecarga cognitiva, mascarar erros de configuração de rede entre containers, dificultar a identificação da causa raiz de falhas e retardar a primeira entrega funcional.

O desenvolvedor estabeleceu como requisito essencial uma abordagem incremental, baseada em testes (TDD) e orientada a boas práticas de engenharia de software.

---

## 2. Alternativas Consideradas

### Opção A: Setup Completo de Infraestrutura ("Big Bang")
- Subir todos os serviços do Docker no primeiro dia e escrever o código da aplicação de ponta a ponta.
- **Prós**: O ambiente final está visível de imediato.
- **Contras**: Dificuldade massiva de diagnóstico de falhas; testes só podem rodar quando todas as APIs e bancos estiverem operacionais; alto risco de retrabalho em schemas e conexões.

### Opção B: Desenvolvimento Incremental Orientado a Testes (TDD + Docker Progressivo)
- Dividir o desenvolvimento em 9 sprints modulares.
- Cada serviço Docker é adicionado ao `docker-compose.local.yml` estritamente no sprint em que se torna necessário.
- A ordem de implementação segue a cadeia de pré-requisitos técnicos: as dependências são construídas antes dos serviços dependentes (ex: PostgreSQL é criado antes do Langfuse e antes do LangGraph).
- **Prós**:
  - Cada camada é testada e homologada isoladamente antes de receber novas camadas.
  - O sistema é executável e demonstrável ao final de cada sprint.
  - Erros de rede ou conexão no Docker são isolados imediatamente no momento em que o serviço é introduzido.
  - Suite de testes automatizados (`pytest-asyncio` e mocks de HTTP) cresce junto com o código.
- **Contras**: Requer rigor na definição de contratos de interface e paciência para não antecipar etapas.

---

## 3. Decisão

Adotou-se a **Opção B: Pipeline Incremental em 9 Sprints com TDD Estrito e Docker Compose Progressivo**.

Ordem de execução das dependências:
1. **Sprint 1**: Estrutura de pastas, ambiente virtual, requirements e linters.
2. **Sprint 2**: FastAPI skeleton (routers, schemas Pydantic e testes de endpoints com mocks).
3. **Sprint 3**: PostgreSQL unificado (`init-db.sql`) + Redis.
4. **Sprint 4**: Langfuse self-hosted (conectado na database `langfuse` criada no Sprint 3).
5. **Sprint 5**: LangGraph + Google Gemini (conectado na database `autolaw` com `AsyncPostgresSaver` e tracing direto no Langfuse).
6. **Sprint 6**: Evolution API (WhatsApp Baileys conectado na database `evolution_db` e Redis).
7. **Sprint 7**: Kommo CRM (wrappers de API, criação de leads e movimentação de etapas).
8. **Sprint 8**: ZapSign (geração de minutas e webhook de documento assinado).
9. **Sprint 9**: ADVBOX (cadastro de cliente e processo após assinatura).

Cada sprint possui sua própria **Definition of Done (DoD)** e suíte de testes correspondente.

---

## 4. Consequências

### Positivas
- **Previsibilidade**: O desenvolvedor sabe exatamente qual bloco de código atacar e como validar se a entrega está correta.
- **Confiança na Refatoração**: Cobertura de testes garante que mudanças posteriores não quebrem fluxos anteriores.
- **Zero Surpresas de Conectividade**: Testes de conexão de banco e mensageria validados de forma atômica.

### Negativas / Riscos Mitigados
- **Tempo Inicial**: Investimento de tempo inicial na escrita de fixtures e testes unitários. *Mitigação*: Retorno imediato em economia de horas de depuração manual.
