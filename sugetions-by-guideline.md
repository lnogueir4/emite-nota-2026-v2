# Sugestões de Melhoria (Baseado na Skill de Engenharia)

Avaliando o projeto `emite-nota-2026-v2` sob a lente das novas diretrizes (Simplicity First, Surgical Changes, etc.), o projeto está com uma arquitetura muito mais sólida agora que migrou para API + Banco de Dados + Webhooks. Porém, a transição deixou alguns "restos mortais" (código órfão) que ferem o princípio de manter as coisas simples.

Aqui estão as sugestões do que mudar para melhor:

## 1. Simplicity First (Limpeza de Código Morto)
**O que está sobrando:**
- Em `config/settings.py`: As constantes `INPUT_DIR`, `OUTPUT_DIR`, `DATA_DIR` e as criações de diretório (`mkdir(exist_ok=True)`) estão lá sem necessidade. Também estão lá `VENDAS_ESTUDIO_FILE`, `WHATSAPP_TXT_FILE` e `NFSE_OUTPUT_FILE`.
- Isso responde à sua pergunta: **Não, não precisa mais das pastas data, input e output.** A arquitetura nova não usa arquivos locais de texto ou planilhas. Tudo é Banco de Dados. Manter isso cria complexidade fantasma ("configurability that wasn't requested").

## 2. Surgical Changes (Limpando as próprias bagunças / Órfãos)
**O que está sobrando:**
- Em `src/automation/nfse_emitter.py`: Quando mudamos para o `emitir_client.py` lendo direto do banco de dados, o método `_carregar_vendas()` (que importava o `openpyxl` e lia a planilha) e o `emitir_notas()` antigo ficaram **órfãos**.
- **Regra quebrada:** *"Remove imports/variables/functions that YOUR changes made unused."*
- **Sugestão:** O `nfse_emitter.py` deveria ser simplificado apenas para receber o dicionário com os dados da nota e fazer a automação web, removendo completamente a dependência de ler arquivos XLSX. 

## 3. Think Before Coding (Redundância de Modelos)
**O que pode melhorar:**
- O script `emitir_client.py` recriou localmente as classes `Venda` e `Cliente` do SQLAlchemy (`Base = declarative_base()...`). 
- **Tradeoff:** Isso foi feito no passado para que o script não dependesse do `db_manager.py` do servidor (caso ele fosse levado para um pendrive ou pc isolado). Mas como o arquivo já mora na pasta do projeto e importa `config.settings`, ele poderia simplesmente importar `Venda` e `Cliente` de `src.database.db_manager`, removendo cerca de 30 linhas de código redundante.
- **Pergunta:** O script vai continuar morando dentro da pasta desse repositório no PC da Andrea, ou vai ficar solto em uma pasta avulsa? Se for ficar na pasta do projeto, podemos remover essa duplicação de modelos.

## 4. Goal-Driven Execution (Testabilidade)
**O que pode melhorar:**
- A lógica de inferência de categoria via LLM e o mapeamento no `config/settings.py` (`PLANO_MAPPING`) não possuem um teste simples. 
- Para garantir que "A IA extrai a venda corretamente", deveríamos ter um arquivo rápido (ex: `test_prompt.py`) contendo apenas 3 cenários falsos de mensagens do WhatsApp, que rodamos para ver se o LLM converte as categorias certo antes de mandar pro ar.

---

> Nenhum arquivo foi modificado. Se quiser que eu execute a faxina (itens 1, 2 e 3), é só avisar!
