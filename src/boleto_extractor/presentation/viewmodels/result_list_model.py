from dataclasses import dataclass
from datetime import date
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

from boleto_extractor.application.services.matching_service import (
    ROTULOS,
    ResultadoSincronizacao,
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
    "beneficiario", "beneficiarioDoc", "situacao", "beneficiarioDetalhe", "protegido",
    # Sincronização com o ERP
    "elegivel", "documentoErp", "vencimentoTexto", "vencimentoIso", "vencimentoEditavel",
    "erroDocumento", "erroData", "statusErp", "statusErpTexto", "parcelaErp", "detalheErp",
)
_BASE = Qt.ItemDataRole.UserRole.value + 1
_VAZIA = DadosEmpresa()
MSG_PROTEGIDO = "🔒 PDF protegido por senha. Clique em 🔒 Senha para informar."


@dataclass(slots=True)
class LinhaResultado:
    job_id: int
    caminho: Path
    pagina: int | None = None
    status: str = ExtractionStatus.PENDING.value
    tipo: str = ""
    emissor: str = ""
    vencimento: str = ""                      # texto exibido (formatar_data)
    valor: Decimal | None = None
    linha: str = ""
    codigo: str = ""
    mensagem: str = "Na fila…"
    beneficiario: Beneficiario | None = None
    protegido: bool = False
    # ---- Sincronização ----
    vencimento_data: date | None = None       # data extraída
    vencimento_travado: bool = False          # True = veio do fator do código (confiável)
    vencimento_manual: date | None = None     # digitada/escolhida no calendário
    documento_erp: int | None = None          # pagparc_documento
    erro_documento: bool = False
    erro_data: bool = False
    sincronizacao: ResultadoSincronizacao | None = None

    @property
    def empresa(self) -> DadosEmpresa:
        if self.beneficiario and self.beneficiario.empresa:
            return self.beneficiario.empresa
        return _VAZIA

    @property
    def beneficiario_doc(self) -> str:
        """CPF/CNPJ do beneficiário (não confundir com documento_erp)."""
        return self.beneficiario.documento_formatado if self.beneficiario else ""

    @property
    def chave(self) -> str:
        """Identificador único da linha para a sincronização."""
        return f"{self.job_id}:{self.pagina or 0}:{self.codigo}"

    @property
    def elegivel(self) -> bool:
        return self.status == ExtractionStatus.SUCCESS.value and bool(self.codigo)

    @property
    def vencimento_efetivo(self) -> date | None:
        if self.vencimento_travado:
            return self.vencimento_data
        return self.vencimento_manual or self.vencimento_data

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

        venc = item.vencimento_efetivo
        s = item.sincronizacao
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
            "beneficiarioDoc": item.beneficiario_doc,
            "situacao": item.empresa.situacao_cadastral,
            "protegido": item.protegido,
            "elegivel": item.elegivel,
            "documentoErp": str(item.documento_erp) if item.documento_erp is not None else "",
            "vencimentoTexto": venc.strftime("%d/%m/%Y") if venc else "",
            "vencimentoIso": venc.isoformat() if venc else "",
            "vencimentoEditavel": item.elegivel and not item.vencimento_travado,
            "erroDocumento": item.erro_documento,
            "erroData": item.erro_data,
            "statusErp": s.status.value if s else "",
            "statusErpTexto": ROTULOS[s.status] if s else "",
            "parcelaErp": s.parcela.rotulo if s and s.parcela else "",
            "detalheErp": s.detalhe if s else "",
        }
        return valores[campo]

    def _linha_do_job(self, job_id: int, **filtro: object) -> int | None:
        return next(
            (
                i for i, item in enumerate(self._itens)
                if item.job_id == job_id
                and all(getattr(item, k) == v for k, v in filtro.items())
            ),
            None,
        )

    def _notificar(self, linha: int) -> None:
        indice = self.index(linha)
        self.dataChanged.emit(indice, indice)

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
        linha = self._linha_do_job(job_id, status=ExtractionStatus.PENDING.value)
        if linha is None or not resultados:
            return

        primeiro, *resto = resultados
        self._preencher(self._itens[linha], primeiro)
        self._notificar(linha)

        if resto:
            self.beginInsertRows(QModelIndex(), linha + 1, linha + len(resto))
            for deslocamento, resultado in enumerate(resto, start=1):
                item = LinhaResultado(job_id=job_id, caminho=resultado.arquivo)
                self._preencher(item, resultado)
                self._itens.insert(linha + deslocamento, item)
            self.endInsertRows()

    # ---------------- PDF protegido ----------------
    def marcar_protegido(self, job_id: int) -> None:
        linha = self._linha_do_job(job_id, status=ExtractionStatus.PENDING.value)
        if linha is None:
            return
        item = self._itens[linha]
        item.status = ExtractionStatus.REVIEW.value
        item.mensagem = MSG_PROTEGIDO
        item.protegido = True
        self._notificar(linha)

    def reabrir(self, job_id: int) -> None:
        """Volta o item protegido para a fila de processamento."""
        linha = self._linha_do_job(job_id, protegido=True)
        if linha is None:
            return
        item = self._itens[linha]
        item.status = ExtractionStatus.PENDING.value
        item.mensagem = "Na fila…"
        item.protegido = False
        self._notificar(linha)

    def item(self, linha: int) -> LinhaResultado | None:
        return self._itens[linha] if 0 <= linha < len(self._itens) else None

    def _preencher(self, item: LinhaResultado, resultado: ExtractionResult) -> None:
        item.status = resultado.status.value
        item.pagina = resultado.pagina
        item.mensagem = " | ".join(resultado.mensagens)
        item.beneficiario = resultado.beneficiario
        item.protegido = False
        item.sincronizacao = None  # documento_erp e data manual são preservados

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
            item.vencimento_data = d.vencimento
            # Só o fator de vencimento da cobrança é confiável o bastante para travar
            item.vencimento_travado = (
                boleto.tipo == BoletoType.BANK_SLIP
                and d.vencimento is not None
                and not d.vencimento_estimado
            )

    # ---------------- Sincronização ----------------
    def alterar(self, linha: int, **campos: object) -> None:
        item = self.item(linha)
        if item is None:
            return
        for nome, valor in campos.items():
            setattr(item, nome, valor)
        self._notificar(linha)

    def aplicar_sincronizacao(self, por_chave: dict[str, ResultadoSincronizacao]) -> None:
        for i, item in enumerate(self._itens):
            if (r := por_chave.get(item.chave)) is not None:
                item.sincronizacao = r
                self._notificar(i)

    def contar_erp(self, status: str) -> int:
        return sum(
            1 for i in self._itens if i.sincronizacao and i.sincronizacao.status.value == status
        )

    # ---------------- Utilitários ----------------
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
