from __future__ import annotations

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
    documento: int = 0  # pagparc_documento

    @property
    def rotulo(self) -> str:
        return f"Parc. {self.parcela}/{self.qtd_parcelas or '?'} (#{self.cod})"


class ErpParcelaRepository:
    """Somente leitura no ERP. A sincronização filtra por pagparc_documento."""

    def __init__(self, config: Callable[[], dict[str, Any]], senha: Callable[[], str]) -> None:
        self._config = config
        self._senha = senha

    def _conectar(self):
        import pymysql

        cfg = self._config()
        return pymysql.connect(
            host=cfg["db_host"], port=int(cfg["db_porta"]), user=cfg["db_usuario"],
            password=self._senha(), database=cfg["db_banco"] or None,
            charset="latin1", ssl={"ssl": {}} if cfg.get("db_ssl") else None,
            connect_timeout=5, read_timeout=30,
        )

    @staticmethod
    def _normalizar(documentos: Iterable[Any]) -> list[int]:
        saida: set[int] = set()
        for d in documentos:
            try:
                saida.add(int(str(d).strip()))
            except (TypeError, ValueError):
                continue
        return sorted(saida)

    def parcelas_dos_documentos(self, documentos: Iterable[Any]) -> dict[int, list[ParcelaErp]]:
        docs = self._normalizar(documentos)
        if not docs:
            return {}

        resultado: dict[int, list[ParcelaErp]] = defaultdict(list)
        marcas = ",".join(["%s"] * len(docs))
        sql = f"""
            SELECT p.pagparc_cod, p.pagparc_conta, p.pagparc_parcela, pg.pag_qtdparcelas,
                   p.pagparc_dtvencimento, p.pagparc_vlrdocumento, {_SALDO},
                   p.pagparc_dtpagamento, COALESCE(p.pagparc_nome, ''),
                   COALESCE(NULLIF(p.pagparc_nota, ''), pg.pag_numnf, ''),
                   {_DOC}
              FROM pagar_parcelas p
         LEFT JOIN pagar pg ON pg.pag_cod = p.pagparc_conta
             WHERE {_DOC} IN ({marcas})
          ORDER BY p.pagparc_documento, p.pagparc_dtvencimento, p.pagparc_parcela
        """
        with self._conectar() as con, con.cursor() as cur:
            cur.execute(sql, docs)
            for r in cur.fetchall():
                saldo = Decimal(str(r[6] or 0)).quantize(_DOIS)
                doc = int(r[10] or 0)
                resultado[doc].append(ParcelaErp(
                    cod=r[0], conta=int(r[1] or 0), parcela=r[2] or 0, qtd_parcelas=r[3] or 0,
                    vencimento=r[4] if isinstance(r[4], date) else None,
                    valor_documento=Decimal(str(r[5] or 0)).quantize(_DOIS),
                    saldo=saldo,
                    pago=r[7] is not None or saldo <= Decimal("0.009"),
                    nome=(r[8] or "").strip(), nota=(r[9] or "").strip(),
                    documento=doc,
                ))
        return dict(resultado)
