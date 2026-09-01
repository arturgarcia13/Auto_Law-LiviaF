# ADR-009: Processamento e Transcrição de Áudio via Google Gemini Multimodal STT

## 📌 Status
**Aceito** (2026-08-31)

---

## 🏛️ Contexto e Problema
No atendimento trabalhista via WhatsApp, uma parcela significativa de clientes prefere enviar áudios detalhando seu caso (tempo trabalhado, relatos de abusos, motivos da demissão).
Para qualificar leads de forma ágil e humanizada, o assistente virtual precisa receber esses áudios, transcrevê-los para texto com alta fidelidade ao vocabulário jurídico e popular brasileiro, e processar as respostas dentro da máquina de estados do LangGraph.

---

## ⚖️ Alternativas Consideradas

| Alternativa | Prós | Contras |
|---|---|---|
| **A. OpenAI Whisper API / Groq** | Boa precisão e velocidade. | Requer contratação de fornecedor adicional, novas chaves de API e faturamento separado. |
| **B. Whisper Local (faster-whisper)** | Zero custo de API, privacidade total. | Exige GPU dedicada ou consome muita CPU/RAM no servidor, aumentando tempo de resposta. |
| **C. Google Gemini Flash Multimodal STT** | ✅ Já integrado na stack do projeto (`GEMINI_API_KEY`).<br>✅ Baixíssima latência e excelente compreensão do português brasileiro.<br>✅ Suporte nativo a formatos de áudio do WhatsApp (OGG / Opus / MP3).<br>✅ Custo zero adicional. | Depende da API do Google Gemini. |

---

## 🎯 Decisão
Adotar o **Google Gemini Flash (Multimodal Audio)** como motor de transcrição de áudios (Speech-to-Text).
- Ao receber evento com áudio do Kommo, o backend faz o download assíncrono dos bytes de áudio.
- Envia os bytes para o modelo Gemini com prompt de formatação textual fidedigna.
- O texto resultante é prefixado como `[Áudio Transcrito]` e injetado no fluxo conversacional do agente no LangGraph.

---

## 🚀 Consequências

### Benefícios
- **Stack Unificada**: Usa a mesma credencial e infraestrutura já utilizada pelo agente de IA.
- **Experiência do Usuário Superior**: O lead pode se comunicar por voz e ser compreendido com extrema precisão.
- **Resiliência**: Tratamento de exceções e fallback informando ao cliente caso o áudio esteja corrompido ou inaudível.
