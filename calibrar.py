"""
calibrar.py — Utilitário de recalibração de coordenadas PyAutoGUI para o portal NFSe.

Uso:
  python calibrar.py --tracker  # Mostra x,y em tempo real no terminal enquanto você move o mouse
  python calibrar.py --wizard   # Popup individual para CADA campo com contagem regressiva
"""

import argparse
import re
import sys
import time
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("ERRO: pyautogui não instalado. Execute: pip install pyautogui")
    sys.exit(1)

CAMPOS = [
    # Etapa 1: Dados Básicos e Tomador
    ("ibs_cbs_opcao", "Opção 'Não' para 'Preencher as informações IBS/CBS?' (Primeiro campo)"),
    ("data_competencia", "Campo 'Data de Competência'"),
    ("indicador_municipio", "Opção 'Prestado em Manaus' (ou seleção do município)"),
    ("regime_apuracao", "Opção de Regime de Apuração"),
    ("tomador_servico_brasil", "Seleção 'Brasil' para Tomador do Serviço"),
    ("cpf_field", "Campo de inserção do CPF/CNPJ"),
    ("email_field", "Campo de e-mail do tomador"),
    ("botao_avancar_1", "Botão 'Avançar' (Etapa 1)"),

    # Etapa 2: Serviço Prestado
    ("municipio_field", "Campo 'Município da Prestação'"),
    ("codigo_tributacao", "Campo 'Código de Tributação' (130301)"),
    ("codigo_complementar", "Campo 'Código Complementar'"),
    ("nao_incidencia_issqn", "Opção 'Não Incidência / Isenção'"),
    ("descricao_servico", "Campo 'Descrição do Serviço'"),
    ("nbs_field", "Campo 'NBS' (114081100)"),
    ("botao_avancar_2", "Botão 'Avançar' (Etapa 2)"),

    # Etapa 3: Valores e Tributos
    ("valor_field", "Campo 'Valor do Serviço'"),
    ("nao_retencao_issqn", "Opção 'Não Retenção do ISSQN'"),
    ("situacao_tributaria", "Campo 'Situação Tributária'"),
    ("tipo_retencao", "Campo 'Tipo de Retenção'"),
    ("valor_preencher_federal", "Campo de Tributação Federal / Impostos"),
    ("botao_avancar_3", "Botão 'Avançar' (Etapa 3)"),

    # Etapa 4: Emissão e Próxima
    ("botao_emitir", "Botão 'Emitir DPS / NFSe'"),
    ("botao_nova_nfse", "Botão 'Emitir Nova NFSe'"),
]

def run_tracker():
    print("\n=======================================================")
    print(" MOSTRADOR DE COORDENADAS EM TEMPO REAL")
    print(" Pressione Ctrl+C no terminal a qualquer momento para sair.")
    print("=======================================================\n")
    try:
        pyautogui.displayMousePosition()
    except KeyboardInterrupt:
        print("\nTracker encerrado.")

def run_wizard():
    print("\n=======================================================")
    print(" ASSISTENTE DE CALIBRACAO COM POPUPS INDIVIDUAIS")
    print("=======================================================\n")

    # Popup inicial de boas vindas
    res = pyautogui.confirm(
        text=(
            "CALIBRAÇÃO COMPLETA DO PORTAL NFSe\n\n"
            "Será exibido 1 POPUP para cada um dos 22 elementos.\n"
            "Para cada campo:\n"
            "  1. Clique em OK no popup.\n"
            "  2. Mova o mouse sobre o elemento na tela em 3 segundos.\n\n"
            "Deseja iniciar agora?"
        ),
        title="Assistente de Calibração NFSe",
        buttons=["Sim, Iniciar", "Cancelar"]
    )

    if res != "Sim, Iniciar":
        print("Calibração cancelada pelo usuário.")
        return

    novas_coordenadas = {}

    for idx, (chave, descricao) in enumerate(CAMPOS, 1):
        print(f"\n[>] [{idx}/{len(CAMPOS)}] Solicitando campo: {chave}")

        ans = pyautogui.confirm(
            text=(
                f"CAMPO [{idx}/{len(CAMPOS)}]: {chave}\n"
                f"Descrição: {descricao}\n\n"
                "Instrução: Clique em OK e em seguida posicione a ponta do mouse sobre este elemento na tela!"
            ),
            title=f"Calibrar [{idx}/{len(CAMPOS)}]: {chave}",
            buttons=["OK", "Pular este campo", "Cancelar Tudo"]
        )

        if ans == "Cancelar Tudo":
            print("\n[!] Calibração interrompida pelo usuário.")
            pyautogui.alert("Calibração cancelada.", title="NFSe")
            return
        elif ans == "Pular este campo":
            print(f"    [PULADO] Campo {chave} mantido sem alteração.")
            continue

        print("    Capturando em 3 segundos...", flush=True)
        for i in range(3, 0, -1):
            print(f"    {i}...", end="\r", flush=True)
            time.sleep(1)

        x, y = pyautogui.position()
        novas_coordenadas[chave] = (x, y)
        print(f"    [OK] Capturado: {chave} = ({x}, {y})")

    if not novas_coordenadas:
        print("Nenhuma nova coordenada foi capturada.")
        return

    # Atualiza o arquivo config/settings.py com todas as coordenadas capturadas
    settings_path = Path(__file__).parent / "config" / "settings.py"
    content = settings_path.read_text(encoding="utf-8")

    for k, (x, y) in novas_coordenadas.items():
        pattern = rf'"{k}":\s*\(\d+,\s*\d+\)'
        if re.search(pattern, content):
            content = re.sub(pattern, f'"{k}": ({x}, {y})', content)

    settings_path.write_text(content, encoding="utf-8")

    pyautogui.alert(
        text=(
            "CALIBRAÇÃO CONCLUÍDA COM SUCESSO!\n\n"
            f"Foram capturadas e salvas {len(novas_coordenadas)} coordenadas em config/settings.py."
        ),
        title="Calibração Finalizada",
        button="OK"
    )

    print("\n=======================================================")
    print(" NOVAS COORDENADAS GRAVADAS NO CONFIG/SETTINGS.PY:")
    print("=======================================================")
    for k, v in novas_coordenadas.items():
        print(f'  "{k}": {v},')
    print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrador de coordenadas para o portal NFSe.")
    parser.add_argument("--tracker", action="store_true", help="Mostra as coordenadas x,y em tempo real no terminal.")
    parser.add_argument("--wizard", action="store_true", help="Assistente com 1 popup individual por campo.")
    args = parser.parse_args()

    if args.tracker:
        run_tracker()
    elif args.wizard:
        run_wizard()
    else:
        print("Escolha um modo de uso:\n")
        print("  python calibrar.py --tracker  (mostra x,y em tempo real)")
        print("  python calibrar.py --wizard   (assistente com popups por campo)")
