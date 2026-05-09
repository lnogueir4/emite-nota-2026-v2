import time
from pathlib import Path
from typing import List, Optional, Callable
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import (
    NFSE_PORTAL_URL, PYAUTOGUI_COORDINATES,
    PAUSE_BETWEEN_ACTIONS, PAGE_TRANSITION_DELAY, SCROLL_AMOUNT,
    municipio, codtn, nbs
)


class NFSeEmitter:
    """
    Automatiza emissão de NFSe no portal do governo via pyautogui.
    Emite NFSe a partir de dicionários de dados populados via banco de dados.
    """

    def __init__(self, callback_status: Optional[Callable] = None):
        self.callback_status = callback_status
        self.coordinates = PYAUTOGUI_COORDINATES
        self.municipio = municipio
        self.codtn = codtn
        self.nbs = nbs
        self._abort = False

    def _log(self, msg: str):
        if self.callback_status:
            self.callback_status(msg)
        else:
            print(msg)

    def preparar_navegador(self) -> bool:
        """Abre Chrome e navega para portal NFSe."""
        try:
            import pyautogui
            import pyperclip

            pyautogui.PAUSE = 1.0

            pyautogui.press("winleft")
            pyautogui.write("chrome")
            pyautogui.press("enter")

            response = pyautogui.confirm(
                "O robô vai começar.\n\n"
                "REQUISITOS:\n"
                "- Usar zoom 50% no navegador\n"
                "- Não mexer no mouse/teclado\n\n"
                "Clique em OK para continuar ou Cancelar para abortar.",
                title="Automação NFSe"
            )

            if response != "OK":
                self._log("Automação cancelada pelo usuário")
                return False

            pyautogui.hotkey('ctrl', 't')
            pyperclip.copy(NFSE_PORTAL_URL)
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.press("enter")
            time.sleep(5)

            return True
        except ImportError:
            self._log("ERRO: pyautogui não instalado. Execute: pip install pyautogui pyperclip")
            return False



    def _emitir_nota(self, venda: dict) -> tuple:
        """Emite uma única NFSe."""
        try:
            import pyautogui
            import pyperclip

            pyautogui.PAUSE = 1.0

            self._preencher_dados_basicos(venda, pyautogui, pyperclip)
            self._preencher_servico(venda, pyautogui, pyperclip)
            self._preencher_valores(venda, pyautogui, pyperclip)
            sucesso, num_nota = self._finalizar_emissao(pyautogui)

            if sucesso:
                self._preparar_proxima(pyautogui)

            return sucesso, num_nota

        except Exception as e:
            self._log(f"Erro ao emitir: {e}")
            return False, None

    def _preencher_dados_basicos(self, venda, pyautogui, pyperclip):
        coord = self.coordinates

        time.sleep(3)

        pyautogui.click(*coord["data_competencia"])
        pyperclip.copy(venda['data_emissao'])
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('tab')

        pyautogui.click(*coord["indicador_municipio"])
        pyautogui.press('down')
        pyautogui.press('enter')
        pyautogui.press('tab')

        pyautogui.click(*coord["regime_apuracao"])
        pyautogui.press('down')
        pyautogui.press('enter')
        pyautogui.press('tab')

        pyautogui.click(*coord["tomador_servico_brasil"])

        pyautogui.click(*coord["cpf_field"])
        pyperclip.copy(venda['CPF'])
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('tab')

        pyautogui.scroll(SCROLL_AMOUNT)

        pyautogui.click(*coord["email_field"])
        pyperclip.copy(venda['EMAIL'])
        pyautogui.hotkey('ctrl', 'v')

        pyautogui.click(*coord["botao_avancar_1"])
        time.sleep(PAGE_TRANSITION_DELAY)

    def _preencher_servico(self, venda, pyautogui, pyperclip):
        coord = self.coordinates

        pyautogui.click(*coord["municipio_field"])
        pyperclip.copy(self.municipio)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        pyautogui.press('tab')

        pyautogui.click(*coord["codigo_tributacao"])
        pyperclip.copy(self.codtn)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        pyautogui.press('tab')

        pyautogui.click(*coord["codigo_complementar"])
        pyautogui.press('enter')

        pyautogui.click(*coord["nao_incidencia_issqn"])

        pyautogui.click(*coord["descricao_servico"])
        pyperclip.copy(venda['DESCRICAO'])
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('tab')

        pyautogui.click(*coord["nbs_field"])
        pyperclip.copy(self.nbs)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        pyautogui.press('tab')
        pyautogui.scroll(SCROLL_AMOUNT)

        pyautogui.click(*coord["botao_avancar_2"])
        time.sleep(PAGE_TRANSITION_DELAY)

    def _preencher_valores(self, venda, pyautogui, pyperclip):
        coord = self.coordinates
        valor = float(venda['VALOR'])
        valor_centavos = str(int(round(valor * 100)))

        pyautogui.click(*coord["valor_field"])
        pyautogui.write(valor_centavos, interval=0.05)
        pyautogui.press("tab")

        pyautogui.click(*coord["nao_retencao_issqn"])
        pyautogui.scroll(-700)

        pyautogui.click(*coord["situacao_tributaria"])
        pyperclip.copy("00")
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        pyautogui.press("tab")

        pyautogui.click(*coord["tipo_retencao"])
        pyautogui.press('down')
        pyautogui.press('enter')

        pyautogui.click(*coord["valor_preencher_federal"])
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.write("0", interval=0.05)
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.write("0", interval=0.05)
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.write("0", interval=0.05)

        pyautogui.click(*coord["botao_avancar_3"])
        time.sleep(PAGE_TRANSITION_DELAY)

    def _finalizar_emissao(self, pyautogui) -> tuple:
        coord = self.coordinates

        pyautogui.scroll(-1000)
        pyautogui.scroll(-400)

        time.sleep(3)
        pyautogui.click(*coord["botao_emitir"])
        time.sleep(PAGE_TRANSITION_DELAY)

        sucesso = True
        num_nota = None

        time.sleep(2)

        return sucesso, num_nota

    def _preparar_proxima(self, pyautogui):
        coord = self.coordinates
        pyautogui.click(*coord["botao_nova_nfse"])
        time.sleep(PAGE_TRANSITION_DELAY)

    def abortar(self):
        self._abort = True