from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)

from boleto_extractor.domain.entities.beneficiario import Beneficiario, DadosEmpresa
from boleto_extractor.domain.entities.extraction_result import ExtractionResult
from boleto_extractor.domain.enums.boleto_type import BoletoType
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus
from boleto_extractor.presentation.formatting import (
    formatar_data,
    formatar_linha,
    formatar_valor,
)

TIPOS = {
    BoletoType.BANK_SLIP: "Cobrança",
    BoletoType.ARRECADACAO: "Arrecadação",
    BoletoType.UNKNOWN: "Desconhecido",
}

_CAMPOS = (
    "arquivo", "caminho", "pagina", "status", "tipo", "emissor", "vencimento",
    "valor", "linha", "linhaFormatada", "codigo", "mensagem",
    "beneficiario", "beneficiarioDoc", "situacao", "beneficiarioDetalhe",
)
_BASE = Qt.ItemDataRole.UserRole.value + 1
_VAZIA = DadosEmpresa()


@dataclass(slots=True)
class LinhaResultado:
    job_id: int
    caminho: Path
    pagina: int | None = None
    status: str = ExtractionStatus.PENDING.value
    tipo: str = ""
    emissor: str = ""
    vencimento: str = ""
    valor: Decimal | None = None
    linha: str = ""
    codigo: str = ""
    mensagem: str = "Na fila…"
    beneficiario: Beneficiario | None = None

    @property
    def empresa(self) -> DadosEmpresa:
        if self.beneficiario and self.beneficiario.empresa:
            return self.beneficiario.empresa
        return _VAZIA

    @property
    def documento(self) -> str:
        return self.beneficiario.documento_formatado if self.beneficiario else ""

    def detalhe_beneficiario(self) -> str:
        b = self.beneficiario
        if b is None:
            return ""
        e = self.empresa
        local = " / ".join(x for x in (e.municipio, e.uf) if x)
        pares = (
            (b.tipo, b.documento_formatado),
            ("Razão social", e.razao_social),
            ("Fantasia", e.nome_fantasia),
            ("Situação", e.situacao_cadastral),
            ("Local", local),
            ("Telefone", e.telefone),
            ("E-mail", e.email),
            ("CNAE", e.cnae_principal),
            ("Porte", e.porte_empresa),
            ("Simples", e.opcao_simples),
            ("MEI", e.opcao_mei),
        )
        linhas = [f"{k}: {v}" for k, v in pares if v]
        if b.confirmado_pelo_codigo:
            linhas.append("✔ CNPJ confirmado pelo código de barras")
        if b.tipo == "CNPJ" and b.empresa is None:
            linhas.append("Dados da empresa indisponíveis no momento")
        return "\n".join(linhas)


class ResultListModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._itens: list[LinhaResultado] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._itens)

    def roleNames(self) -> dict[int, QByteArray]:
        return {_BASE + i: QByteArray(nome.encode()) for i, nome in enumerate(_CAMPOS)}

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = 0) -> object:
        if not index.isValid():
            return None
        posicao = role - _BASE
        if not 0 <= posicao < len(_CAMPOS):
            return None

        item = self._itens[index.row()]
        campo = _CAMPOS[posicao]
        if campo == "beneficiarioDetalhe":
            return item.detalhe_beneficiario()

        valores: dict[str, object] = {
            "arquivo": item.caminho.name,
            "caminho": str(item.caminho),
            "pagina": item.pagina or 0,
            "status": item.status,
            "tipo": item.tipo,
            "emissor": item.emissor,
            "vencimento": item.vencimento,
            "valor": formatar_valor(item.valor),
            "linha": item.linha,
            "linhaFormatada": formatar_linha(item.linha),
            "codigo": item.codigo,
            "mensagem": item.mensagem,
            "beneficiario": item.beneficiario.nome if item.beneficiario else "",
            "beneficiarioDoc": item.documento,
            "situacao": item.empresa.situacao_cadastral,
        }
        return valores[campo]

    def adicionar(self, job_id: int, caminho: Path) -> None:
        linha = len(self._itens)
        self.beginInsertRows(QModelIndex(), linha, linha)
        self._itens.append(LinhaResultado(job_id=job_id, caminho=caminho))
        self.endInsertRows()

    def adicionar_resultado(self, job_id: int, resultado: ExtractionResult) -> None:
        """Insere um resultado já processado (ex.: código bipado no leitor)."""
        item = LinhaResultado(job_id=job_id, caminho=resultado.arquivo)
        self._preencher(item, resultado)
        linha = len(self._itens)
        self.beginInsertRows(QModelIndex(), linha, linha)
        self._itens.append(item)
        self.endInsertRows()

    def atualizar(self, job_id: int, resultados: tuple[ExtractionResult, ...]) -> None:
        linha = next(
            (
                i for i, item in enumerate(self._itens)
                if item.job_id == job_id and item.status == ExtractionStatus.PENDING.value
            ),
            None,
        )
        if linha is None or not resultados:
            return

        primeiro, *resto = resultados
        self._preencher(self._itens[linha], primeiro)
        indice = self.index(linha)
        self.dataChanged.emit(indice, indice)

        if resto:
            self.beginInsertRows(QModelIndex(), linha + 1, linha + len(resto))
            for deslocamento, resultado in enumerate(resto, start=1):
                item = LinhaResultado(job_id=job_id, caminho=resultado.arquivo)
                self._preencher(item, resultado)
                self._itens.insert(linha + deslocamento, item)
            self.endInsertRows()

    def _preencher(self, item: LinhaResultado, resultado: ExtractionResult) -> None:
        item.status = resultado.status.value
        item.pagina = resultado.pagina
        item.mensagem = " | ".join(resultado.mensagens)
        item.beneficiario = resultado.beneficiario

        boleto = resultado.boleto
        if boleto is None:
            return

        item.tipo = TIPOS[boleto.tipo]
        item.linha = boleto.linha_digitavel or ""
        item.codigo = boleto.codigo_barras or ""

        if boleto.detalhes:
            d = boleto.detalhes
            item.emissor = d.emissor
            item.valor = d.valor
            item.vencimento = formatar_data(d.vencimento, d.vencimento_estimado)

    def contem_codigo(self, codigo: str) -> bool:
        return any(item.codigo == codigo for item in self._itens)

    def limpar(self) -> None:
        self.beginResetModel()
        self._itens.clear()
        self.endResetModel()

    def contar(self, status: ExtractionStatus) -> int:
        return sum(1 for item in self._itens if item.status == status.value)

    def total_valor(self) -> Decimal:
        return sum(
            (i.valor for i in self._itens
             if i.valor is not None and i.status == ExtractionStatus.SUCCESS.value),
            Decimal(0),
        )

    def itens(self) -> tuple[LinhaResultado, ...]:
        return tuple(self._itens)
