"""
pegar_nbs.py — Captura a coordenada exata do novo campo 'Item da NBS' na Etapa 2.
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

pyautogui.alert(
    text=(
        "RECALIBRAÇÃO DO CAMPO NBS (ETAPA 2):\n\n"
        "1. No Chrome, esteja na ETAPA 2 (Serviço Prestado) NO TOPO DA PÁGINA (SEM ROLAR A TELA).\n"
        "2. Clique em OK abaixo.\n"
        "3. Você terá 5 SEGUNDOS para posicionar o mouse sobre o campo 'Item da NBS'.\n\n"
        "Clique em OK quando estiver no topo da Etapa 2!"
    ),
    title="Calibrador NBS Etapa 2",
    button="OK"
)

print("\n[!] Contagem de 5 segundos iniciada...")
for s in range(5, 0, -1):
    print(f"    Posicione o mouse sobre o campo 'Item da NBS'... {s}s", flush=True)
    time.sleep(1)

x, y = pyautogui.position()
print(f"\n[OK] Coordenada NBS capturada: ({x}, {y})")

settings_path = Path(__file__).parent / "config" / "settings.py"
content = settings_path.read_text(encoding="utf-8")

new_content = re.sub(
    r'"nbs_field":\s*\(\d+,\s*\d+\)',
    f'"nbs_field": ({x}, {y})',
    content
)

settings_path.write_text(new_content, encoding="utf-8")

pyautogui.alert(
    text=(
        f"CAMPO NBS CALIBRADO COM SUCESSO!\n\n"
        f"Coordenada: ({x}, {y})\n\n"
        f"Gravado automaticamente em config/settings.py!"
    ),
    title="NBS Calibrado",
    button="OK"
)
