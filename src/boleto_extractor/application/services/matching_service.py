from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from boleto_extractor.infrastructure.erp.erp_parcela_repository import ParcelaErp

_TOL = Decimal("0.01")


class StatusSincronizacao(str, Enum):
    ENCONTRADO = "encontrado"
    JA_PAGO = "ja_pago"
    DATA_DIVERGENTE = "data_divergente"
    VALOR_DIVERGENTE = "valor_divergente"
    DOC_INEXISTENTE = "doc_inexistente"
    NAO_ENCONTRADO = "nao_encontrado"
    DUPLICADO = "duplicado"


ROTULOS = {
    StatusSincronizacao.ENCONTRADO: "Encontrado",
    StatusSincronizacao.JA_PAGO: "Já pago",
    StatusSincronizacao.DATA_DIVERGENTE: "Data divergente",
    StatusSincronizacao.VALOR_DIVERGENTE: "Valor divergente",
    StatusSincronizacao.DOC_INEXISTENTE: "Documento inexistente",
    StatusSincronizacao.NAO_ENCONTRADO: "Não encontrado",
    StatusSincronizacao.DUPLICADO: "Duplicado",
}


@dataclass(frozen=True, slots=True)
class ItemSincronizacao:
    chave: str          # identificador da linha
    documento: int      # pagparc_documento
    vencimento: date
    valor: Decimal


@dataclass(frozen=True, slots=True)
class ResultadoSincronizacao:
    chave: str
    status: StatusSincronizacao
    parcela: ParcelaErp | None
    detalhe: str


def _br(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "--"


def _moeda(v: Decimal) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pago(p: ParcelaErp) -> str:
    return " (paga)" if p.pago else ""


def _valor_confere(p: ParcelaErp, valor: Decimal) -> bool:
    return abs(p.valor_documento - valor) <= _TOL or abs(p.saldo - valor) <= _TOL


def _abertas_primeiro(parcelas: list[ParcelaErp]) -> list[ParcelaErp]:
    return sorted(parcelas, key=lambda p: p.pago)  # estável: mantém a ordem original


def sincronizar(itens: list[ItemSincronizacao],
                parcelas_por_documento: dict[int, list[ParcelaErp]]) -> list[ResultadoSincronizacao]:
    usadas: set[int] = set()
    saida: list[ResultadoSincronizacao] = []

    for it in itens:
        parcelas = parcelas_por_documento.get(it.documento, [])
        if not parcelas:
            saida.append(ResultadoSincronizacao(
                it.chave, StatusSincronizacao.DOC_INEXISTENTE, None,
                f"Documento {it.documento} não existe no ERP"))
            continue

        exatas = [p for p in parcelas if p.vencimento == it.vencimento and _valor_confere(p, it.valor)]
        livres = [p for p in exatas if p.cod not in usadas]

        if livres:
            escolhida = _abertas_primeiro(livres)[0]
            usadas.add(escolhida.cod)
            if escolhida.pago:
                saida.append(ResultadoSincronizacao(
                    it.chave, StatusSincronizacao.JA_PAGO, escolhida, "Parcela já baixada no ERP"))
            else:
                saida.append(ResultadoSincronizacao(
                    it.chave, StatusSincronizacao.ENCONTRADO, escolhida,
                    f"Saldo {_moeda(escolhida.saldo)}"))
            continue

        if exatas:
            saida.append(ResultadoSincronizacao(
                it.chave, StatusSincronizacao.DUPLICADO, exatas[0],
                "Parcela já usada por outro boleto do lote"))
            continue

        mesmo_valor = _abertas_primeiro([p for p in parcelas if _valor_confere(p, it.valor)])
        if mesmo_valor:
            datas = ", ".join(f"{_br(p.vencimento)}{_pago(p)}" for p in mesmo_valor[:6])
            saida.append(ResultadoSincronizacao(
                it.chave, StatusSincronizacao.DATA_DIVERGENTE, None,
                f"Vencimentos com esse valor: {datas}"))
            continue

        mesma_data = _abertas_primeiro([p for p in parcelas if p.vencimento == it.vencimento])
        if mesma_data:
            valores = ", ".join(f"{_moeda(p.valor_documento)}{_pago(p)}" for p in mesma_data[:4])
            saida.append(ResultadoSincronizacao(
                it.chave, StatusSincronizacao.VALOR_DIVERGENTE, None,
                f"Valor no ERP: {valores}"))
            continue

        saida.append(ResultadoSincronizacao(
            it.chave, StatusSincronizacao.NAO_ENCONTRADO, None,
            f"{len(parcelas)} parcela(s) no documento, nenhuma confere"))
    return saida
