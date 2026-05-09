# Plano de Implementação — Emite Nota (v2.2 — Estado Atual)

## Contexto

Este documento registra a evolução arquitetural do projeto desde sua concepção inicial (scripts fragmentados) até a versão atual em produção no Easypanel/Docker Swarm.

---

## Arquitetura Atual (v2.2 — Em Produção)

### Componentes em Execução

| Componente | Tecnologia | Localização |
|---|---|---|
| Recepção de mensagens | Evolution API → n8n → FastAPI | VPS (Docker Swarm) |
| API de integração | FastAPI (Uvicorn, porta 8502) | `api.py` |
| Extração via IA | LangChain + OpenAI/Gemini/Groq | `src/parsers/agent_parser.py` |
| Painel de revisão | Streamlit (porta 8501) | `app_revisao.py` |
| Banco de dados | PostgreSQL (pgvector) | Container `n8n-banco` |
| Emissão de notas | PyAutoGUI (PC Windows) | `main.py preparar` + `emitir` |

### Fluxo de Dados

```
WhatsApp (Andrea)
    ↓
Evolution API
    ↓
n8n: HTTP Request POST /webhook  → mensagens_buffer (texto bruto)
    ↓
n8n: HTTP Request POST /process-buffer?force=true
    ↓
LLM (OpenAI/Gemini): extrai campos estruturados de múltiplas msgs
    ↓
vendas_pendentes (aguardando_aprovacao)
    ↓
Streamlit app_revisao.py: Andrea revisa e aprova/rejeita
    ↓ (ao clicar Aprovar)
clientes + vendas (tabelas definitivas)
    ↓
PC Windows: python main.py preparar → notas_a_emitir.xlsx
    ↓
PC Windows: python main.py emitir → PyAutoGUI → Portal NFSe
```

---

## Decisões Técnicas (ADRs)

### ADR-001: Migração de CLI para API HTTP (n8n)
**Contexto:** A v2.0 usava `Execute Command` no n8n para chamar `python main.py parse-webhook`.  
**Decisão:** Criar `api.py` com FastAPI expondo `/webhook` e `/process-buffer`.  
**Motivo:** O n8n de produção não tem acesso ao filesystem do container Python. HTTP Request é o meio correto de integração entre serviços no Docker Swarm.

### ADR-002: NullPool no SQLAlchemy
**Contexto:** Streamlit exibia dados obsoletos mesmo após deleções no banco.  
**Decisão:** Configurar `engine = create_engine(URL, poolclass=NullPool)`.  
**Motivo:** O pool padrão do SQLAlchemy reutilizava conexões abertas durante o processo do Streamlit, que via uma snapshot antiga da transação PostgreSQL.

### ADR-003: Variáveis de Ambiente via Docker Swarm (não via .env)
**Contexto:** O `.env` está no `.dockerignore` por segurança.  
**Decisão:** As variáveis (`DATABASE_URL`, `STREAMLIT_PASSWORD`, `OPENAI_API_KEY`, `API_SECRET`) são configuradas na aba Ambiente do Easypanel e injetadas pelo Swarm.  
**Impacto:** Mudanças de senha/chaves requerem `docker service update --env-add` ou edição no Easypanel — não basta editar o `.env` local.

### ADR-004: Autenticação da API via Header Secret
**Contexto:** A API precisa ser pública (HTTPS via Traefik) mas protegida.  
**Decisão:** Verificar header `x-api-secret` em todos os endpoints.  
**Implementação:** `API_SECRET` como env var; n8n configura via "Header Auth" credential.

### ADR-005: Janela de 15 minutos no `process_buffer`
**Contexto:** A Andrea frequentemente manda 2-3 mensagens em sequência sobre o mesmo cliente (primeira com dados pessoais, segunda com plano e pagamento).  
**Decisão:** O `process_buffer` aguarda 15 min de silêncio antes de enviar ao LLM, para garantir que todas as mensagens de uma venda estejam no buffer.  
**Override:** Parâmetro `?force=true` ignora a janela (útil para testes e reprocessamentos).

### ADR-006: Normalização via Prompt do LLM (não via código)
**Contexto:** Campos como `aniversario` (04.08.1982 → 04/08/1982) e `como_conheceu` (Pela Mayara → Indicação) chegam em formatos livres.  
**Decisão:** Instruir o LLM via `description` dos campos Pydantic a já entregar os dados normalizados.  
**Motivo:** A normalização via regex seria frágil para texto livre. O LLM entende contexto e pode categorizar corretamente.

---

## Regras de Extração do LLM (Atuais)

Definidas no modelo `VendaExtraction` em `src/parsers/agent_parser.py`:

| Campo | Regra |
|---|---|
| `cpf` | Apenas números |
| `aniversario` | Padronizar com barras: DD/MM/AAAA |
| `como_conheceu` | Categorizar: Indicação, Instagram, Google, Facebook ou Outros |
| `plano` | Extrair EXCLUSIVAMENTE da linha "Fez ensaio..." |
| `categoria` | Inferir do plano (Gestante, Mães, Familia, Infantil, Newborn, etc.) |
| `valor` | Somar todos os pagamentos mencionados |
| `meio_pagto` | Meio com maior valor (Pix, Cartão, Dinheiro, Infinity) |

**Regra crítica de agrupamento:** Se o mesmo cliente aparecer em múltiplas mensagens, unificar em UMA venda. Nunca criar duplicatas.

**Regra crítica sobre o plano:** Ignorar o tipo de ensaio preenchido pelo cliente no formulário (junto com nome/CPF). O plano real vem da mensagem da Andrea começando com "Fez ensaio...".

---

## Estrutura de Arquivos

```
emite-nota-2026-v2/
├── api.py                         # FastAPI: /webhook e /process-buffer
├── app_revisao.py                 # Streamlit: painel de aprovação
├── main.py                        # CLI: preparar e emitir notas (PC Windows)
├── start.sh                       # Inicializa Streamlit + FastAPI no container
├── Dockerfile                     # Build do container
├── requirements.txt
├── .env                           # Uso LOCAL apenas (não vai para o Docker)
├── .env.example
├── .dockerignore
├── config/
│   └── settings.py                # Coordenadas PyAutoGUI, templates NFSe
├── src/
│   ├── parsers/
│   │   └── agent_parser.py        # LLM extraction (LangChain)
│   ├── processors/
│   │   └── cpf_validator.py       # Validação de CPF
│   ├── database/
│   │   └── db_manager.py          # SQLAlchemy models + NullPool engine
│   ├── exporters/
│   │   └── nfse_preparer.py       # Geração do XLSX para emissão
│   └── automation/
│       └── nfse_emitter.py        # PyAutoGUI (PC Windows)
└── old/                           # Arquivos descontinuados
```

---

## Checklist de Status

- [x] API FastAPI (webhook + process-buffer) em produção
- [x] Streamlit com autenticação e botão de recarregar
- [x] NullPool: dados sempre frescos no painel
- [x] n8n integrado via HTTP Request (não mais Execute Command)
- [x] Autenticação via `x-api-secret`
- [x] Prompt LLM: agrupamento de clientes repetidos
- [x] Prompt LLM: plano extraído apenas de "Fez ensaio..."
- [x] Normalização de datas e "como conheceu" via LLM
- [x] Janela de 15 min + override `?force=true`
- [ ] Captura automática do número da NFSe após emissão (PyAutoGUI)
- [ ] Deduplicação automática por CPF+data+valor antes de inserir em `vendas_pendentes`
