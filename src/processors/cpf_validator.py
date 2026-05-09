import re


class CPFValidator:
    """Validador de CPF brasileiro."""

    def __init__(self):
        pass

    def clean(self, cpf: str) -> str:
        return re.sub(r'[^\d]', '', str(cpf))

    def validate(self, cpf: str) -> bool:
        cpf = self.clean(cpf)

        if len(cpf) != 11:
            return False

        if cpf == cpf[0] * 11:
            return False

        def calcular_digito(cpf_parcial: str, posicao: int) -> int:
            soma = sum(int(digito) * peso for digito, peso in zip(cpf_parcial, range(posicao, 1, -1)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto

        digito1 = calcular_digito(cpf[:9], 10)
        digito2 = calcular_digito(cpf[:10], 11)

        return cpf[9] == str(digito1) and cpf[10] == str(digito2)

    def validate_batch(self, cpfs: list) -> dict:
        return {cpf: self.validate(cpf) for cpf in cpfs}