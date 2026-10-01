"""
pegar_nova_nfse.py — Captura a coordenada do botão 'Emitir Nova NFSe' na tela final pós-emissão.
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
        "CALIBRAÇÃO DO BOTÃO 'EMITIR NOVA NFSE':\n\n"
        "1. No Chrome, esteja na TELA FINAL de confirmação de nota emitida.\n"
        "2. Clique em OK abaixo.\n"
        "3. Você terá 5 SEGUNDOS para posicionar o mouse sobre o botão 'Emitir Nova NFSe' (ou 'Nova DPS/NFSe').\n\n"
        "Clique em OK quando a tela final estiver visível!"
    ),
    title="Calibrador Nova NFSe",
    button="OK"
)

print("\n[!] Contagem de 5 segundos iniciada...")
for s in range(5, 0, -1):
    print(f"    Posicione o mouse sobre o botão 'Emitir Nova NFSe'... {s}s", flush=True)
    time.sleep(1)

x, y = pyautogui.position()
print(f"\n[OK] Coordenada botao_nova_nfse capturada: ({x}, {y})")

settings_path = Path(__file__).parent / "config" / "settings.py"
content = settings_path.read_text(encoding="utf-8")

new_content = re.sub(
    r'"botao_nova_nfse":\s*\(\d+,\s*\d+\)',
    f'"botao_nova_nfse": ({x}, {y})',
    content
)

settings_path.write_text(new_content, encoding="utf-8")

pyautogui.alert(
    text=(
        f"BOTÃO NOVA NFSE CALIBRADO COM SUCESSO!\n\n"
        f"Coordenada: ({x}, {y})\n\n"
        f"Gravado automaticamente em config/settings.py!"
    ),
    title="Nova NFSe Calibrado",
    button="OK"
)
