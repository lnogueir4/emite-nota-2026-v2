# Emite Nota — Pipeline de Emissão de NFSe (v2.2)

Sistema automatizado para capturar vendas via WhatsApp, processar os dados com Inteligência Artificial, aprovar via painel administrativo (Streamlit) e emitir Notas Fiscais de Serviço Eletrônicas (NFSe) no portal do governo utilizando PyAutoGUI.

## Fluxo do Sistema

```mermaid
graph TD
    A[WhatsApp - Andrea] -->|Mensagem| B(Evolution API)
    B -->|Webhook| C[n8n Workflow]
    C -->|POST /webhook| D[FastAPI api.py :8502]
    D -->|Salva msg bruta| E[(PostgreSQL: mensagens_buffer)]

    F[n8n: POST /process-buffer?force=true] -->|Dispara extração| G[FastAPI api.py]
    G -->|Envia bloco ao LLM| H[OpenAI / Gemini / Groq]
    H -->|Extrai vendas estruturadas| I[(PostgreSQL: vendas_pendentes)]

    I --> J[Streamlit app_revisao.py :8501]
    J -->|Revisão e Aprovação| K[(PostgreSQL: clientes + vendas)]

    K --> L[PC Windows: python main.py preparar]
    L -->|Gera XLSX local| M[PC Windows: python main.py emitir]
    M -->|PyAutoGUI| N[Portal NFSe Governo]
```

## Arquitetura de Deploy (Produção)

O sistema roda em um único container Docker dentro do **Docker Swarm** no Easypanel.  
Um script `start.sh` sobe dois processos em paralelo:

| Processo | Porta | Função |
|---|---|---|
| `streamlit run app_revisao.py` | **8501** | Painel de revisão e aprovação |
| `uvicorn api:app` | **8502** | API HTTP para integração com n8n |

O deploy é feito **manualmente via terminal** (não usar o botão "Implantar" do Easypanel):

```bash
cd /root/codeprojects/emite-nota-2026-v2
docker build -t emite-nota:latest .
docker service update --image emite-nota:latest --force n8n_emite-nota
```

## Variáveis de Ambiente (Configuradas no Docker Swarm)

As variáveis **não vêm do `.env`** (que está no `.dockerignore`). Elas são configuradas na aba **Ambiente** do Easypanel, ou via:

```bash
docker service update \
  --env-add DATABASE_URL=postgresql://postgres:SENHA@n8n-banco:5432/n8n \
  --env-add STREAMLIT_USER=admin \
  --env-add STREAMLIT_PASSWORD=sua_senha \
  --env-add OPENAI_API_KEY=sk-... \
  --env-add API_SECRET=chave_secreta_n8n \
  n8n_emite-nota
```

> ⚠️ Para alterar a senha do Streamlit, use o comando acima — não edite o `.env` local.

## Integração com n8n

O n8n recebe todas as mensagens da Andrea via Webhook da Evolution API e decide o que fazer com um nó **IF**:

```
Webhook (Evolution API)
    ↓
IF: mensagem.toLowerCase().trim() === "processbuffer"
    ├─ SIM → HTTP Request: POST /process-buffer?force=true
    └─ NÃO → HTTP Request: POST /webhook  (salva no buffer)
                ↓
          HTTP Request: POST /process-buffer  (sem force — respeita 15 min)
```

**Por que dois modos?**
- **Modo manual (Processbuffer):** A Andrea digita "Processbuffer" no WhatsApp quando terminar de mandar todas as mensagens do dia. Dispara o processamento imediato com `?force=true`.
- **Modo automático (após cada mensagem):** O n8n tenta processar após cada mensagem recebida, mas sem `force=true` o sistema aguarda 15 min de silêncio — garante que mensagens fragmentadas do mesmo cliente sejam agrupadas antes de ir ao LLM.

### Configuração dos nós HTTP Request

**Nó: Salvar no buffer (branch NÃO)**

| Campo | Valor |
|---|---|
| Method | `POST` |
| URL | `https://api-notas.SEU_DOMINIO/webhook` |
| Header | `x-api-secret: SUA_CHAVE` |
| Body (JSON) | `{ "message": "{{ $json.body.data.message.conversation }}" }` |

**Nó: Processar automaticamente (logo após salvar)**

| Campo | Valor |
|---|---|
| Method | `POST` |
| URL | `https://api-notas.SEU_DOMINIO/process-buffer` |
| Header | `x-api-secret: SUA_CHAVE` |

**Nó: Processar sob demanda (branch SIM — "Processbuffer")**

| Campo | Valor |
|---|---|
| Method | `POST` |
| URL | `https://api-notas.SEU_DOMINIO/process-buffer?force=true` |
| Header | `x-api-secret: SUA_CHAVE` |

> 💡 Use a expressão `{{ $json.body.data.message.conversation.toLowerCase().trim() === "processbuffer" }}` no IF para aceitar qualquer variação de maiúsculas/espaços.

### Credencial Reutilizável no n8n (recomendado)

Em vez de colocar o `x-api-secret` hardcoded, crie uma **Credential** no n8n:

1. Settings → Credentials → New → **Header Auth**
2. Name: `Emite Nota API`
3. Header: `x-api-secret` | Value: `SUA_CHAVE`

Depois selecione essa credential nos nós HTTP Request (campo Authentication).

## Endpoints da API (api.py — porta 8502)

| Endpoint | Método | Descrição |
|---|---|---|
| `/webhook` | POST | Recebe mensagem bruta e salva em `mensagens_buffer` |
| `/process-buffer` | POST | Dispara extração via LLM e popula `vendas_pendentes` |
| `/health` | GET | Health check |

Todos os endpoints exigem o header `x-api-secret`.

## Painel de Revisão (Streamlit)

Acesse via `https://app-notas.SEU_DOMINIO` (porta 8501).

- Exibe todas as vendas extraídas pela IA com status `aguardando_aprovacao`
- Permite editar manualmente qualquer campo antes de aprovar
- **Aprovar Venda**: valida CPF → cria/atualiza cliente → cria venda oficial → some da tela
- **Rejeitar / Descartar**: marca como `rejeitada` → some da tela (sem salvar nada)

## Emissão de Notas (PC Windows da Andrea)

A automação de envio de NFSe roda **localmente** no PC (Windows) porque precisa controlar o mouse e o teclado. O banco de dados fica seguro no servidor.

Para conectar o PC ao banco sem expor o banco para a internet, usamos um **Túnel SSH**.

### Passo 1: Abrir o Túnel SSH
No Windows (Prompt de Comando, PowerShell ou MINGW64), execute:
```bash
ssh -N -L 3999:localhost:3999 root@IP_DO_SERVIDOR
```
> **Nota:** A janela ficará "travada" com o cursor piscando. Isso é normal! O túnel está aberto enquanto essa janela não for fechada.

### Passo 2: Configurar a conexão
No PC Windows, crie um arquivo `.env` na mesma pasta do projeto contendo:
```ini
DATABASE_URL=postgresql://postgres:SENHA_DO_BANCO@localhost:3999/n8n
```

### Passo 3: Emitir as Notas
Sem fechar a janela do túnel, abra **um novo terminal** na mesma pasta e execute:
```bash
python emitir_client.py
```
*(Se quiser apenas testar a conexão sem abrir o Chrome, pode usar `python emitir_client.py --dry-run`)*

O robô pedirá uma confirmação, abrirá o Chrome no portal e emitirá as notas pendentes (aprovadas via Dashboard Streamlit).

## Banco de Dados (Schema: `estudio_2026`)

| Tabela | Função |
|---|---|
| `mensagens_buffer` | Rascunho: texto bruto recebido do WhatsApp |
| `vendas_pendentes` | Fila de revisão: dados extraídos pela IA aguardando aprovação |
| `clientes` | Cadastro definitivo de clientes (PK: CPF) |
| `vendas` | Histórico oficial de vendas aprovadas |

## Troubleshooting

**Mensagens não aparecem em `vendas_pendentes` após `/process-buffer`:**
- Verifique os logs: `docker logs $(docker ps -q --filter name=n8n_emite-nota) --tail 30`
- Se aparecer `Aguardando janela de 15 min`, use `?force=true` na URL.

**O robô PyAutoGUI não preenche no lugar certo:**
- Confirme se a escala do monitor Windows está em 100% e o zoom do Chrome em 50%.
- Recalibre as coordenadas em `config/settings.py` → `PYAUTOGUI_COORDINATES`.

**A IA está gerando duplicatas:**
- O prompt instrui a IA a nunca criar dois registros para o mesmo cliente.
- Se ainda ocorrer, delete os registros duplicados direto no banco e reprocesse.
