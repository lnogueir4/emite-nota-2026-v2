# Roadmap de Melhorias — Emite Nota

Sugestões de melhoria identificadas após análise do sistema v2.2 em produção.  
Organizadas por prioridade e esforço de implementação.

---
### 0. revisar codigo com hardcodes e o que puder colocar no env
exemplo schema estudio_2026


## 🔴 Alta Prioridade — Riscos Reais Hoje

### 1. Sem feedback após processamento + sem visibilidade de erros

**Problema:** Dois problemas relacionados no mesmo fluxo:

1. **Sem retorno de resultado:** O endpoint `/process-buffer` dispara o LLM em uma thread separada (`daemon=True`) e responde `{"status": "ok"}` imediatamente. Se o LLM falhar ou retornar dados inválidos, ninguém é notificado.
2. **Sem feedback para a Andrea:** Ela digita "Processbuffer", o webhook dispara o endpoint — e fica sem saber se funcionou. Precisa abrir o Streamlit manualmente.

**Impacto:** Mensagens ficam no buffer como "não processadas" sem alertar ninguém.

**Solução sugerida:**
- Após o commit bem-sucedido em `process_buffer()`, usar a **Evolution API** para responder de volta no WhatsApp da Andrea:
```python
# No final de process_buffer(), após o commit:
import requests
requests.post(f"{EVOLUTION_URL}/message/sendText/{INSTANCE}", json={
    "number": PHONE,
    "text": f"✅ {len(result.vendas)} venda(s) extraída(s) e prontas para revisão.\nAcesse: https://app-notas.SEU_DOMINIO"
}, headers={"apikey": EVOLUTION_KEY})
```
- Em caso de erro do LLM, enviar mensagem de falha ao invés de silêncio:
```python
except Exception as e:
    requests.post(...)  # "❌ Erro ao processar buffer: {e}"
    logger.error(f"Erro LLM: {e}", exc_info=True)
```

**Variáveis necessárias no `.env`:** `EVOLUTION_URL`, `EVOLUTION_INSTANCE`, `EVOLUTION_KEY`, `PHONE`

---

### 2. Proteção contra execução paralela de `/process-buffer`

**Contexto atualizado:** O `/process-buffer` **não é mais chamado automaticamente pelo n8n** após cada mensagem. Ele só é acionado quando a Andrea digita "Processbuffer" manualmente. O risco de race condition por múltiplas chamadas simultâneas é muito menor.

**Risco residual:** Ainda é possível disparar duas execuções sobrepostas se o endpoint for chamado duas vezes em sequência rápida (ex: retry manual ou chamada dupla acidental).

**Solução:** Usar `threading.Lock()` com `acquire(blocking=False)` — implementado corretamente no item 15.

**Ação:** Nenhuma lógica de `_processing = False` com variável global é necessária. Ver item 15 para a implementação correta.

---

## 🟡 Média Prioridade — Qualidade e Rastreabilidade

### 4. Rastreabilidade: qual buffer gerou qual venda

**Problema atual:** O campo `raw_message` em `vendas_pendentes` armazena o texto de TODAS as mensagens do lote, não apenas as do cliente daquela venda. Se o lote tinha 10 mensagens de 5 clientes, todas as 5 vendas extraídas têm o mesmo `raw_message` gigante. Difícil saber de onde veio qual dado.

**Solução sugerida:** Adicionar coluna `mensagens_buffer_ids` (array de inteiros) em `vendas_pendentes` linkando os IDs do buffer usados na extração.

---

### 5. Deduplicação antes de inserir em `vendas_pendentes`

**Problema atual:** Se o mesmo cliente já tem uma venda `aguardando_aprovacao` e o buffer é processado de novo (ex: mensagem duplicada recebida), uma segunda venda é criada para o mesmo CPF.

**Solução sugerida:** Antes de inserir, verificar:
```python
existente = session.query(VendaPendente).filter(
    VendaPendente.cpf == ext_venda.cpf,
    VendaPendente.status == "aguardando_aprovacao"
).first()
if not existente:
    session.add(pendente)
```

---

### 6. Validação de CPF ainda no LLM (antes da tela)

**Problema atual:** O CPF só é validado quando a Andrea clica em "Aprovar". Se o LLM inventou dígitos, a Andrea tem que corrigir manualmente.

**Solução sugerida:** Após a extração do LLM, validar os CPFs em Python antes de salvar em `vendas_pendentes`. CPFs inválidos ficam com campo `cpf = ""` e um aviso no `raw_message`, para a Andrea preencher na tela.

---

### 7. Auto-refresh do Streamlit

**Problema atual:** O Streamlit não atualiza automaticamente enquanto a aba está aberta. A Andrea precisa clicar no botão "🔄 Recarregar" ou pressionar F5.

**Solução sugerida:** Adicionar auto-refresh a cada 30 segundos usando `st_autorefresh`:
```python
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30_000, key="auto")  # 30s
```
Ou via `time.sleep` + `st.rerun()` em um loop (menos elegante).

---

### 8. Aprovação em lote

**Problema atual:** Se a Andrea receber 8 vendas em um dia e todos os dados estiverem corretos, ela tem que clicar "Aprovar" 8 vezes individualmente.

**Solução sugerida:** Adicionar botão "✅ Aprovar Todas" no topo da página, que faz o loop internamente — aprovando apenas aquelas onde o CPF é válido.

---

## 🟢 Baixa Prioridade — Operacional e Futuro

### 9. Rotação e retenção de logs do Docker

**Problema atual:** `docker logs` cresce indefinidamente. Em uma VPS pequena, pode lotar o disco ao longo do tempo.

**Solução sugerida:** Configurar no `docker service update`:
```bash
docker service update \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  n8n_emite-nota
```

---



### 12. Docker Secrets (segurança avançada)

**Problema atual:** `OPENAI_API_KEY` e `DATABASE_URL` (com senha) estão em variáveis de ambiente visíveis via `docker service inspect`.

**Solução sugerida:** Migrar para **Docker Secrets**:
```bash
echo "sk-..." | docker secret create openai_api_key -
docker service update --secret-add openai_api_key n8n_emite-nota
```
Lido no código via `/run/secrets/openai_api_key` em vez de `os.getenv()`.

---

### 13. Migração de schema com Alembic

**Problema atual:** Qualquer alteração no banco (nova coluna, novo índice) é feita manualmente via `psql`. Sem histórico, sem rollback.

**Solução sugerida:** Adicionar Alembic ao projeto para gerenciar migrations:
```bash
pip install alembic
alembic init migrations
# Cada mudança de schema vira um arquivo versionado em migrations/versions/
```

---

## 🔵 Qualidade de Código e Arquitetura

> Identificados via análise técnica aprofundada (maio/2026). Ver `ARCHITECTURE_REVIEW.md` para detalhes completos.

### 14. Gerenciamento de sessão DB com context manager

**Problema atual:** Em `agent_parser.py` e `add_message_to_buffer`, as sessões do SQLAlchemy são abertas e fechadas manualmente (`session = SessionLocal()` / `session.close()`). Se ocorrer uma exceção antes do `close()`, a conexão fica vazando indefinidamente.

**Impacto:** Leak de conexões em produção sob carga ou erros de rede/LLM.

**Solução sugerida:** Trocar para context manager em todos os pontos:
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

### 15. Lock thread-safe no endpoint `/process-buffer`

**Contexto atualizado:** Como o `/process-buffer` só é acionado manualmente pela Andrea (digitando "Processbuffer"), não há mais chamada automática do n8n após cada mensagem. O risco de execuções paralelas é baixo, mas ainda real (ex: chamada acidental duplicada).

**Por que `global _processing = False` é inadequado:** Duas threads podem ler `_processing == False` ao mesmo tempo antes de qualquer uma setar `True` — race condition intrínseca de variáveis booleanas simples.

**Solução correta:** Usar `threading.Lock()` com `acquire(blocking=False)` — atomicamente seguro:
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

**Impacto da mudança de fluxo:** Com a remoção do trigger automático pós-webhook, essa proteção deixa de ser crítica e passa a ser uma boa prática de robustez.

---

### 16. Logging estruturado (substituir `print()`)

**Problema atual:** Todo o feedback de execução usa `print()` direto — sem levels (DEBUG/INFO/WARNING/ERROR), sem timestamps, sem rastreabilidade por módulo. Em produção via Docker, não é possível filtrar ou monitorar erros automaticamente.

**Solução sugerida:** Adicionar configuração central de logging e substituir `print()` nos módulos:
```python
# Em config/settings.py ou config/logging_config.py
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Em cada módulo:
logger = logging.getLogger(__name__)
logger.info("Mensagem adicionada ao buffer.")
logger.error(f"Erro ao processar LLM: {e}", exc_info=True)
```

---

### 17. Testes unitários mínimos

**Problema atual:** Zero cobertura de testes. As funções `CPFValidator.validate()` e `inferir_categoria()` são candidatas ideais — são puras, sem dependências externas, e críticas para o negócio.

**Solução sugerida:** Criar `tests/` com pelo menos:
```
tests/
  test_cpf_validator.py    # CPFs válidos, inválidos, todos iguais, tamanho errado
  test_categoria.py        # Mapeamento dos planos para categoria correta
```

Executar com `pytest` no CI ou antes de cada deploy.

---

### 18. Separar dados de negócio do `settings.py`

**Problema atual:** O `config/settings.py` mistura três tipos diferentes de informação:
- Configurações de runtime (paths, URLs) → correto estar aqui
- Dados de negócio (`PLANO_MAPPING`, `NFSE_DESCRICAO_TEMPLATES`) → deveriam ser dados externos
- Coordenadas de pixel do PyAutoGUI (`PYAUTOGUI_COORDINATES`) → extremamente frágeis aqui

**Impacto:** Qualquer mudança de resolução de tela ou novo plano do estúdio exige editar código Python.

**Solução sugerida:**
```
config/
  settings.py              # Apenas runtime (paths, DB URL, timeouts)
  business_data.json       # PLANO_MAPPING, NFSE_DESCRICAO_TEMPLATES, CATEGORIA_MAPPING
  pyautogui_coords.json    # Coordenadas por resolução, facilmente atualizável
```

---

### 19. Cliente local de emissão — NFSeEmitter lendo direto do banco

**Decisão arquitetural (maio/2026):** O PyAutoGUI precisa de navegador local com interface gráfica — não pode rodar num servidor headless. A solução é um script standalone que roda no **PC da Andrea**, conecta diretamente ao banco PostgreSQL do servidor e emite as notas.

**Estado atual:**
- `NFSeEmitter` lê um arquivo XLSX gerado previamente pelo `NFSePreparer`
- Requer dois comandos: `python main.py preparar` → `python main.py emitir`
- O XLSX pode ficar desatualizado se aprovações ocorrerem após a geração

**Estado alvo:**
```
PC da Andrea (emitir_client.py)
    │
    ├─ conecta ao PostgreSQL do servidor via DATABASE_URL remoto
    ├─ consulta: SELECT * FROM vendas WHERE status = 'pendente'
    ├─ roda PyAutoGUI → Chrome → nfse.gov.br (uma nota por vez)
    └─ UPDATE vendas SET status='emitida', num_nota=... WHERE id=...
```

**Mudanças necessárias no código:**

| Arquivo | Mudança |
|---|---|
| `src/automation/nfse_emitter.py` | Substituir `_carregar_vendas()` (lê XLSX) por método que consulta `SessionLocal` diretamente |
| `emitir_client.py` | Novo script standalone para o PC — importa `NFSeEmitter` e `db_manager`, sem depender do `main.py` do servidor |
| `src/exporters/nfse_preparer.py` | Tornar obsoleto / remover do fluxo principal |
| `.env` (PC da Andrea) | `DATABASE_URL=postgresql://postgres:SENHA@IP_DO_SERVIDOR:3999/emitenota` |

**Pré-requisito de infraestrutura:** O PostgreSQL do servidor escuta na porta **3999** (porta customizada). O cliente deve apontar diretamente para essa porta:
```bash
# Conexão direta (firewall liberado para o IP da Andrea):
DATABASE_URL=postgresql://postgres:SENHA@IP_VPS:3999/emitenota

# OU via SSH tunnel (mais seguro — mapeia porta local para a remota):
ssh -L 3999:localhost:3999 usuario@IP_VPS
# Então no .env local:
DATABASE_URL=postgresql://postgres:SENHA@localhost:3999/emitenota
```

---

## Resumo do Roadmap

| # | Melhoria | Prioridade | Esforço | Status |
|---|---|---|---|---|
| 1 | Feedback pós-processamento (erro LLM + resposta WhatsApp) | 🔴 Alta | Médio | ✅ Aplicado |
| 2 | Proteção contra execução paralela do `/process-buffer` | 🔴 Alta | Baixo | ✅ Aplicado |
| 3 | Rastreabilidade buffer → venda | 🟡 Média | Médio | ✅ Aplicado |
| 4 | Deduplicação por CPF antes de inserir | 🟡 Média | Baixo | — |
| 5 | Validação de CPF antes de salvar | 🟡 Média | Baixo | ✅ Aplicado |
| 6 | Auto-refresh do Streamlit (30s) | 🟡 Média | Baixo | — |
| 7 | Aprovação em lote | 🟡 Média | Médio | — |
| 8 | Rotação de logs do Docker | 🟢 Baixa | Baixo | — |
| 9 | Docker Secrets para chaves de API | 🟢 Baixa | Médio | — |
| 10 | Migrations com Alembic | 🟢 Baixa | Alto | — |
| 11 | Context manager para sessões DB | 🔵 Arquitetura | Baixo | ✅ Aplicado |
| 12 | Lock thread-safe (`threading.Lock`) | 🔵 Arquitetura | Baixo | ✅ Aplicado |
| 13 | Logging estruturado (substituir print) | 🔵 Arquitetura | Baixo | ✅ Aplicado |
| 14 | Testes unitários mínimos (pytest) | 🔵 Arquitetura | Médio | — |
| 15 | Separar dados de negócio do settings.py | 🔵 Arquitetura | Médio | — |
| 16 | Cliente local de emissão (NFSeEmitter DB-first, porta 3999) | 🔵 Arquitetura | Alto | ✅ Aplicado |

---

## 📦 Histórico de Implementação

### Sprint 1 — 2026-05-02

Itens executados desta sessão:

| Item | O que foi feito | Arquivos modificados |
|---|---|---|
| #1 — Feedback WhatsApp | `process_buffer()` agora envia mensagem via Evolution API após sucesso ou erro do LLM. Falha silenciosa se variáveis não configuradas. | `src/parsers/agent_parser.py` |
| #2 — Lock thread-safe | `api.py` substitui lógica de `global _processing` por `threading.Lock()` com `acquire(blocking=False)`. Retorna `{"status": "skip"}` se já em andamento. | `api.py` |
| #3 — Rastreabilidade buffer → venda | Campo `mensagens_buffer_ids` (JSON `"[1,2,3]"`) adicionado em `VendaPendente`. Cada venda sabe exatamente de quais mensagens do buffer foi extraída. | `src/database/db_manager.py`, `src/parsers/agent_parser.py`, `migrations/add_buffer_ids_to_vendas_pendentes.sql` |
| #5 — Validação de CPF | Antes de salvar em `vendas_pendentes`, o CPF é validado com `CPFValidator`. CPF inválido → campo `cpf=""` + aviso incluído na notificação WhatsApp. | `src/parsers/agent_parser.py` |
| #11 — Context manager DB | Todas as sessões SQLAlchemy trocadas para `with SessionLocal() as session:` — elimina leak de conexão em caso de exceção. | `src/parsers/agent_parser.py` |
| #12 — Lock thread-safe | Ver item #2 acima. | `api.py` |
| #13 — Logging estruturado | `print()` substituído por `logging.getLogger(__name__)` com format `asctime [LEVEL] modulo: mensagem` em `agent_parser.py` e `api.py`. | `src/parsers/agent_parser.py`, `api.py` |
| #16 — Cliente local emissão | Novo `emitir_client.py` standalone para o PC da Andrea. Conecta ao banco na porta 3999, lê `vendas` com `status='pendente'`, emite via PyAutoGUI e atualiza `status='emitida'`. Suporta `--dry-run`. | `emitir_client.py` (novo), `.env.example` |

**Pré-requisito de deploy:** Executar migration SQL antes de subir nova versão:
```bash
docker exec -it <container_banco> psql -U postgres n8n < migrations/add_buffer_ids_to_vendas_pendentes.sql
```

**Variáveis de ambiente novas (adicionar ao `.env` do servidor):**
```
EVOLUTION_URL=https://sua-evolution-api.com
EVOLUTION_INSTANCE=nome_da_instancia
EVOLUTION_KEY=sua_api_key_evolution
PHONE=5592999999999
```

