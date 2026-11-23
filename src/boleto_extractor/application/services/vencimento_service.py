from __future__ import annotations

import re
from datetime import date, datetime, timedelta

_BASE_ANTIGA = date(1997, 10, 7)    # fator 0000
_BASE_NOVA = date(2025, 2, 22)      # fator 1000 após o reinício
_RE_VENC = re.compile(r"venc\w*\D{0,30}?(\d{2})[/.-](\d{2})[/.-](\d{4})", re.I | re.S)


def _por_fator(codigo: str, hoje: date) -> date | None:
    fator = int(codigo[5:9])
    if fator == 0:
        return None
    antiga = _BASE_ANTIGA + timedelta(days=fator)
    nova = _BASE_NOVA + timedelta(days=fator - 1000)
    return min((antiga, nova), key=lambda d: abs((d - hoje).days))


def _por_texto(texto: str) -> date | None:
    for d, m, a in _RE_VENC.findall(texto or ""):
        try:
            return datetime(int(a), int(m), int(d)).date()
        except ValueError:
            continue
    return None


def _por_campo_livre(codigo: str, hoje: date) -> date | None:
    livre = codigo[19:]
    for i in range(len(livre) - 7):
        trecho = livre[i:i + 8]
        if not trecho.startswith("20"):
            continue
        try:
            d = datetime.strptime(trecho, "%Y%m%d").date()
        except ValueError:
            continue
        if abs((d - hoje).days) <= 366:
            return d
    return None


def extrair_vencimento(codigo_barras: str, texto_pdf: str = "",
                       hoje: date | None = None) -> tuple[date | None, str]:
    """Retorna (data, origem) com origem em: 'codigo', 'pdf' ou ''."""
    hoje = hoje or date.today()
    cod = re.sub(r"\D", "", codigo_barras or "")
    if len(cod) != 44:
        return _por_texto(texto_pdf), "pdf" if _por_texto(texto_pdf) else ""

    if not cod.startswith("8") and (d := _por_fator(cod, hoje)):
        return d, "codigo"
    if d := _por_texto(texto_pdf):
        return d, "pdf"
    if cod.startswith("8") and (d := _por_campo_livre(cod, hoje)):
        return d, "pdf"
    return None, ""
