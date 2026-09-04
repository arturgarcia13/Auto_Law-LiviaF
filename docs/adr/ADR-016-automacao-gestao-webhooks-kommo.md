# ADR-016: Automação Integral de Gestão, Permissões e Auto-Cura de Webhooks no Kommo CRM

## 📌 Status
**Aceito** (2026-09-04)

---

## 🏛️ Contexto e Problema
A integração do assistente jurídico da Dra. Lívia França com o Kommo CRM depende do recebimento em tempo real de mensagens e eventos disparados pela plataforma Kommo via Webhooks (API v4).

Anteriormente, o registro e a manutenção da URL do webhook dependiam de etapas manuais executadas pelo operador na interface web da Kommo CRM (Configurações > Integrações > Webhooks). Essa abordagem gerava os seguintes problemas:
1. **Carga Operacional**: Toda vez que o ambiente ou token de segurança mudava, era necessário navegar no painel web para cadastrar o webhook manualmente.
2. **Risco de Dessincronização e Silenciamento**: Caso a Kommo desativasse o webhook (`disabled: true`) por falha temporária de rede ou se faltasse a permissão essencial `add_message`, o sistema ficava inoperante sem que o operador percebesse imediatamente.
3. **Limitação da API v4 do Kommo**: A API v4 de webhooks da Kommo não fornece um método `PATCH` para atualização de eventos/permissões inscritos em uma URL existente, exigindo orquestração cuidadosa de remoção (`DELETE`) e recriação (`POST`).

---

## 🎯 Decisão
1. **Módulo Cliente de Alta Confiabilidade (`integrations/kommo.py`)**:
   - Implementação das funções `listar_webhooks()`, `criar_webhook()`, `remover_webhook()`, `modificar_webhook_permissoes()` e `testar_ping_webhook()`.
   - Implementação da função orquestradora `garantir_webhook_ativo()`, que executa o ciclo de auto-cura: consulta status no CRM, checa presença do evento `add_message`, testa o ping do endpoint e, se houver qualquer divergência, remove o registro antigo e recria com validação pós-criação.
2. **Definição Estrita do Escopo de Eventos**:
   - Subscrição padrão focada exclusivamente em `["add_message"]`, conforme alinhamento de requisitos, mantendo catálogo estruturado de todos os demais eventos (`add_lead`, `status_lead`, `add_task`, etc.) para extensibilidade futura.
3. **Automação Nativa no Inicializador do Túnel (`start_tunnel.ps1`)**:
   - A cada inicialização do túnel Ngrok e Uvicorn, o script executa imediatamente a rotina de verificação e auto-cura via CLI Python.
   - Caso o webhook esteja íntegro, prossegue sem alterações; caso esteja ausente, desativado ou sem `add_message`, repara automaticamente e confirma a saúde no console com feedback visual.
4. **CLI Executável Autônomo (`scripts/gerenciar_webhook_kommo.py`)**:
   - Interface de linha de comando para auditoria, inspeção, modificação manual de permissões e diagnósticos pontuais.
5. **API Administrativa REST (`app/routers/admin.py`)**:
   - Endpoints sob o prefixo `/admin/kommo/webhooks` protegidos por token de segurança (`ADMIN_SECRET_TOKEN` ou `KOMMO_WEBHOOK_SECRET`) para permitir gestão programática remota e monitoramento contínuo.

---

## 🚀 Consequências

### Benefícios
- **Zero Intervenção Manual**: A inicialização via `start_tunnel.ps1` garante que o webhook esteja sempre registrado, ativo e com a permissão correta sem exigir cliques na interface da Kommo.
- **Auto-Cura Resiliente**: Webhooks desativados pelo CRM ou com lista de eventos desatualizada são corrigidos automaticamente em milissegundos.
- **Idempotência**: Se o webhook já estiver correto e respondendo, nenhuma operação destrutiva é executada.
- **Auditoria e Observabilidade**: O comando `--verificar` e o endpoint `/admin/kommo/webhooks/verify` fornecem relatório imediato de conectividade, status no CRM e latência de ping.

### Riscos e Mitigações
- **Restrição de Plano e Permissões na Kommo**: O uso da API v4 de webhooks requer plano Advanced/Pro/Enterprise e credencial de Administrador.
  - *Mitigação*: Mensagens de erro claras e logs detalhados são exibidos caso a API retorne HTTP 401 ou 403, permitindo diagnóstico imediato sem travar o servidor local.
- **Inexistência de PATCH Nativo na Kommo**: A remoção e recriação criam uma janela mínima de milissegundos entre o `DELETE` e o `POST`.
  - *Mitigação*: A operação é executada de forma sequencial imediata e testada logo após a recriação, garantindo reativação instantânea.
