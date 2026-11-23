import re

_NAO_ALNUM = re.compile(r"[^A-Z0-9]")


def limpar(valor: str) -> str:
    return _NAO_ALNUM.sub("", (valor or "").upper())


def cpf_valido(cpf: str) -> bool:
    d = re.sub(r"\D", "", cpf or "")
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def _dv_cnpj(base: str) -> str:
    """DV do CNPJ numérico ou alfanumérico (valor = ASCII - 48; pesos 2..9)."""
    soma = sum((ord(c) - 48) * ((i % 8) + 2) for i, c in enumerate(reversed(base)))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(cnpj: str) -> bool:
    c = limpar(cnpj)
    if not re.fullmatch(r"[A-Z0-9]{12}\d{2}", c) or c == c[0] * 14:
        return False
    dv1 = _dv_cnpj(c[:12])
    return c[12:] == dv1 + _dv_cnpj(c[:12] + dv1)
