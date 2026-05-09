"""
Atualiza estudio_2026.clientes com dados do Excel:
- Cria coluna data_cadastro (date) se não existir
- Atualiza: como_conheceu, aniversario, profissao, data_cadastro
- Normaliza: como_conheceu (mapeamento fixo), profissao (title case)
- Chave de join: cpf
"""

import re
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

from dotenv import load_dotenv
import os

load_dotenv()

# ── Configuração ──────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
EXCEL_PATH   = "clientes-estudio-limpo.xlsx"
SCHEMA       = "estudio_2026"
TABLE        = "clientes"
BATCH_SIZE   = 100

# ── Mapeamento como_conheceu ──────────────────────────────────────────────────
COMO_CONHECEU_MAP = {
    "DICA": "Indicação",
    "IG":   "Instagram",
    "gym":  "Indicação",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def normaliza_cpf(x):
    if pd.isna(x):
        return None
    s = re.sub(r'[\.\-\/]', '', str(x).strip())
    s = re.sub(r'\.0$', '', s)
    return s.zfill(11) if s.isdigit() else s

def parse_data(x):
    if pd.isna(x):
        return pd.NaT
    if isinstance(x, (int, float)):
        return pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(x))
    return pd.to_datetime(x, errors='coerce')

def normaliza_como_conheceu(v):
    if pd.isna(v) or str(v).strip() == '':
        return None
    return COMO_CONHECEU_MAP.get(str(v).strip(), str(v).strip())

def normaliza_profissao(v):
    if pd.isna(v) or str(v).strip() == '':
        return None
    return str(v).strip().title()

def normaliza_aniversario(v):
    if pd.isna(v):
        return None
    try:
        ts = pd.Timestamp(v)
        return ts.strftime('%d/%m/%Y')
    except Exception:
        return None

def normaliza_data_cadastro(v):
    if pd.isna(v):
        return None
    try:
        return pd.Timestamp(v).date()
    except Exception:
        return None

# ── Leitura e deduplicação do Excel ──────────────────────────────────────────
def carregar_excel(path):
    df = pd.read_excel(path)
    df['cpf']           = df['cpf'].apply(normaliza_cpf)
    df['data_cadastro'] = df['data_cadastro'].apply(parse_data)
    df = df[df['cpf'].notna()]
    df = (df.sort_values('data_cadastro', na_position='last')
            .drop_duplicates(subset='cpf', keep='first'))
    print(f"Excel carregado: {len(df)} registros únicos")
    return df

# ── Banco ─────────────────────────────────────────────────────────────────────
def criar_coluna_se_necessario(cur):
    cur.execute(f"""
        ALTER TABLE {SCHEMA}.{TABLE}
        ADD COLUMN IF NOT EXISTS data_cadastro date;
    """)
    print("Coluna data_cadastro verificada/criada.")

def montar_registros(df):
    registros = []
    sem_dados = 0

    for _, row in df.iterrows():
        como_conheceu  = normaliza_como_conheceu(row.get('como_conheceu'))
        profissao      = normaliza_profissao(row.get('profissao'))
        aniversario    = normaliza_aniversario(row.get('niver'))
        data_cadastro  = normaliza_data_cadastro(row.get('data_cadastro'))

        # Só inclui se ao menos um campo tem valor útil
        if any(v is not None for v in [como_conheceu, profissao, aniversario, data_cadastro]):
            registros.append({
                'cpf':           row['cpf'],
                'como_conheceu': como_conheceu,
                'profissao':     profissao,
                'aniversario':   aniversario,
                'data_cadastro': data_cadastro,
            })
        else:
            sem_dados += 1

    print(f"Registros com ao menos 1 campo para atualizar: {len(registros)}")
    print(f"Registros sem nenhum dado novo (ignorados):     {sem_dados}")
    return registros

def executar_updates(cur, registros):
    sql = f"""
        UPDATE {SCHEMA}.{TABLE}
        SET
            como_conheceu  = COALESCE(%s, como_conheceu),
            profissao      = COALESCE(%s, profissao),
            aniversario    = COALESCE(%s, aniversario),
            data_cadastro  = COALESCE(%s, data_cadastro),
            atualizado_em  = NOW()
        WHERE cpf = %s
    """
    params = [
        (
            r['como_conheceu'],
            r['profissao'],
            r['aniversario'],
            r['data_cadastro'],
            r['cpf'],
        )
        for r in registros
    ]
    execute_batch(cur, sql, params, page_size=BATCH_SIZE)
    print(f"Updates executados: {len(params)}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    df = carregar_excel(EXCEL_PATH)
    registros = montar_registros(df)

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                criar_coluna_se_necessario(cur)
                executar_updates(cur, registros)
        print("Concluído com sucesso.")
    except Exception as e:
        print(f"ERRO: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
