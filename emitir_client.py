"""
emitir_client.py — Cliente standalone de emissão de NFSe para o PC da Andrea.

Roda LOCALMENTE no PC da Andrea (Windows com Chrome e acesso ao portal nfse.gov.br).
Conecta diretamente ao banco PostgreSQL do servidor via DATABASE_URL (porta 3999).
NÃO depende do main.py do servidor nem de arquivo XLSX.

Fluxo:
  1. Conecta ao banco remoto
  2. Busca vendas aprovadas com status='pendente' (aprovadas no Streamlit)
  3. Emite cada nota via PyAutoGUI no Chrome
  4. Atualiza status='emitida' e num_nota no banco

Configuração (.env no mesmo diretório deste script, ou variável de ambiente):
  DATABASE_URL=postgresql://postgres:SENHA@IP_DO_SERVIDOR:xxxx/n8n
  (ou via SSH tunnel local: DATABASE_URL=postgresql://postgres:SENHA@localhost:xxxx/n8n)

Uso:
  python emitir_client.py           # emite todas as pendentes
  python emitir_client.py --dry-run # lista vendas sem emitir (teste de conectividade)
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# Adiciona o diretório pai ao path para importar config e src
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

from config.settings import (
    NFSE_PORTAL_URL, PYAUTOGUI_COORDINATES,
    PAUSE_BETWEEN_ACTIONS, PAGE_TRANSITION_DELAY, SCROLL_AMOUNT,
    NFSE_DESCRICAO_TEMPLATES, municipio, codtn, nbs,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("emitir_client")


# ── Banco de dados ───────────────────────────────────────────────────────────

def _build_session():
    """Cria engine e sessionmaker apontando para o banco remoto (porta 3999)."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL não configurado. Defina no .env deste diretório.")
        sys.exit(1)

    logger.info(f"Conectando ao banco: {db_url.split('@')[-1]}")  # oculta senha no log
    engine = create_engine(db_url, poolclass=NullPool, connect_args={"connect_timeout": 10})

    # Teste rápido de conectividade
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexão com o banco OK.")
    except Exception as e:
        logger.error(f"Falha ao conectar ao banco: {e}")
        sys.exit(1)

    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Modelo mínimo para leitura (sem importar db_manager do servidor) ─────────

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean

Base = declarative_base()

class Venda(Base):
    """Espelho mínimo da tabela vendas para leitura/atualização."""
    __tablename__ = "vendas"
    __table_args__ = {"schema": "estudio_2026"}

    id          = Column(Integer, primary_key=True)
    cliente_cpf = Column(String)
    plano       = Column(String)
    plano_ajustado = Column(String)
    categoria   = Column(String)
    valor       = Column(Float)
    data_venda  = Column(Date)
    meio_pagto  = Column(String)
    parcelas    = Column(Integer)
    num_nota    = Column(String)
    status      = Column(String)  # 'pendente' | 'emitida'
    data_nota   = Column(Date)

class Cliente(Base):
    """Espelho mínimo da tabela clientes para lookup de email/nome."""
    __tablename__ = "clientes"
    __table_args__ = {"schema": "estudio_2026"}

    cpf   = Column(String, primary_key=True)
    nome  = Column(String)
    email = Column(String)


# ── Emissão ──────────────────────────────────────────────────────────────────

def _montar_venda_dict(venda: Venda, cliente: Cliente | None) -> dict:
    """Converte ORM → dict compatível com NFSeEmitter._emitir_nota()."""
    categoria = venda.categoria or "gelow"
    descricao = NFSE_DESCRICAO_TEMPLATES.get(categoria.lower(), "ENSAIO FOTOGRAFICO")

    return {
        "CPF":          venda.cliente_cpf,
        "RAZAO":        cliente.nome if cliente else "CLIENTE",
        "EMAIL":        cliente.email if cliente else "",
        "VALOR":        venda.valor,
        "DESCRICAO":    descricao,
        "data_emissao": date.today().strftime("%m/%Y"),
        "_venda_id":    venda.id,
    }


def _atualizar_nota(SessionMaker, venda_id: int, num_nota: str | None) -> None:
    """Marca venda como emitida no banco após emissão bem-sucedida."""
    with SessionMaker() as session:
        venda = session.get(Venda, venda_id)
        if venda:
            venda.status   = "emitida"
            venda.num_nota = num_nota or ""
            venda.data_nota = date.today()
            session.commit()
            logger.info(f"Venda {venda_id} marcada como emitida. Nota: {num_nota}")


def emitir_pendentes(dry_run: bool = False) -> None:
    """
    Busca todas as vendas com status='pendente' e as emite via PyAutoGUI.

    Args:
        dry_run: se True, apenas lista as vendas sem emitir (útil para testar conectividade).
    """
    SessionMaker = _build_session()

    with SessionMaker() as session:
        vendas = (
            session.query(Venda)
            .filter(Venda.status == "pendente")
            .order_by(Venda.data_venda.asc())
            .all()
        )

        if not vendas:
            logger.info("Nenhuma venda pendente para emitir.")
            return

        logger.info(f"Encontradas {len(vendas)} venda(s) pendente(s).")

        # Montar dicts com dados de cliente
        vendas_dict = []
        for v in vendas:
            cliente = session.get(Cliente, v.cliente_cpf)
            vendas_dict.append(_montar_venda_dict(v, cliente))

    if dry_run:
        logger.info("=== DRY RUN — nenhuma nota será emitida ===")
        for i, v in enumerate(vendas_dict, 1):
            logger.info(
                f"  {i}. ID={v['_venda_id']} | {v['RAZAO']} | CPF={v['CPF']} | "
                f"R$ {v['VALOR']:.2f} | {v['DESCRICAO']}"
            )
        return

    # Importação local para não quebrar em ambientes sem pyautogui (servidor)
    try:
        import pyautogui
        import pyperclip
    except ImportError:
        logger.error("pyautogui/pyperclip não instalados. Execute: pip install pyautogui pyperclip")
        sys.exit(1)

    from src.automation.nfse_emitter import NFSeEmitter

    # NFSeEmitter agora emite as notas recebendo os dicionários diretamente do banco
    emitter = NFSeEmitter(callback_status=lambda msg: logger.info(f"[NFSe] {msg}"))

    if not emitter.preparar_navegador():
        logger.error("Preparação do navegador falhou. Abortando.")
        return

    resultados = []
    for idx, venda_dict in enumerate(vendas_dict):
        venda_id = venda_dict.pop("_venda_id")

        logger.info(f"Emitindo {idx+1}/{len(vendas_dict)}: {venda_dict['RAZAO']} (CPF {venda_dict['CPF']})")

        try:
            sucesso, num_nota = emitter._emitir_nota(venda_dict)
        except Exception as e:
            logger.error(f"Erro ao emitir nota para {venda_dict['RAZAO']}: {e}", exc_info=True)
            sucesso, num_nota = False, None

        resultados.append({"id": venda_id, "nome": venda_dict["RAZAO"], "sucesso": sucesso, "num_nota": num_nota})

        if sucesso:
            _atualizar_nota(SessionMaker, venda_id, num_nota)
            logger.info(f"  ✓ Emitida: {num_nota}")
        else:
            logger.warning(f"  ✗ Falha na emissão para venda ID={venda_id}.")

    # Resumo final
    ok  = sum(1 for r in resultados if r["sucesso"])
    nok = len(resultados) - ok
    logger.info(f"\n=== Emissão concluída: {ok} ✓ | {nok} ✗ ===")
    if nok:
        failed = [r["nome"] for r in resultados if not r["sucesso"]]
        logger.warning(f"Falhas: {failed}")


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Emissor local de NFSe — conecta direto ao banco do servidor.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas lista vendas pendentes sem emitir (testa conectividade com o banco).",
    )
    args = parser.parse_args()
    emitir_pendentes(dry_run=args.dry_run)
