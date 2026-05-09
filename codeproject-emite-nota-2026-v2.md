---
tipo: projeto-codigo
linguagem: python
status: em andamento
inicio: 2026-04-28
tags: [aprendizado, codigo, fastapi, streamlit, n8n, postgresql, pyautogui, llm, nfse, docker]
aliases: [emite-nota, emite-nota-2026, emite-nota-v2]
---

# Projeto — Emite Nota 2026 v2

Sistema automatizado para capturar vendas via WhatsApp, processar os dados com Inteligência Artificial, aprovar via painel administrativo (Streamlit) e emitir Notas Fiscais de Serviço Eletrônicas (NFSe) no portal do governo utilizando PyAutoGUI.

## Repositório

`08-code-projects/emite-nota-2026-v2/`

Arquivos do projeto:
- [[08-code-projects/emite-nota-2026-v2/README.md|README]]
- [[08-code-projects/emite-nota-2026-v2/ARCHITECTURE_REVIEW.md|Revisão de Arquitetura]]
- [[08-code-projects/emite-nota-2026-v2/PLANO_IMPLEMENTACAO.md|Plano de Implementação]]
- [[08-code-projects/emite-nota-2026-v2/HOWTO_DEPLOY.md|How-To Deploy]]
- [[08-code-projects/emite-nota-2026-v2/ROADMAP.md|Roadmap de Melhorias]]

---

## Objetivo

Automatizar o pipeline completo de emissão de notas fiscais de serviço para o estúdio fotográfico da Andrea, eliminando:
- Digitação manual de dados de clientes
- Geração de planilhas intermediárias (XLSX)
- Etapas manuais de sincronização entre sistemas

**Fluxo resumido:**
```
WhatsApp (Andrea) → n8n → FastAPI → PostgreSQL → LLM → Streamlit (revisão) → PyAutoGUI → Portal NFSe
```

---

## Decisões de arquitetura

### ADR-001: Migração de CLI para API HTTP (n8n)
A v2.0 usava `Execute Command` no n8n para chamar `python main.py parse-webhook`. Criado `api.py` com FastAPI expondo `/webhook` e `/process-buffer` porque o n8n de produção não tem acesso ao filesystem do container Python.

### ADR-002: NullPool no SQLAlchemy
Streamlit exibia dados obsoletos mesmo após deleções no banco. Configurado `engine = create_engine(URL, poolclass=NullPool)` para evitar que o pool padrão reutilizasse conexões abertas durante o processo do Streamlit.

### ADR-003: Variáveis de Ambiente via Docker Swarm (não via .env)
O `.env` está no `.dockerignore` por segurança. Variáveis configuradas na aba Ambiente do Easypanel e injetadas pelo Swarm.

### ADR-004: Autenticação da API via Header Secret
API pública (HTTPS via Traefik) mas protegida com header `x-api-secret` em todos os endpoints.

### ADR-005: Processamento do buffer ativado manualmente por mensagem WhatsApp
A v2 inicial tentou uma janela de 15 minutos para acumular mensagens antes de enviar ao LLM. Essa lógica foi **removida**. O fluxo atual é:

1. Andrea envia as mensagens de venda normalmente pelo WhatsApp.
2. Quando quiser processar, ela envia a mensagem `"Processbuffer"` pelo WhatsApp.
3. O n8n detecta esse comando e chama o endpoint `POST /process-buffer` da API.
4. A API processa **todas as mensagens pendentes do buffer** de uma vez, enviando o contexto completo ao LLM.

Isso elimina a dependência de timer e dá controle explícito à Andrea sobre quando o processamento ocorre. O parâmetro `?force=true` ainda é aceito por compatibilidade, mas não tem efeito prático.

### ADR-006: Normalização via Prompt do LLM (não via código)
Campos como `aniversario` e `como_conheceu` chegam em formatos livres. Instruir o LLM via `description` dos campos Pydantic a entregar dados normalizados, evitando regex frágeis.

### ADR-007: Separação servidor/PC local (maio/2026)
PyAutoGUI precisa de navegador local com interface gráfica — não funciona em servidor headless. Criado `emitir_client.py` standalone para o PC da Andrea, conectando diretamente ao banco PostgreSQL do servidor via porta 3999 ou SSH tunnel.

---

## Snippets úteis desse projeto

### Multi-provider LLM com fallback automático

**Por que está aqui:** Padrão de resiliência para evitar vendor lock-in em projetos com LLM.

```python
def get_llm():
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    elif os.getenv("ANTHROPIC_API_KEY") and ChatAnthropic:
        return ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
    elif os.getenv("GOOGLE_API_KEY") and ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    elif os.getenv("GROQ_API_KEY") and ChatGroq:
        return ChatGroq(model="llama3-70b-8192", temperature=0)
```

### Lock thread-safe no endpoint FastAPI

**Por que está aqui:** Proteção contra race condition em endpoints que disparam processamento em background.

```python
import threading
_lock = threading.Lock()

@app.post("/process-buffer")
async def trigger_process_buffer(force: bool = False, ...):
    if not _lock.acquire(blocking=False):
        return {"status": "skip", "detail": "Já em processamento"}
    def run():
        try:
            process_buffer(force=force)
        finally:
            _lock.release()
    threading.Thread(target=run, daemon=True).start()
    return {"status": "ok"}
```

### Context manager para sessões SQLAlchemy

**Por que está aqui:** Elimina leak de conexões em caso de exceção.

```python
# Em vez de:
session = SessionLocal()
session.add(buffer)
session.commit()
session.close()

# Usar:
with SessionLocal() as session:
    session.add(buffer)
    session.commit()
```

---

## Problemas que enfrentei e como resolvi

| Problema                                                          | Solução                                                            |
| ----------------------------------------------------------------- | ------------------------------------------------------------------ |
| Streamlit exibia dados obsoletos após deleções                    | NullPool no SQLAlchemy (ADR-002)                                   |
| n8n não tinha acesso ao filesystem do container                   | Migração para API HTTP com FastAPI (ADR-001)                       |
| Mensagens fragmentadas do mesmo cliente geravam vendas duplicadas | Processamento manual via disparo explícito — LLM recebe todas as mensagens pendentes de uma vez (ADR-005) |
| PyAutoGUI não roda em servidor headless                           | Separação: servidor (API + DB) + PC local (emissão) (ADR-007)      |
| Race condition em `/process-buffer`                               | `threading.Lock()` com `acquire(blocking=False)`                   |
| Leak de conexões DB em caso de exceção                            | Context manager `with SessionLocal() as session:`                  |
| CPFs inválidos gerados pelo LLM                                   | Validação com `CPFValidator` antes de salvar em `vendas_pendentes` |
| Sem feedback para usuária após processamento                      | Notificação via Evolution API para WhatsApp da Andrea              |

---

## O que aprendi aqui

- [[01-learning/ai/n8n/how-to/integracao-fastapi-n8n|Integração FastAPI + n8n via HTTP Request]]
- [[01-learning/python/how-to/context-manager-sqlalchemy|Context manager para sessões SQLAlchemy]]
- [[01-learning/python/how-to/threading-lock-fastapi|Threading.Lock em endpoints FastAPI]]
- [[01-learning/docker/how-to/deploy-docker-swarm-easypanel|Deploy com Docker Swarm no Easypanel]]
- [[01-learning/ai/llm/how-to/multi-provider-llm|Multi-provider LLM com fallback]]
- [[01-learning/python/how-to/pyautogui-automacao-nfse|Automação de NFSe com PyAutoGUI]]

---

## Links relacionados

- [[08-code-projects/emite-nota-2026-v2/README.md]]
- [[08-code-projects/emite-nota-2026-v2/ARCHITECTURE_REVIEW.md]]
- [[08-code-projects/emite-nota-2026-v2/PLANO_IMPLEMENTACAO.md]]
- [[08-code-projects/emite-nota-2026-v2/HOWTO_DEPLOY.md]]
- [[08-code-projects/emite-nota-2026-v2/ROADMAP.md]]
- [[02-work/andrea-sabba-fotografia/projects/emite-nota|Projeto no contexto do estúdio]]

---

*Última atualização: 2026-05-02*