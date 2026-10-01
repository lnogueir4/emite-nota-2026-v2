"""
pegar_avancar3.py — Captura a coordenada do botão 'Avançar 3' com a tela da Etapa 3 rolada até o final.
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
        "CALIBRAÇÃO DO BOTÃO AVANÇAR (ETAPA 3):\n\n"
        "1. No Chrome, na ETAPA 3, ROLE A TELA TOTALMENTE ATÉ O FINAL.\n"
        "2. Clique em OK abaixo.\n"
        "3. Você terá 5 SEGUNDOS para posicionar o mouse sobre o botão 'Avançar' no rodapé.\n\n"
        "Clique em OK quando a página estiver rolada até o final!"
    ),
    title="Calibrador Avançar 3",
    button="OK"
)

print("\n[!] Contagem de 5 segundos iniciada...")
for s in range(5, 0, -1):
    print(f"    Posicione o mouse sobre o botão 'Avançar 3'... {s}s", flush=True)
    time.sleep(1)

x, y = pyautogui.position()
print(f"\n[OK] Coordenada botao_avancar_3 capturada: ({x}, {y})")

settings_path = Path(__file__).parent / "config" / "settings.py"
content = settings_path.read_text(encoding="utf-8")

new_content = re.sub(
    r'"botao_avancar_3":\s*\(\d+,\s*\d+\)',
    f'"botao_avancar_3": ({x}, {y})',
    content
)

settings_path.write_text(new_content, encoding="utf-8")

pyautogui.alert(
    text=(
        f"BOTÃO AVANÇAR 3 CALIBRADO COM SUCESSO!\n\n"
        f"Coordenada: ({x}, {y})\n\n"
        f"Gravado automaticamente em config/settings.py!"
    ),
    title="Avançar 3 Calibrado",
    button="OK"
)
