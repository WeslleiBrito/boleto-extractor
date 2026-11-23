import re
from dataclasses import dataclass

from boleto_extractor.application.services.documento_validator import (
    cnpj_valido,
    cpf_valido,
    limpar,
)

_RE_CNPJ = re.compile(
    r"(?<![A-Z0-9])[A-Z0-9]{2}\.?[A-Z0-9]{3}\.?[A-Z0-9]{3}/?[A-Z0-9]{4}-?\d{2}(?![A-Z0-9])"
)
_RE_CPF = re.compile(r"(?<![A-Z0-9])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![A-Z0-9])")

_ROTULOS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("beneficiario", re.compile(r"BENEFICI[AÁ]RIO|CEDENTE")),
    ("avalista", re.compile(r"SACADOR|AVALISTA")),
    ("pagador", re.compile(r"PAGADOR|\bSACADO\b")),
)
_JANELA = 400


@dataclass(frozen=True, slots=True)
class DocumentoEncontrado:
    documento: str
    tipo: str
    papel: str
    posicao: int
    confirmado_pelo_codigo: bool = False


class BeneficiarioExtractor:
    """Localiza o CPF/CNPJ do beneficiário no texto do boleto."""

    def extrair(self, texto: str, raiz_cnpj: str | None = None) -> DocumentoEncontrado | None:
        try:
            docs = self._todos(texto)
        except Exception:
            return None

        if raiz_cnpj:
            for d in docs:
                if d.tipo == "CNPJ" and d.documento.startswith(raiz_cnpj):
                    return DocumentoEncontrado(
                        d.documento, d.tipo, d.papel, d.posicao, confirmado_pelo_codigo=True
                    )

        criterios = (
            lambda d: d.papel == "beneficiario",
            lambda d: d.papel == "desconhecido" and d.tipo == "CNPJ",
            lambda d: d.papel == "desconhecido",
        )
        for criterio in criterios:
            for d in docs:
                if criterio(d):
                    return d
        return None

    def _todos(self, texto: str) -> list[DocumentoEncontrado]:
        t = (texto or "").upper()
        rotulos = sorted((m.start(), p) for p, rx in _ROTULOS for m in rx.finditer(t))

        def papel_de(pos: int) -> str:
            antes = [r for p, r in rotulos if p < pos and pos - p <= _JANELA]
            return antes[-1] if antes else "desconhecido"

        achados: list[DocumentoEncontrado] = []
        vistos: set[str] = set()
        buscas = ((_RE_CNPJ, "CNPJ", cnpj_valido), (_RE_CPF, "CPF", cpf_valido))
        for rx, tipo, valida in buscas:
            for m in rx.finditer(t):
                doc = limpar(m.group())
                if doc in vistos or not valida(doc):
                    continue
                vistos.add(doc)
                achados.append(DocumentoEncontrado(doc, tipo, papel_de(m.start()), m.start()))
        return sorted(achados, key=lambda d: d.posicao)
