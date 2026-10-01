# CLAUDE.md

Este arquivo orienta o Claude Code (claude.ai/code) ao trabalhar com o código deste repositório.

## O que é este projeto

Pipeline que transforma mensagens de venda enviadas por WhatsApp de um estúdio fotográfico (Estúdio Andréa Sabbá) em NFSe (Nota Fiscal de Serviço Eletrônica). Código, comentários, logs, colunas do banco e documentação estão em português — mantenha o código novo em português também.

Fluxo: WhatsApp → Evolution API → n8n → FastAPI `/webhook` (texto bruto em `mensagens_buffer`) → `/process-buffer` (o LLM extrai vendas estruturadas para `vendas_pendentes`) → painel de revisão Streamlit (aprovar → `clientes` + `vendas` com `status='pendente'`) → `emitir_client.py` no PC Windows da Andrea controla o Chrome via PyAutoGUI no nfse.gov.br → `vendas.status='emitida'`.

## Dois ambientes de execução

O código roda em duas máquinas fisicamente separadas, que compartilham apenas o banco PostgreSQL (schema `estudio_2026`):

- **Servidor (Docker Swarm / Easypanel)**: um único container; o `start.sh` sobe `uvicorn api:app` na porta 8502 em background e `streamlit run app_revisao.py` na 8501 em foreground. O painel de revisão (Streamlit) fica em https://emite-nota.xyz.easypanel.host/. As variáveis de ambiente vêm da configuração do serviço no Swarm, não do `.env` (o `.env` está no `.dockerignore`).
- **PC Windows da Andrea**: `emitir_client.py` + `src/automation/nfse_emitter.py` + scripts de calibração. Conecta ao banco do servidor por túnel SSH (`DATABASE_URL=...@localhost:3999/n8n` num `.env` local). O PyAutoGUI precisa de uma tela real, então a emissão nunca pode rodar no servidor.

O `emitir_client.py` define propositalmente suas próprias cópias mínimas dos modelos ORM `Venda`/`Cliente`, em vez de importar `src/database/db_manager.py`. Ao alterar o schema de `vendas` ou `clientes`, atualize juntos `db_manager.py`, `emitir_client.py` e `migrations/schema_consolidado.sql`.

## Comandos

```bash
pip install -r requirements.txt

# Componentes do servidor localmente (exigem DATABASE_URL; o db_manager cria o engine na importação)
uvicorn api:app --host 0.0.0.0 --port 8502
streamlit run app_revisao.py --server.port=8501

# Cliente de emissão (PC Windows)
python emitir_client.py --dry-run   # só lista as vendas pendentes; testa a conexão com o banco
python emitir_client.py             # emissão real — assume o controle do mouse/teclado

# Calibração das coordenadas do PyAutoGUI (grava de volta em config/settings.py via regex)
python calibrar.py --tracker        # mostra x,y em tempo real
python calibrar.py --wizard         # um popup por campo, todos os campos
# Recalibradores parciais de uma etapa/campo: calibrar_tomador.py, calibrar_etapa3.py, pegar_*.py

# Deploy em produção (na VPS; não use o botão "Implantar" do Easypanel)
docker build -t emite-nota:latest .
docker service update --image emite-nota:latest --force n8n_emite-nota
```

Não há suíte de testes nem linter configurados. O `test_db.py` é um script avulso de consulta ao banco (lê `TESTE_DATABASE_URL`). Schema para um banco do zero: `migrations/schema_consolidado.sql` (sem Alembic; as tabelas usam triggers para `atualizado_em`).

## Detalhes importantes

- **Autenticação da API**: todo endpoint compara o header `x-api-secret` com `API_SECRET` (a checagem é ignorada se `API_SECRET` estiver vazio). O `/process-buffer` executa `process_buffer()` numa thread em background protegida por um `threading.Lock` não bloqueante — chamadas simultâneas retornam `{"status": "skip"}`.
- **Extração via LLM** (`src/parsers/agent_parser.py`): `get_llm()` escolhe o provedor conforme a chave de API configurada (OpenAI → Anthropic → Google → Groq) e usa `with_structured_output(VendaExtractionList)` do LangChain. As descrições dos campos do modelo Pydantic `VendaExtraction` fazem parte do prompt — editá-las muda o comportamento da extração. Regras de negócio no prompt: unificar mensagens do mesmo cliente em uma única venda; plano/categoria vêm só da linha que começa com "Fez ensaio ...". CPFs inválidos são salvos em branco para correção manual. Todas as mensagens não processadas do buffer são marcadas `processada=True` na mesma transação.
- **Validação de e-mail** (`src/processors/email_validator.py`) roda em três pontos: na extração (mantém o valor e avisa no WhatsApp), na aprovação do Streamlit (bloqueia, junto com o CPF) e no `emitir_client.py` (pula a venda sem emitir). E-mail vazio é permitido. Typos de domínio conhecidos ficam nos dicionários `DOMINIOS_TYPO`/`TERMINACOES_TYPO` da classe.
- **O parâmetro `force` é resquício**: o README descreve uma janela de 15 minutos de silêncio, mas `process_buffer()` não a implementa mais; `force` só é aceito por compatibilidade com o n8n.
- **Notificação por WhatsApp** após o processamento lê `EVOLUTION_URL`, `EVOLUTION_INSTANCE`, `EVOLUTION_KEY` e `PHONE` (atenção: o `.env.example` documenta `ANDREA_PHONE`, mas o código lê `PHONE`). Configuração ausente = pula silenciosamente com um warning no log.
- **Valores de status**: `vendas_pendentes.status` ∈ `aguardando_aprovacao | aprovada | rejeitada`; `vendas.status` ∈ `pendente | emitida`.
- **Mapeamentos de negócio** ficam em `config/settings.py`: `PLANO_MAPPING`, `CATEGORIA_MAPPING`, `NFSE_DESCRICAO_TEMPLATES` (descrição da nota por chave de categoria), valores fixos da NFSe (`municipio`, `codtn`, `nbs`) e `PYAUTOGUI_COORDINATES`.
- **A emissão via PyAutoGUI é baseada em coordenadas e frágil**: pressupõe escala do Windows em 100% e zoom do Chrome em 50%. O fluxo do portal tem 4 etapas (dados básicos/tomador → serviço → valores → emitir); cada clique corresponde a uma chave em `PYAUTOGUI_COORDINATES`. Após cada nota, um popup pergunta se ela foi realmente emitida — só "Sim, Emitida" atualiza o banco; qualquer outra resposta interrompe a execução. O `num_nota` ainda não é capturado (é salvo como string vazia). Se adicionar uma chave de coordenada, inclua-a também nas listas de campos dos scripts de calibração e mantenha o formato `"chave": (x, y)`, pois os calibradores reescrevem o arquivo via regex.
- A pasta `old/` guarda o pipeline antigo baseado em XLSX (`main.py`, `nfse_preparer.py`, parser de texto do WhatsApp) e está no `.gitignore` — não construa nada em cima dela. O diagrama do README ainda cita `main.py preparar/emitir`; o caminho atual é o `emitir_client.py`.

## Documentação de referência no repositório

`README.md` (configuração dos nós do n8n, endpoints, passo a passo do túnel SSH), `HOWTO_DEPLOY.md`, `ARCHITECTURE_REVIEW.md`, `PLANO_IMPLEMENTACAO.md` (ADRs), `ROADMAP.md` (backlog priorizado + histórico de implementação), `documentacao/emite-nota-arquitetura.drawio`.
