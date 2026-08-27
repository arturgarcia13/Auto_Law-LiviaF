# ADR-004: Persistência de Dados — PostgreSQL Único com Multi-Databases

* **Status**: Aceito
* **Data**: 2026-08-27
* **Decisores**: Desenvolvedor / Arquiteto do Projeto
* **Contexto Técnico**: Camada de Banco de Dados Relacional e Checkpointing

---

## 1. Contexto e Problema

Três subsistemas distintos da arquitetura necessitam de persistência em banco relacional PostgreSQL:
1. **LangGraph (`AsyncPostgresSaver`)**: Necessita de persistência assíncrona para tabelas de checkpointing (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`), garantindo que o estado de cada conversa (`thread_id = telefone`) sobreviva a reinicializações e falhas do servidor.
2. **Langfuse**: Aplicação Next.js com Prisma ORM que cria automaticamente mais de 40 tabelas para controle de traces, spans, observações, usuários e chaves de API. Exige timezone `UTC`.
3. **Evolution API**: Gateway de WhatsApp que armazena dados das instâncias, tokens e credenciais de conexão do protocolo WhatsApp.

Surgiram três hipóteses de implementação:
- **Hipótese 1**: Subir três containers de PostgreSQL independentes no Docker Compose.
- **Hipótese 2**: Utilizar uma única base de dados compartilhada para todos os três serviços.
- **Hipótese 3**: Subir um único container PostgreSQL, mas com databases lógicas estritamente separadas.

---

## 2. Alternativas Consideradas

### Opção A: Três Containers PostgreSQL Independentes
- Subir `postgres-app`, `postgres-langfuse` e `postgres-evolution`.
- **Prós**: Isolamento total de processos e recursos.
- **Contras**: Desperdício desnecessário de memória RAM (três instâncias de PostgreSQL alocando buffers e pools de conexão independentes, consumindo entre 600 MB a 1.2 GB a mais de memória sem necessidade real).

### Opção B: Banco Único Compartilhado (Mesma Database)
- Conectar todos os serviços na mesma database `autolaw`.
- **Prós**: Máxima simplicidade inicial de configuração.
- **Contras**: **Altíssimo risco técnico**. As migrations automáticas do Prisma (Langfuse) e da Evolution API podem colidir com nomes de tabelas, índices ou triggers do LangGraph. Backups e restaurações pontuais tornam-se impossíveis de segregar.

### Opção C: Container Único com Bases de Dados Lógicas Isoladas
- Executar um único container PostgreSQL 16 (Alpine) com volumes nomeados para persistência.
- Utilizar um script de inicialização padrão (`init-db.sql`) montado no diretório `/docker-entrypoint-initdb.d/` para criar bases dedicadas no primeiro boot.
- **Prós**:
  - **Isolamento Completo de Schemas**: As migrations de um serviço jamais interferem nos outros.
  - **Eficiência de Recursos**: Apenas um processo PostgreSQL gerenciando conexões e buffer de memória.
  - **Backups e Restaurações Independentes**: Possibilidade de executar `pg_dump -d autolaw` sem misturar com logs pesados de traces do Langfuse.
- **Contras**: Se o container do PostgreSQL for interrompido, os três serviços perdem a camada relacional simultaneamente.

---

## 3. Decisão

Adotou-se a **Opção C: Container Único de PostgreSQL 16 com Multi-Databases Isoladas**.

Configuração adotada via `init-db.sql`:
```sql
-- Executado na inicialização automática do PostgreSQL
CREATE DATABASE langfuse;
GRANT ALL PRIVILEGES ON DATABASE langfuse TO "user";

CREATE DATABASE evolution_db;
GRANT ALL PRIVILEGES ON DATABASE evolution_db TO "user";
```

Configuração de conexões nos serviços:
- **FastAPI / LangGraph**: `postgresql+asyncpg://user:password@postgres:5432/autolaw`
- **Langfuse**: `postgresql://user:password@postgres:5432/langfuse`
- **Evolution API**: `postgresql://user:password@postgres:5432/evolution_db`

Parâmetro `TZ: UTC` foi fixado globalmente no container para assegurar compatibilidade estrita com os requisitos do Langfuse v4+.

---

## 4. Consequências

### Positivas
- **Pegada Leve de Memória**: Economia de memória essencial tanto para desenvolvimento local quanto para viabilizar VPS com menor custo operacional.
- **Segurança de Schema**: Cada ferramenta gerencia suas próprias migrações sem risco de regressão mútua.
- **Simplicidade de Manutenção**: Apenas uma porta exposta e um volume persistente de dados (`pgdata`).

### Negativas / Riscos Mitigados
- **Disponibilidade**: Ponto único de persistência. *Mitigação*: Uso de healthcheck nativo com `pg_isready -U user -d autolaw` no Docker Compose e volumes montados com persistência garantida.
