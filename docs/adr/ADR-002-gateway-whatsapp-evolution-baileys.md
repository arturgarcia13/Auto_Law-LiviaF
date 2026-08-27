# ADR-002: Gateway WhatsApp — Evolution API no Modo Baileys (QR Code)

* **Status**: Aceito
* **Data**: 2026-08-27
* **Decisores**: Desenvolvedor / Arquiteto do Projeto
* **Contexto Técnico**: Canal de Atendimento e Recepção de Leads (WhatsApp)

---

## 1. Contexto e Problema

O canal primário de entrada dos leads para o escritório da Dra. Lívia França é o WhatsApp (advindos de anúncios do Facebook, Instagram e Google Ads). Para automatizar o diálogo inicial e a coleta de dados, a aplicação precisa receber as mensagens em tempo real (webhooks) e enviar mensagens de texto e documentos.

A API oficial da Meta (WhatsApp Cloud API) impõe:
- Verificação documental formal da empresa no Meta Business Manager (burocracia demorada).
- Cobrança por bloco de conversas de marketing e utilidade iniciadas pelo bot (custo em dólar).
- Aprovação prévia e rígida de Message Templates para iniciar conversas fora da janela de 24h.
- Complexidade elevada para testes em ambiente local de desenvolvimento.

Para o ciclo de desenvolvimento, homologação e início das operações do escritório, buscou-se uma alternativa sem burocracia, de implantação imediata e custo operacional zero.

---

## 2. Alternativas Consideradas

### Opção A: WhatsApp Cloud API Oficial (Meta)
- Conexão direta ou via BSP (Twilio, Z-API oficial, etc.) com a infraestrutura da Meta.
- **Prós**: Estabilidade máxima; conformidade oficial com os Termos de Serviço da Meta; zero risco de bloqueio de chip.
- **Contras**: Custo recorrente por mensagem/conversa; processo moroso de verificação de empresa; impossibilita testes locais ágeis sem configuração complexa na Meta.

### Opção B: Evolution API no Modo Baileys (Conexão via QR Code)
- Utilização da Evolution API v2 (open-source) conteinerizada via Docker, conectada ao WhatsApp do escritório por escaneamento de QR Code (emulação de WhatsApp Web sobre WebSocket).
- **Prós**:
  - Implantação imediata: basta subir o container e escanear o QR Code pelo celular da Dra. Lívia.
  - Custo zero de software e de tráfego de mensagens.
  - Testável localmente no Docker sem dependência de domínios ou verificação da Meta.
  - Camada de abstração transparente: a chamada de envio (`POST /message/sendText/{instance}`) é idêntica caso a instância venha a ser migrada para a Cloud API oficial no futuro.
- **Contras**:
  - Utilização de protocolo não-oficial (sujeito aos termos de uso da Meta).
  - Risco de desconexão da sessão ou restrição de chip caso haja comportamento abusivo de disparos em massa.

---

## 3. Decisão

Adotou-se a **Opção B: Evolution API v2 no modo Baileys (QR Code)** para todo o ciclo de desenvolvimento, homologação e fase inicial de operação.

Medidas técnicas implementadas para mitigar os riscos da opção:
1. **Sem disparos em massa**: O bot apenas responderá a leads que ativamente enviaram mensagens (tráfego puramente receptivo 1-a-1).
2. **Simulação humana de digitação**: Inclusão de atraso programado (`"delay": 1500` ms) antes do envio da mensagem.
3. **Persistência resiliente de sessão**: Sessão salva no PostgreSQL (`evolution_db`) e Redis, garantindo que reinicializações do container não percam a conexão do celular.
4. **Fixação de versão**: Imagem Docker com tag específica (`evoapicloud/evolution-api:v2.2.3`) e parâmetro `CONFIG_SESSION_PHONE_VERSION` sincronizado.
5. **Arquitetura Desacoplada**: A aplicação Python interage com a interface HTTP da Evolution API; se o escritório decidir futuramente migrar para a API oficial Meta, bastará reconfigurar a instância na Evolution API, com zero alteração no código FastAPI/LangGraph.

---

## 4. Consequências

### Positivas
- **Velocidade de Entrega**: Ambiente funcional imediatamente em desenvolvimento local.
- **Zero Custo de Mensageria**: Economia direta para o cliente na fase de validação comercial.
- **Portabilidade**: Migração indolor para a Cloud API oficial no futuro através da mesma Evolution API.

### Negativas / Riscos Mitigados
- **Monitoramento de Conexão**: Necessidade de rota de monitoramento de saúde (`GET /health`) para verificar se a instância está no estado `"open"`, alertando caso o celular desconecte.
