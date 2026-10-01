"""
pegar_ibs.py — Captura a coordenada exata da opção 'Não' do IBS/CBS com popups de aviso na tela.
"""
import sys
import time
import re
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("ERRO: pyautogui não instalado.")
    sys.exit(1)

# Popup de início
pyautogui.alert(
    text=(
        "INSTRUÇÕES DE CALIBRAÇÃO IBS/CBS:\n\n"
        "1. Deixe a página do portal NFSe visível no Chrome.\n"
        "2. Clique em OK abaixo.\n"
        "3. Você terá 5 SEGUNDOS para colocar o cursor do mouse sobre o botão 'Não' de IBS/CBS.\n\n"
        "Clique em OK quando estiver pronto!"
    ),
    title="Calibrador IBS/CBS",
    button="OK"
)

print("\n[!] Contagem regressiva iniciada: 5 segundos para posicionar o mouse...")

for s in range(5, 0, -1):
    print(f"    Posicione o mouse sobre o botao 'Nao'... {s}s", flush=True)
    time.sleep(1)

x, y = pyautogui.position()

# Atualiza direto o config/settings.py
settings_path = Path(__file__).parent / "config" / "settings.py"
content = settings_path.read_text(encoding="utf-8")

new_content = re.sub(
    r'"ibs_cbs_opcao":\s*\(\d+,\s*\d+\)',
    f'"ibs_cbs_opcao": ({x}, {y})',
    content
)

settings_path.write_text(new_content, encoding="utf-8")

# Popup de conclusão
pyautogui.alert(
    text=(
        f"CAPTURADO COM SUCESSO!\n\n"
        f"Coordenada X, Y: ({x}, {y})\n\n"
        f"O arquivo config/settings.py foi atualizado automaticamente!"
    ),
    title="Calibração Concluída",
    button="OK"
)

print(f"\n[OK] Coordenada salva em config/settings.py: ibs_cbs_opcao = ({x}, {y})\n")
