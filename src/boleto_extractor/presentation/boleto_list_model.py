from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt

from boleto_extractor.application.services.matching_service import ROTULOS, ResultadoCruzamento


@dataclass(slots=True)
class LinhaBoleto:
    arquivo: str
    codigo_barras: str
    linha_digitavel: str
    valor: Decimal | None
    vencimento: date | None = None
    origem_vencimento: str = ""     # 'codigo' | 'pdf' | 'manual' | ''
    documento: int | None = None
    resultado: ResultadoCruzamento | None = None
    erro_documento: bool = False
    erro_data: bool = False

    @property
    def tipo(self) -> str:
        return "Arrecadação" if self.codigo_barras.startswith("8") else "Cobrança"


def _moeda(v: Decimal | None) -> str:
    if v is None:
        return "--"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class BoletoListModel(QAbstractListModel):
    _NOMES = [
        "arquivo", "tipo", "linhaDigitavel", "valor", "vencimento", "origemVencimento",
        "documento", "status", "statusTexto", "parcela", "detalhe", "erroDocumento", "erroData",
    ]
    ROLES = {Qt.UserRole + i + 1: n for i, n in enumerate(_NOMES)}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._itens: list[LinhaBoleto] = []

    # ---------- Qt ----------
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._itens)

    def roleNames(self) -> dict[int, QByteArray]:
        return {r: QByteArray(n.encode()) for r, n in self.ROLES.items()}

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        it = self._itens[index.row()]
        nome = self.ROLES.get(role)
        res = it.resultado
        match nome:
            case "arquivo": return it.arquivo
            case "tipo": return it.tipo
            case "linhaDigitavel": return it.linha_digitavel
            case "valor": return _moeda(it.valor)
            case "vencimento": return it.vencimento.strftime("%d/%m/%Y") if it.vencimento else ""
            case "origemVencimento": return it.origem_vencimento
            case "documento": return str(it.documento) if it.documento else ""
            case "status": return res.status.value if res else ""
            case "statusTexto": return ROTULOS[res.status] if res else "Pendente"
            case "parcela": return res.parcela.rotulo if res and res.parcela else ""
            case "detalhe": return res.detalhe if res else ""
            case "erroDocumento": return it.erro_documento
            case "erroData": return it.erro_data
        return None

    # ---------- API ----------
    @property
    def itens(self) -> list[LinhaBoleto]:
        return self._itens

    def adicionar(self, linhas: list[LinhaBoleto]) -> None:
        existentes = {i.codigo_barras for i in self._itens}
        novas = [l for l in linhas if l.codigo_barras not in existentes]
        if not novas:
            return
        ini = len(self._itens)
        self.beginInsertRows(QModelIndex(), ini, ini + len(novas) - 1)
        self._itens.extend(novas)
        self.endInsertRows()

    def remover(self, row: int) -> None:
        if 0 <= row < len(self._itens):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._itens[row]
            self.endRemoveRows()

    def limpar(self) -> None:
        self.beginResetModel()
        self._itens.clear()
        self.endResetModel()

    def atualizar(self, row: int) -> None:
        idx = self.index(row)
        self.dataChanged.emit(idx, idx)

    def atualizar_todos(self) -> None:
        if self._itens:
            self.dataChanged.emit(self.index(0), self.index(len(self._itens) - 1))
