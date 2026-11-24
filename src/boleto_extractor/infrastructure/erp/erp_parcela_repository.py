from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

_DOIS = Decimal("0.01")

_SALDO = (
    "(p.pagparc_vlrdocumento + COALESCE(p.pagparc_vlracrescimo,0)"
    " - COALESCE(p.pagparc_vlrdesconto,0) - COALESCE(p.pagparc_vlrbaixas,0)"
    " - COALESCE(p.pagparc_vlrpago,0))"
)

_DOC = "CAST(TRIM(p.pagparc_documento) AS UNSIGNED)"
# NF fica na tabela pagar; se vazia, cai para pagparc_nota
_NF = (
    "CAST(TRIM(COALESCE(NULLIF(TRIM(pg.pag_numnf), ''), NULLIF(TRIM(p.pagparc_nota), ''), '0'))"
    " AS UNSIGNED)"
)
# Fornecedor da parcela; se vazio, o da conta (pagar)
_FORN = "COALESCE(NULLIF(p.pagparc_fornecedor, 0), NULLIF(pg.pag_fornecedor, 0))"

MODOS = ("documento", "nota", "auto")


def _digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


@dataclass(frozen=True, slots=True)
class ParcelaErp:
    cod: int
    conta: int          # pagparc_conta (ligação com a tabela pagar)
    parcela: int
    qtd_parcelas: int
    vencimento: date | None
    valor_documento: Decimal
    saldo: Decimal
    pago: bool
    nome: str
    nota: str
    documento: int = 0          # pagparc_documento
    fornecedor_cod: int = 0
    fornecedor_nome: str = ""
    fornecedor_cnpj: str = ""   # somente dígitos

    @property
    def rotulo(self) -> str:
        return f"Parc. {self.parcela}/{self.qtd_parcelas or '?'} (#{self.cod})"

    @property
    def tem_fornecedor(self) -> bool:
        return self.fornecedor_cod > 0


class ErpParcelaRepository:
    """Leitura no ERP. Busca por pagparc_documento ou pelo número da NF (pagar).
    Também fornece conexões (conectar) para o repositório de escrita."""

    def __init__(self, config: Callable[[], dict[str, Any]], senha: Callable[[], str]) -> None:
        self._config = config
        self._senha = senha

    def conectar(self):
        """Abre uma conexão NOVA a cada chamada (autocommit desligado)."""
        import pymysql

        cfg = self._config()
        return pymysql.connect(
            host=cfg["db_host"], port=int(cfg["db_porta"]), user=cfg["db_usuario"],
            password=self._senha(), database=cfg["db_banco"] or None,
            charset="latin1", ssl={"ssl": {}} if cfg.get("db_ssl") else None,
            connect_timeout=5, read_timeout=30, write_timeout=30,
            autocommit=False,
        )

    # Compatibilidade com chamadas antigas
    _conectar = conectar

    @staticmethod
    def _normalizar(chaves: Iterable[Any]) -> list[int]:
        saida: set[int] = set()
        for c in chaves:
            try:
                n = int(str(c).strip())
            except (TypeError, ValueError):
                continue
            if n > 0:
                saida.add(n)
        return sorted(saida)

    def parcelas_por_chaves(self, chaves: Iterable[Any], modo: str = "documento") -> dict[int, list[ParcelaErp]]:
        """Retorna {chave: [parcelas]}. modo = 'documento' ou 'nota'."""
        valores = self._normalizar(chaves)
        if not valores:
            return {}
        expr = _NF if modo == "nota" else _DOC

        resultado: dict[int, list[ParcelaErp]] = defaultdict(list)
        marcas = ",".join(["%s"] * len(valores))
        sql = f"""
            SELECT p.pagparc_cod, p.pagparc_conta, p.pagparc_parcela, pg.pag_qtdparcelas,
                   p.pagparc_dtvencimento, p.pagparc_vlrdocumento, {_SALDO},
                   p.pagparc_dtpagamento, COALESCE(p.pagparc_nome, ''),
                   COALESCE(NULLIF(TRIM(pg.pag_numnf), ''), p.pagparc_nota, ''),
                   {_DOC}, {expr},
                   f.forn_cod, COALESCE(f.forn_nome, ''), COALESCE(f.forn_cnpj, '')
              FROM pagar_parcelas p
         LEFT JOIN pagar pg ON pg.pag_cod = p.pagparc_conta
         LEFT JOIN fornecedor f ON f.forn_cod = {_FORN}
             WHERE {expr} IN ({marcas})
          ORDER BY {expr}, p.pagparc_dtvencimento, p.pagparc_parcela
        """
        with self.conectar() as con, con.cursor() as cur:
            cur.execute(sql, valores)
            for r in cur.fetchall():
                saldo = Decimal(str(r[6] or 0)).quantize(_DOIS)
                chave = int(r[11] or 0)
                resultado[chave].append(ParcelaErp(
                    cod=r[0], conta=int(r[1] or 0), parcela=r[2] or 0, qtd_parcelas=r[3] or 0,
                    vencimento=r[4] if isinstance(r[4], date) else None,
                    valor_documento=Decimal(str(r[5] or 0)).quantize(_DOIS),
                    saldo=saldo,
                    pago=r[7] is not None or saldo <= Decimal("0.009"),
                    nome=(r[8] or "").strip(), nota=str(r[9] or "").strip(),
                    documento=int(r[10] or 0),
                    fornecedor_cod=int(r[12] or 0),
                    fornecedor_nome=(r[13] or "").strip(),
                    fornecedor_cnpj=_digitos(r[14]),
                ))
        return dict(resultado)

    # Compatibilidade com chamadas antigas
    def parcelas_dos_documentos(self, documentos: Iterable[Any]) -> dict[int, list[ParcelaErp]]:
        return self.parcelas_por_chaves(documentos, "documento")
