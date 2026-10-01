"""
calibrar_etapa3.py — Recalibra os campos da Etapa 3 (após Não Retenção do ISSQN e scroll).
"""
import re
import sys
import time
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("ERRO: pyautogui não instalado.")
    sys.exit(1)

CAMPOS_ETAPA3 = [
    ("situacao_tributaria", "Campo 'Situação Tributária' (onde digita 00)"),
    ("tipo_retencao", "Campo 'Tipo de Retenção'"),
    ("valor_preencher_federal", "Campo de Tributação Federal / Impostos Federais"),
    ("botao_avancar_3", "Botão 'Avançar' no rodapé da Etapa 3"),
]

pyautogui.alert(
    text=(
        "CALIBRAÇÃO DA ETAPA 3 (VALORES E TRIBUTOS):\n\n"
        "1. No Chrome, esteja na ETAPA 3 e ROLE A TELA PARA BAIXO (após Retenção ISSQN).\n"
        "2. Clique em OK abaixo.\n"
        "3. Você receberá 1 popup por campo para posicionar o mouse.\n\n"
        "Clique em OK quando a tela estiver rolada na Etapa 3!"
    ),
    title="Calibração Etapa 3",
    button="OK"
)

novas_coordenadas = {}

for idx, (chave, descricao) in enumerate(CAMPOS_ETAPA3, 1):
    ans = pyautogui.confirm(
        text=(
            f"CAMPO [{idx}/{len(CAMPOS_ETAPA3)}]: {chave}\n"
            f"Descrição: {descricao}\n\n"
            "Clique em OK e em seguida posicione o mouse sobre o elemento na tela em 3 segundos."
        ),
        title=f"Calibrar Etapa 3 [{idx}/{len(CAMPOS_ETAPA3)}]",
        buttons=["OK", "Pular", "Cancelar"]
    )

    if ans == "Cancelar":
        print("Calibração cancelada.")
        sys.exit(0)
    elif ans == "Pular":
        continue

    for i in range(3, 0, -1):
        print(f"    Capturando {chave} em {i}s...", end="\r", flush=True)
        time.sleep(1)

    x, y = pyautogui.position()
    novas_coordenadas[chave] = (x, y)
    print(f"    [OK] Capturado: {chave} = ({x}, {y})")

if novas_coordenadas:
    settings_path = Path(__file__).parent / "config" / "settings.py"
    content = settings_path.read_text(encoding="utf-8")

    for k, (x, y) in novas_coordenadas.items():
        pattern = rf'"{k}":\s*\(\d+,\s*\d+\)'
        if re.search(pattern, content):
            content = re.sub(pattern, f'"{k}": ({x}, {y})', content)

    settings_path.write_text(content, encoding="utf-8")

    pyautogui.alert(
        text=(
            "CALIBRAÇÃO DA ETAPA 3 CONCLUÍDA!\n\n"
            f"As coordenadas foram salvas em config/settings.py:\n"
            + "\n".join([f"  {k}: {v}" for k, v in novas_coordenadas.items()])
        ),
        title="Etapa 3 Calibrada",
        button="OK"
    )
