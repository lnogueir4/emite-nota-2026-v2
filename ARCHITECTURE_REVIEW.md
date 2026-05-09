# Revisão de Arquitetura — emite-nota-2026-v2

> Análise realizada em: maio/2026  
> Versão analisada: v2.2 (em produção)
## Visão Geral do Sistema

### Arquitetura Alvo (decisão maio/2026)

O sistema é dividido em dois ambientes físicos distintos:

```
╔══════════════════════════════════════════════════════╗
║  SERVIDOR VPS  (Docker Swarm)                        ║
║                                                      ║
║  WhatsApp ──► n8n ──► FastAPI ──► PostgreSQL (PG)    ║
║                                        │             ║
║                               Streamlit (revisão)    ║
║                                        │             ║
║                            clientes + vendas (PG)    ║
║                             status="pendente"        ║
╚══════════════════════════════╤═══════════════════════╝
                               │
                    DATABASE_URL via rede
                    (porta exposta ou SSH tunnel)
                               │
╔══════════════════════════════▼═══════════════════════╗
║  PC DA ANDREA  (cliente local)                       ║
║                                                      ║
║  python emitir_client.py                             ║
║       │                                              ║
║       ├─ conecta ao PG do servidor                   ║
║       ├─ lê vendas status="pendente"                 ║
║       ├─ NFSeEmitter (PyAutoGUI)                     ║
║       │       └─► Chrome ──► nfse.gov.br             ║
║       └─ atualiza status="emitida" + num_nota no PG  ║
╚══════════════════════════════════════════════════════╝
```

**Por que separar assim?**
- O PyAutoGUI controla o navegador **local** — não funciona num servidor headless sem display
- O banco fica centralizado no servidor — única fonte de verdade
- Elimina o XLSX como intermediário frágil (arquivo pode ficar desatualizado, ser esquecido, etc.)
- Após a emissão, o cliente atualiza o status diretamente no banco — sem etapas manuais de sincronização

### Fluxo Detalhado

```
[SERVIDOR]                              [PC DA ANDREA]

mensagens buffer
      │
      ▼ LLM
vendas_pendentes
      │
      ▼ Streamlit (Andrea aprova)
clientes + vendas
status = "pendente"
      │
      │ ◄──── DATABASE_URL ────────────── python emitir_client.py
      │                                          │
      │                                   lê vendas pendentes
      │                                          │
      │                                   NFSeEmitter (PyAutoGUI)
      │                                          │
      │                                   Chrome → nfse.gov.br
      │                                          │
      │ ◄──── UPDATE status="emitida" ────────────┘
             num_nota gravado no banco
```

**Tecnologias:** Python 3.11 · FastAPI · SQLAlchemy · PostgreSQL · LangChain · Streamlit · Docker Swarm · n8n · PyAutoGUI

### O que precisa mudar no código

| Componente | Estado atual | Estado alvo |
|---|---|---|
| `NFSeEmitter` | lê de XLSX via `openpyxl` | lê diretamente do banco (`SessionLocal`) |
| `NFSePreparer` | gera XLSX intermediário | **obsoleto** — pode ser removido |
| `main.py emitir` | roda no servidor | extrair para `emitir_client.py` (script standalone para o PC) |
| `config/settings.py` | `DATABASE_URL` aponta para localhost | no cliente, apontar para o servidor remoto via `.env` local |


> **Ver ROADMAP.md item 19** para o plano de implementação desta mudança.

---


## Veredito por Camada

| Camada | Arquivo(s) | Nível | Observação |
|---|---|---|---|
| **Modelagem do banco** | `db_manager.py` | ✅ Sênior | Schema isolado, tipos corretos, timestamps, NullPool documentado |
| **Estrutura de módulos** | `src/` | ✅ Sênior+ | Separação clara de responsabilidades |
| **Pipeline LLM** | `agent_parser.py` | ✅ Sênior | Multi-provider, structured output Pydantic, prompt contextualizado |
| **FastAPI** | `api.py` | 🟡 Mid | Funcional, mas sem lock thread-safe e fire-and-forget sem observabilidade |
| **Streamlit** | `app_revisao.py` | 🟡 Mid | Sessão DB mal gerenciada na renderização, funciona mas é frágil |
| **Config** | `config/settings.py` | 🟡 Mid- | Mistura runtime config com dados de negócio e coordenadas de pixel |
| **Tratamento de erros** | Geral | 🔴 Junior | Sem `try/finally` em operações DB, sem logging estruturado |
| **Testabilidade** | Geral | 🔴 Junior | Zero testes, acoplamento direto dificulta unit tests |

---

## ✅ Pontos Fortes

### 1. Separação de módulos por responsabilidade
```
src/
  parsers/     ← entrada e extração (LLM)
  processors/  ← validação de negócio (CPF)
  database/    ← acesso a dados (SQLAlchemy)
  exporters/   ← saída (XLSX para NFSe)
  automation/  ← automação de UI (PyAutoGUI)
```
Cada módulo tem uma razão clara para existir. Não há "utils.py" genérico ou god objects.

### 2. Multi-provider LLM com fallback automático
```python
def get_llm():
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    elif os.getenv("ANTHROPIC_API_KEY") and ChatAnthropic:
        return ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
    elif os.getenv("GOOGLE_API_KEY") and ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    elif os.getenv("GROQ_API_KEY") and ChatGroq:
        return ChatGroq(model="llama3-70b-8192", temperature=0)
```
Vendor lock-in zero. Troca de provider sem alterar código de negócio.

### 3. Structured Output com Pydantic
`VendaExtraction` + `VendaExtractionList` garantem que o LLM retorne dados tipados e validados antes de chegarem ao banco. Sem parsing manual de JSON frágil.

### 4. NullPool no SQLAlchemy (decisão consciente)
```python
engine = create_engine(DATABASE_URL, poolclass=NullPool)
```
Comentário no código explica o motivo (evitar dados stale no Streamlit). Decisão técnica documentada = código sênior.

### 5. Schema isolado no PostgreSQL
```python
__table_args__ = {'schema': 'estudio_2026'}
```
Permite compartilhar o banco com outros serviços (n8n) sem risco de colisão de tabelas.

### 6. Janela de 15 minutos no buffer
Acumular mensagens antes de enviar ao LLM é uma decisão pragmática inteligente — resolve o problema de contexto fragmentado (Andrea manda 5 mensagens em sequência sobre a mesma cliente) sem precisar de lógica de correlação complexa.

### 7. ROADMAP.md com análise honesta
O próprio projeto já documentava os riscos reais antes dessa revisão. Autoconsciência técnica.

---

## 🟡 O que Funciona mas Precisa de Atenção

### `agent_parser.py` faz coisas demais (viola SRP)

O arquivo acumula quatro responsabilidades distintas:
- Acesso ao banco (repositório)
- Orquestração do LLM
- Lógica de negócio (`inferir_categoria`)
- Formatação de dados para persistência

**Ideal futuro:**
```
src/parsers/
  buffer_repository.py   ← CRUD do mensagens_buffer
  llm_service.py         ← chamada ao LLM, get_llm()
  sale_extractor.py      ← inferir_categoria, lógica de negócio
  agent_parser.py        ← orquestrador (usa os três acima)
```

### Sessão DB compartilhada no Streamlit

Em `app_revisao.py`, a mesma sessão aberta na renderização inicial é reusada nas operações de approve/reject. Se o Streamlit rerenderizar entre o `open` e o `commit`, o estado da sessão fica inconsistente.

**Padrão correto:** abrir e fechar sessão por operação atômica:
```python
# Em vez de uma sessão global na renderização:
if st.button("Aprovar"):
    with SessionLocal() as session:
        # toda a operação de aprovação aqui
        session.commit()
```

### Imports dentro de funções em `main.py`

```python
def preparar_nfse(vendas=None):
    from src.database.db_manager import SessionLocal, Venda, Cliente  # ← code smell
```
Imports no topo do arquivo são a convenção Python (PEP 8). Imports dentro de funções existem para resolver circular imports — aqui não é o caso.

---

## 🔴 Riscos Reais em Produção

### Race condition no `/process-buffer`

**Estado atual:** sem proteção alguma contra chamadas simultâneas.

**Risco descrito no ROADMAP (item 2):** correto, mas a solução sugerida (`global _processing = False`) ainda tem race condition — duas threads podem ler `False` simultaneamente antes de qualquer uma escrever `True`.

**Solução correta:**
```python
import threading

_lock = threading.Lock()

@app.post("/process-buffer")
async def trigger_process_buffer(force: bool = False, x_api_secret: str | None = Header(default=None)):
    _check_secret(x_api_secret)
    
    if not _lock.acquire(blocking=False):
        return {"status": "skip", "detail": "Já em processamento"}
    
    def run():
        try:
            process_buffer(force=force)
        finally:
            _lock.release()  # garante liberação mesmo se process_buffer lançar exceção
    
    threading.Thread(target=run, daemon=True).start()
    return {"status": "ok", "detail": "Processamento iniciado"}
```

### Leak de conexões DB

```python
def add_message_to_buffer(raw_message: str):
    session = SessionLocal()
    buffer = MensagensBuffer(texto=raw_message)
    session.add(buffer)
    session.commit()  # ← se falhar aqui...
    session.close()   # ← nunca executa
```

Se o commit lançar exceção (timeout de rede, constraint violation), a sessão vaza. Em produção contínua, isso esgota o pool de conexões do PostgreSQL.

---

## 🔵 Os 5 Pontos para Nível Sênior

> Detalhes de implementação estão no `ROADMAP.md` (itens 14–18).

### 1. Context manager para sessões DB (item 14)
Todos os pontos que usam `session = SessionLocal()` / `session.close()` devem virar `with SessionLocal() as session:`. Garante fechamento mesmo em exceções.

### 2. `threading.Lock()` em vez de `global bool` (item 15)
Substitui a solução sugerida no item 2 do ROADMAP pela implementação genuinamente thread-safe.

### 3. Logging estruturado em vez de `print()` (item 16)
```python
# config/logging_config.py
import logging

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )

# Em cada módulo:
logger = logging.getLogger(__name__)
logger.info("Processando %d mensagens do buffer", len(unprocessed))
logger.error("Erro ao processar LLM: %s", e, exc_info=True)
```
Com isso, `docker logs` passa a ter timestamps, levels e rastreamento de stack trace.

### 4. Testes unitários mínimos com pytest (item 17)
```
tests/
  test_cpf_validator.py
  test_categoria.py
  test_plano_mapping.py
```
Funções puras como `CPFValidator.validate()` e `inferir_categoria()` são testáveis sem mock nenhum. São também as que causam mais problemas silenciosos quando quebram.

### 5. Separar dados de negócio do `settings.py` (item 18)
```
config/
  settings.py           ← só runtime: DATABASE_URL, ports, timeouts
  business_data.json    ← PLANO_MAPPING, NFSE_DESCRICAO_TEMPLATES, CATEGORIA_MAPPING
  pyautogui_coords.json ← coordenadas por resolução (1920x1080, 1366x768, etc.)
```
`settings.py` tem 172 linhas, das quais ~140 são dados de negócio. Isso não é configuração — é uma tabela de lookup embutida no código.

---

## Conclusão

**O projeto é bem arquitetado para o contexto em que foi criado** — uma automação interna de estúdio fotográfico com usuário único e volume baixo. As decisões mais difíceis (buffer + LLM batch, NullPool, multi-provider) foram tomadas corretamente.

**O gap para nível sênior** está nas práticas de engenharia de software em volta do código de negócio: tratamento de erros defensivo, observabilidade, testabilidade e separação de concerns mais granular.

Aplicando os 5 itens acima (14–18 do ROADMAP), o projeto passa de um script bem estruturado para uma aplicação de produção auditável.

---

*Revisão por: Antigravity AI · Solicitado por: Andrea Sabbá Estúdio*
