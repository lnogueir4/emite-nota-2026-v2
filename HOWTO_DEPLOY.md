# How-To: Deploy do Emite Nota (Docker Swarm / Easypanel)

## Pré-requisitos

- VPS com Docker Swarm ativo e Easypanel instalado
- Container `n8n-banco` (pgvector/PostgreSQL) rodando na rede `n8n`
- n8n acessível e com fluxo configurado
- Evolution API recebendo mensagens do WhatsApp da Andrea

---

## 1. Primeira Configuração

### 1.1 Configurar as Variáveis de Ambiente no Easypanel

No Easypanel → serviço `emite-nota` → aba **Ambiente**, adicione:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | `postgresql://postgres:SENHA@n8n-banco:5432/n8n` |
| `STREAMLIT_USER` | `admin` |
| `STREAMLIT_PASSWORD` | `sua_senha_aqui` |
| `API_SECRET` | `chave_secreta_para_o_n8n` |
| `OPENAI_API_KEY` | `sk-...` (ou `GROQ_API_KEY`, `GOOGLE_API_KEY`) |

> ⚠️ O hostname `n8n-banco` é o nome interno do container PostgreSQL dentro da rede Docker. Use `n8n-banco`, não `localhost`.

### 1.2 Build e Deploy Inicial

Acesse a VPS via SSH e execute:

```bash
cd /root/codeprojects/emite-nota-2026-v2
docker build -t emite-nota:latest .
docker service update --image emite-nota:latest --force n8n_emite-nota
```

### 1.3 Criar as Tabelas no Banco

Execute uma única vez para criar o schema e as tabelas:

```bash
docker exec -it $(docker ps -q --filter name=n8n_banco) psql -U postgres -d n8n -c "
CREATE SCHEMA IF NOT EXISTS estudio_2026;
CREATE TABLE IF NOT EXISTS estudio_2026.clientes (...);
-- etc (ver db_manager.py para o schema completo)
"
```

Ou rode diretamente pelo Python dentro do container:

```bash
docker exec $(docker ps -q --filter name=n8n_emite-nota) python3 -c "
from src.database.db_manager import Base, engine
Base.metadata.create_all(bind=engine)
print('Tabelas criadas!')
"
```

---

## 2. Deploy de Atualizações (Rotina)

**Quando você deve fazer isso?**
Toda vez que você alterar algum arquivo de código Python (`.py`), `requirements.txt` ou `Dockerfile` no seu servidor.

**Por que é necessário?**
Se você não rodar o build e o update, o Docker vai continuar rodando na memória do servidor a versão antiga do seu código que estava salva na imagem da última vez que você construiu. O código fonte no disco não é lido diretamente pelo container em tempo de execução.

**Atenção:** Nunca clique em "Implantar" no Easypanel (isso sobrescreve as configs do Swarm). Use sempre o fluxo abaixo pelo terminal:
```bash
cd /root/codeprojects/emite-nota-2026-v2

# 1. Build da nova imagem
docker build -t emite-nota:latest .

# 2. Atualiza o serviço no Swarm
docker service update --image emite-nota:latest --force n8n_emite-nota
```

Para verificar se subiu corretamente:

```bash
docker service ps n8n_emite-nota   # Vê o status das tasks
docker logs $(docker ps -q --filter name=n8n_emite-nota) --tail 30
```

---

## 3. Alterar Variáveis de Ambiente (Senha, Chaves de API, etc.)

```bash
# Exemplo: trocar a senha do Streamlit
docker service update \
  --env-add STREAMLIT_PASSWORD=nova_senha_aqui \
  --force n8n_emite-nota
```

> Isso substitui apenas a variável informada. As outras permanecem intactas.

---

## 4. Configurar o n8n

### Fluxo: Receber mensagem → Processar

**Node 1 — Webhook (Evolution API)**
- Deixe o n8n receber o POST da Evolution API

**Node 2 — HTTP Request: salvar no buffer**

| Campo | Valor |
|---|---|
| Method | `POST` |
| URL | `https://api-notas.SEU_DOMINIO/webhook` |
| Headers | `x-api-secret: SUA_CHAVE` |
| Body (JSON) | `{ "message": "{{ $json.body.data.message.conversation }}" }` |

**Node 3 — HTTP Request: processar com IA**

| Campo | Valor |
|---|---|
| Method | `POST` |
| URL | `https://api-notas.SEU_DOMINIO/process-buffer?force=true` |
| Headers | `x-api-secret: SUA_CHAVE` |

### Credencial Reutilizável no n8n (recomendado)

Em vez de colocar o `x-api-secret` hardcoded, crie uma **Credential** no n8n:

1. Settings → Credentials → New → **Header Auth**
2. Name: `Emite Nota API`
3. Header: `x-api-secret` | Value: `SUA_CHAVE`

Depois selecione essa credential nos nós HTTP Request (campo Authentication).

---

## 5. O que Acontece se a VPS Reiniciar

**Docker Swarm reinicia os serviços automaticamente.** Nenhum dado é perdido porque:

- O código está na **imagem Docker** (não no container)
- Os dados estão no volume do **container `n8n-banco`** (PostgreSQL persistente)
- As variáveis de ambiente estão **no Swarm** (persistentes)

> ✅ Um reboot simples da VPS **não exige nenhuma ação manual**.

---

## 6. Logs e Diagnóstico

```bash
# Logs do container (Streamlit + API)
docker logs $(docker ps -q --filter name=n8n_emite-nota) --tail 50

# Verificar processos rodando dentro do container
docker top $(docker ps -q --filter name=n8n_emite-nota)

# Consultar tabelas direto no banco
docker exec -it $(docker ps -q --filter name=n8n_banco) psql -U postgres -d n8n -c \
  "SELECT id, nome, status FROM estudio_2026.vendas_pendentes ORDER BY id;"

docker exec -it $(docker ps -q --filter name=n8n_banco) psql -U postgres -d n8n -c \
  "SELECT id, processada, criado_em FROM estudio_2026.mensagens_buffer ORDER BY id DESC LIMIT 10;"
```

---

## 7. Reconstrução Completa (Disaster Recovery)

Se precisar recriar o serviço do zero:

```bash
# 1. Build da imagem
cd /root/codeprojects/emite-nota-2026-v2
docker build -t emite-nota:latest .

# 2. Criar o serviço no Swarm (se não existir)
docker service create \
  --name n8n_emite-nota \
  --network n8n \
  --publish published=8501,target=8501,mode=host \
  --env DATABASE_URL=postgresql://postgres:SENHA@n8n-banco:5432/n8n \
  --env STREAMLIT_USER=admin \
  --env STREAMLIT_PASSWORD=sua_senha \
  --env API_SECRET=chave_secreta \
  --env OPENAI_API_KEY=sk-... \
  emite-nota:latest

# 3. Configurar rota no Traefik (via Easypanel ou labels do serviço)
```
