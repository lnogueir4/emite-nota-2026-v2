import re


class EmailValidator:
    """Validador de e-mail: formato, um único endereço e erros de digitação comuns no domínio."""

    _FORMATO = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$")

    # Domínios digitados errado → domínio correto
    DOMINIOS_TYPO = {
        "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gmal.com": "gmail.com",
        "gamil.com": "gmail.com", "gnail.com": "gmail.com", "gmail.co": "gmail.com",
        "gmail.com.br": "gmail.com",
        "hotmial.com": "hotmail.com", "hotmal.com": "hotmail.com", "hotmai.com": "hotmail.com",
        "hotmil.com": "hotmail.com", "homail.com": "hotmail.com", "hotamil.com": "hotmail.com",
        "hotmail.co": "hotmail.com",
        "outlok.com": "outlook.com", "outllok.com": "outlook.com", "outlook.co": "outlook.com",
        "yahooo.com": "yahoo.com", "yaho.com": "yahoo.com", "yahoo.com.b": "yahoo.com.br",
        "icloud.co": "icloud.com", "iclod.com": "icloud.com",
    }

    # Finais de domínio digitados errado → final correto
    TERMINACOES_TYPO = {".con": ".com", ".cmo": ".com", ".comm": ".com", ".coom": ".com", ".vom": ".com"}

    def clean(self, email: str) -> str:
        """Remove espaços, asteriscos de negrito do WhatsApp e pontuação solta; converte para minúsculas."""
        if email is None:
            return ""
        email = str(email).strip().strip("*_").strip().rstrip(".,;")
        return email.lower()

    def sugestao(self, email: str) -> str | None:
        """Retorna o e-mail corrigido se o domínio tiver um erro de digitação conhecido."""
        email = self.clean(email)
        if email.count("@") != 1:
            return None
        usuario, dominio = email.split("@")
        if dominio in self.DOMINIOS_TYPO:
            return f"{usuario}@{self.DOMINIOS_TYPO[dominio]}"
        for errado, certo in self.TERMINACOES_TYPO.items():
            if dominio.endswith(errado):
                return f"{usuario}@{dominio[: -len(errado)]}{certo}"
        return None

    def validate(self, email: str) -> bool:
        email = self.clean(email)

        # Mais de um endereço no campo (ex.: "a@x.com / b@y.com") ou formato inválido
        if not self._FORMATO.match(email) or ".." in email:
            return False

        return self.sugestao(email) is None

    def validate_batch(self, emails: list) -> dict:
        return {email: self.validate(email) for email in emails}
