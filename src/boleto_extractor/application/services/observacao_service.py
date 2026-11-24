"""Monta o bloco de observação a partir dos dados do boleto e grava em lote."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from boleto_extractor.infrastructure.erp.erp_escrita_repository import (
    ErpEscritaRepository,
    so_digitos,
)

Boleto = Mapping[str, object]
Progresso = Callable[[int, int], None]


def _txt(v: object) -> str:
    return "" if v is None else str(v).strip()


def _fmt_cnpj(c: str) -> str:
    d = so_digitos(c)
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d


def _fmt_valor(v: object) -> str:
    if v is None or v == "":
        return ""
    try:
        valor = Decimal(str(v).replace(",", ".")) if isinstance(v, str) else Decimal(str(v))
    except (InvalidOperation, ValueError):
        return _txt(v)
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_bloco(boleto: Boleto, agora: datetime | None = None) -> str:
    momento = agora or datetime.now()
    campos: tuple[tuple[str, str], ...] = (
        ("Banco", _txt(boleto.get("banco"))),
        ("Linha digitável", _txt(boleto.get("linha_digitavel"))),
        ("Nosso número", _txt(boleto.get("nosso_numero"))),
        ("Documento", _txt(boleto.get("documento"))),
        ("Vencimento", _txt(boleto.get("vencimento"))),
        ("Valor", _fmt_valor(boleto.get("valor"))),
        ("Beneficiário", _txt(boleto.get("beneficiario_nome"))),
        ("CNPJ beneficiário", _fmt_cnpj(_txt(boleto.get("beneficiario_cnpj")))),
        ("Arquivo", _txt(boleto.get("arquivo"))),
    )
    linhas = [f"Sincronizado em: {momento:%d/%m/%Y %H:%M}"]
    linhas += [f"{rotulo}: {valor}" for rotulo, valor in campos if valor]
    return "\n".join(linhas)


class ObservacaoService:
    def __init__(self, repo: ErpEscritaRepository) -> None:
        self._repo = repo

    def gravar(self, pagparc_cod: int, boleto: Boleto) -> dict[str, Any]:
        cnpj = so_digitos(_txt(boleto.get("beneficiario_cnpj"))) or None
        resultado: dict[str, Any] = self._repo.gravar_parcela(
            pagparc_cod=pagparc_cod,
            bloco_obs=montar_bloco(boleto),
            cnpj_beneficiario=cnpj,
        )
        return resultado

    def gravar_lote(
        self,
        pares: Iterable[tuple[int, Boleto]],
        progresso: Progresso | None = None,
    ) -> list[dict[str, Any]]:
        lista = list(pares)
        total = len(lista)
        resultados: list[dict[str, Any]] = []
        for i, (cod, boleto) in enumerate(lista, start=1):
            resultados.append(self.gravar(cod, boleto))
            if progresso is not None:
                progresso(i, total)
        return resultados
