import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"

VENDAS_ESTUDIO_FILE = BASE_DIR / "Vendas-estudio.xlsx"

WHATSAPP_TXT_FILE = INPUT_DIR / "txt_vendas_raw.txt"
NFSE_OUTPUT_FILE = OUTPUT_DIR / "notas_a_emitir.xlsx"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

PLANO_MAPPING = {
    # Gestante - Low
    "classico": "gelow",
    "clássico": "gelow",
    "memoria": "gelow",
    "memória": "gelow",
    "geclass": "gelow",
    "gemini": "gelow",
    "gestante clssico": "gelow",
    "ensaio gestante plano clssico": "gelow",
    "gestante plano clssico": "gelow",
    "gestante plano bsico": "gelow",
    "ensaio descoberta do sexo do beb": "gelow",
    # Gestante - Medium
    "essencial": "gemedium",
    "especial": "gemedium",
    "experienca": "gemedium",
    "experiência": "gemedium",
    "experiencia": "gemedium",
    "geess": "gemedium",
    "gestante essencial": "gemedium",
    "ensaio gestante plano essencial": "gemedium",
    "gestante black friday": "gehigh",
    # Gestante - High
    "vip": "gehigh",
    "estrela": "gehigh",
    "gestante vip": "gehigh",
    "ensaio gestante plano vip": "gehigh",
    "gestante plano vip": "gehigh",
    # Aniversario
    "bday": "bday",
    "niver": "bday",
    "aniversario": "bday",
    "aniversário": "bday",
    "mini sesso de aniversrio": "bday",
    "aniversrio essencial": "bday",
    "ensaio aniversrio": "bday",
    # Infantil
    "infantil": "kids",
    "kid": "kids",
    "kids": "kids",
    "infantil essencial": "kids",
    # Newborn
    "rn": "rn",
    "nb": "rn",
    "newborn": "rn",
    "recem": "rn",
    "recém": "rn",
    "nascido": "rn",
    # Familia
    "familia": "fami",
    "família": "fami",
    "filha": "fami",
    "mae e filha": "fami",
    "mãe e filha": "fami",
    "me e filha": "fami",
    "ensaio em famlia": "fami",
    "evento de renovao de votos": "fami",
    # Corporativo
    "corporativo": "corp",
    "corp": "corp",
    "corporativo clssico": "corp",
    # Formatura
    "formatura": "forma",
    "formando": "forma",
    "ensaio de formatura": "forma",
    # Natal
    "natal bsico": "natallow",
    "natal plano bsico": "natallow",
    "natal premium": "natalhigh",
    "natal plano premium": "natalhigh",
    # Feminino
    "feminino essencial": "femi",
    "ensaio feminino plano essencial": "femi",
    "feminino black friday": "femi",
    "feminino plano essencial": "femi",
    # Mãe
    "mães": "mãe",
    "maes": "mãe",
    "mães plano premium": "mãe",
    "mães plano memória": "mãe",
    "ensaio mães": "mãe",
    "ensaio mães plano premium": "mãe",
    "ensaio mães plano memória": "mãe",
}

# Mapeamento por categoria para prioridade
CATEGORIA_MAPPING = {
    "corp": ["corporativo", "corp"],
    "forma": ["formatura", "formando"],
    "fami": ["familia", "família", "filha", "mae e filha", "mãe e filha", "renovacao de votos"],
    "bday": ["bday", "aniversario", "aniversário", "niver"],
    "kids": ["infantil", "kid", "kids"],
    "rn": ["newborn", "rn", "nb", "recem", "recém", "nascido"],
    "natal": ["natal"],
    "femi": ["feminino", "femi"],
    "mãe": ["mães", "maes", "mães plano premium", "mães plano memória", "ensaio mães", "ensaio mães plano premium", "ensaio mães plano memória"],
}

NFSE_DESCRICAO_TEMPLATES = {
    "gelow": "ENSAIO FOTOGRAFICO GESTANTE",
    "gemedium": "ENSAIO FOTOGRAFICO GESTANTE",
    "gehigh": "ENSAIO FOTOGRAFICO GESTANTE VIP",
    "bday": "ENSAIO FOTOGRAFICO ANIVERSARIO",
    "kids": "ENSAIO FOTOGRAFICO INFANTIL",
    "rn": "ENSAIO FOTOGRAFICO NEWBORN",
    "corp": "ENSAIO FOTOGRAFICO CORPORATIVO",
    "fami": "ENSAIO FOTOGRAFICO FAMILIA",
    "forma": "ENSAIO FOTOGRAFICO FORMATURA",
    "natal": "ENSAIO FOTOGRAFICO DE NATAL",
    "femi": "ENSAIO FOTOGRAFICO FEMININO",
    "mãe": "ENSAIO FOTOGRAFICO DIA DAS MÃES",
}

COLUNAS_VENDAS_ESTUDIO = [
    "cpf", "nome", "email", "plano", "valor", "data_venda",
    "meio_pagto", "parcelas", "como_conheceu", "aniversario", "profissao", "num_nota"
]

NFSE_PORTAL_URL = "https://www.nfse.gov.br/EmissorNacional/DPS/Pessoas"

# Configurações NFSe
municipio = "Manaus"
codtn = "130301"
nbs = "114081100"

PYAUTOGUI_COORDINATES = {
    "ibs_cbs_opcao": (442, 345),
    "data_competencia": (489, 407),
    "indicador_municipio": (1203, 617),
    "regime_apuracao": (482, 785),
    "tomador_servico_brasil": (452, 312),
    "cpf_field": (483, 402),
    "email_field": (816, 516),
    "botao_avancar_1": (1413, 841),
    "municipio_field": (934, 324),
    "codigo_tributacao": (461, 429),
    "codigo_complementar": (483, 485),
    "nao_incidencia_issqn": (436, 543),
    "descricao_servico": (459, 799),
    "nbs_field": (499, 683),
    "botao_avancar_2": (1419, 844),
    "valor_field": (517, 330),
    "nao_retencao_issqn": (434, 628),
    "situacao_tributaria": (489, 193),
    "tipo_retencao": (465, 258),
    "valor_preencher_federal": (473, 749),
    "botao_avancar_3": (1429, 899),
    "botao_emitir": (1419, 848),
    "botao_nova_nfse": (1192, 734),
}

PAUSE_BETWEEN_ACTIONS = 0.5
PAGE_TRANSITION_DELAY = 3
SCROLL_AMOUNT = -1200