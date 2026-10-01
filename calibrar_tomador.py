"""
calibrar_tomador.py — Recalibra as coordenadas dos campos do Tomador (com a tela rolada até o final).
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

CAMPOS_TOMADOR = [
    ("tomador_servico_brasil", "Seleção 'Brasil' para Tomador do Serviço (Radio Button)"),
    ("cpf_field", "Campo de inserção do CPF/CNPJ do Tomador"),
    ("email_field", "Campo de E-mail do Tomador"),
    ("botao_avancar_1", "Botão 'Avançar' no rodapé da Etapa 1"),
]

pyautogui.alert(
    text=(
        "CALIBRAÇÃO DOS CAMPOS DO TOMADOR (TELA ROLADA)\n\n"
        "1. Na página do portal (Etapa 1), ROLE A TELA PARA O FINAL.\n"
        "2. Clique em OK abaixo.\n"
        "3. Você receberá 1 popup por campo para posicionar o mouse.\n\n"
        "Clique em OK quando a tela estiver rolada para o final!"
    ),
    title="Calibração Tomador",
    button="OK"
)

novas_coordenadas = {}

for idx, (chave, descricao) in enumerate(CAMPOS_TOMADOR, 1):
    ans = pyautogui.confirm(
        text=(
            f"CAMPO [{idx}/{len(CAMPOS_TOMADOR)}]: {chave}\n"
            f"Descrição: {descricao}\n\n"
            "Clique em OK e em seguida posicione o mouse sobre o elemento na tela em 3 segundos."
        ),
        title=f"Calibrar Tomador [{idx}/{len(CAMPOS_TOMADOR)}]",
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
            "CALIBRAÇÃO DO TOMADOR CONCLUÍDA!\n\n"
            f"As coordenadas foram salvas em config/settings.py:\n"
            + "\n".join([f"  {k}: {v}" for k, v in novas_coordenadas.items()])
        ),
        title="Tomador Calibrado",
        button="OK"
    )
