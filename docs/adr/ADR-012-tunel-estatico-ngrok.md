# ADR-012: Túnel de Desenvolvimento Seguro com Domínio Estático Ngrok

## 📌 Status
**Aceito** (2026-09-02)

---

## 🏛️ Contexto e Problema
A integração dos webhooks do Kommo CRM com a aplicação FastAPI local requer um endpoint público seguro sob protocolo HTTPS. 

Anteriormente, utilizou-se o Cloudflare Quick Tunnel (`cloudflared tunnel --url http://localhost:8000`), o que gerava desafios críticos de estabilidade operacional:
1. **Instabilidade de URL**: A cada reinicialização do script ou queda de conexão, o Cloudflare gerava um subdomínio temporário randômico diferente (`https://<palavras-aleatorias>.trycloudflare.com`).
2. **Carga Operacional Excessiva**: O operador precisava atualizar manualmente a URL de webhook dentro das configurações do painel da Kommo CRM a cada início de testes.
3. **Falso Positivo de Queda do Serviço**: Mensagens enviadas enquanto a URL antiga estava inativa geravam erros de entrega (502 / Connection Refused) na Kommo, que pausava o webhook.

---

## 🎯 Decisão
1. **Adoção do Ngrok com Domínio Estático Gratuito**: Utilização do **Ngrok** com o domínio estático permanente vinculado à conta do usuário (`quickness-serrated-felt-tip.ngrok-free.dev`).
2. **Orquestração Automatizada via PowerShell ([`start_tunnel.ps1`](file:///C:/Users/ATLAB-USUARIO.DESKTOP-P2H460F/Documents/PROJECTS/Auto_Law-LiviaF/start_tunnel.ps1))**:
   - Inicialização conjunta do servidor FastAPI (Uvicorn) na porta 8000 com `--reload`.
   - Execução do Ngrok utilizando a flag moderna `--url quickness-serrated-felt-tip.ngrok-free.dev`.
   - Encerramento prévio de instâncias antigas para evitar conflitos de porta (`ERR_NGROK_334`).
   - Leitura automatizada da URL pública e status através da API local do Ngrok (`http://127.0.0.1:4040/api/tunnels`).
3. **Exibição Formatada de Endpoints**: Impressão direta no console das URLs completas já com o token de segurança (`?token=teste123`) para configuração rápida no Kommo CRM.

---

## 🚀 Consequências

### Benefícios
- **URL Permanente e Imutável**: Configura-se o webhook na Kommo uma única vez; a URL nunca se altera, mesmo após reiniciar o computador ou o terminal.
- **Painel de Inspeção Local (Web UI)**: Disponibilidade da interface web em `http://127.0.0.1:4040` para auditar payloads recebidos, tempos de resposta e cabeçalhos HTTP em tempo real.
- **Zero Custo Adicional**: O domínio estático de desenvolvimento é um recurso vitalício e 100% gratuito concedido pela conta do Ngrok.
- **Encerramento Limpo**: Gerenciamento de processos com parada coordenada ao pressionar `Ctrl + C`.

### Riscos e Mitigações
- **Limite de Sessão Única Simultânea**: Uma conta gratuita do Ngrok suporta uma sessão de túnel por vez.
  - *Mitigação*: O script `start_tunnel.ps1` detecta e encerra instâncias anteriores do processo `ngrok.exe` automaticamente antes de estabelecer a nova conexão.
