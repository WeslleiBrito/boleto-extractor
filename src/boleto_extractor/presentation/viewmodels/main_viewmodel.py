import csv
from pathlib import Path

from PySide6.QtCore import Property, QObject, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.core.config import settings
from boleto_extractor.domain.entities.extraction_result import ExtractionResult
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus
from boleto_extractor.presentation.formatting import (
    formatar_linha,
    formatar_valor,
    formatar_valor_csv,
)
from boleto_extractor.presentation.viewmodels.extraction_worker import ExtractionWorker
from boleto_extractor.presentation.viewmodels.result_list_model import (
    LinhaResultado,
    ResultListModel,
)

_CABECALHO = [
    "Arquivo", "Página", "Status", "Tipo", "Emissor", "Vencimento",
    "Valor", "Linha digitável", "Código de barras", "Mensagem",
    "Beneficiário documento", "Beneficiário tipo", "Razão social", "Nome fantasia",
    "Situação cadastral", "Município", "UF", "E-mail", "Telefone",
    "CNAE principal", "Porte", "Opção Simples", "Opção MEI",
]


class MainViewModel(QObject):
    estadoChanged = Signal()
    notificacao = Signal(str)

    def __init__(self, use_case: ExtractBoletoUseCase, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._use_case = use_case
        self._model = ResultListModel(self)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(settings.max_workers)
        self._workers: dict[int, ExtractionWorker] = {}
        self._proximo_id = 0
        self._total = 0
        self._concluidos = 0

    @Property(QObject, constant=True)
    def resultados(self) -> ResultListModel:
        return self._model

    @Property(bool, notify=estadoChanged)
    def processando(self) -> bool:
        return self._total > 0

    @Property(str, notify=estadoChanged)
    def progresso(self) -> str:
        return f"Processando {self._concluidos} de {self._total} arquivo(s)…" if self._total else ""

    @Property(str, notify=estadoChanged)
    def resumo(self) -> str:
        m = self._model
        texto = (
            f"✔ {m.contar(ExtractionStatus.SUCCESS)}   "
            f"✖ {m.contar(ExtractionStatus.INVALID)}   "
            f"⚠ {m.contar(ExtractionStatus.REVIEW)}   "
            f"⛔ {m.contar(ExtractionStatus.ERROR)}"
        )
        total = m.total_valor()
        return f"{texto}   •   Total: {formatar_valor(total)}" if total else texto

    @Property(int, notify=estadoChanged)
    def quantidade(self) -> int:
        return self._model.rowCount()

    def _novo_id(self) -> int:
        job_id = self._proximo_id
        self._proximo_id += 1
        return job_id

    # ---------------- Entrada por código (leitor USB / digitação) ----------------
    @Slot(str, result=bool)
    def adicionarCodigo(self, texto: str) -> bool:
        resultado = self._use_case.executar_codigo(texto)

        if resultado.status != ExtractionStatus.SUCCESS or resultado.boleto is None:
            motivo = " | ".join(resultado.mensagens) or "Código inválido."
            self.notificacao.emit(f"✖ {motivo}")
            return False

        codigo = resultado.boleto.codigo_barras or ""
        if self._model.contem_codigo(codigo):
            self.notificacao.emit("⚠ Esse boleto já está na lista.")
            return False

        self._model.adicionar_resultado(self._novo_id(), resultado)
        self.estadoChanged.emit()

        detalhes = resultado.boleto.detalhes
        valor = formatar_valor(detalhes.valor) if detalhes else ""
        self.notificacao.emit(f"✔ Boleto adicionado {valor}".strip())
        return True

    # ---------------- Entrada por arquivos ----------------
    @Slot("QVariantList")
    def adicionarArquivos(self, urls: list[object]) -> None:
        arquivos = self._expandir(urls)
        if not arquivos:
            self.notificacao.emit("Nenhum arquivo suportado (PDF, PNG, JPG).")
            return

        for arquivo in arquivos:
            job_id = self._novo_id()
            self._model.adicionar(job_id, arquivo)

            worker = ExtractionWorker(job_id, arquivo, self._use_case)
            worker.signals.concluido.connect(self._ao_concluir)
            self._workers[job_id] = worker
            self._total += 1
            self._pool.start(worker)

        self.estadoChanged.emit()

    def _expandir(self, urls: list[object]) -> list[Path]:
        extensoes = set(settings.supported_extensions)
        arquivos: list[Path] = []

        for item in urls:
            url = item if isinstance(item, QUrl) else QUrl(str(item))
            caminho = Path(url.toLocalFile()) if url.isLocalFile() else Path(str(item))

            if caminho.is_dir():
                arquivos.extend(
                    sorted(p for p in caminho.rglob("*") if p.suffix.lower() in extensoes)
                )
            elif caminho.suffix.lower() in extensoes:
                arquivos.append(caminho)

        return arquivos

    @Slot(int, object)
    def _ao_concluir(self, job_id: int, resultados: tuple[ExtractionResult, ...]) -> None:
        self._workers.pop(job_id, None)
        self._model.atualizar(job_id, resultados)
        self._concluidos += 1

        if self._concluidos >= self._total:
            self._total = self._concluidos = 0
            self.notificacao.emit("Processamento concluído.")

        self.estadoChanged.emit()

    # ---------------- Ações ----------------
    @Slot(str)
    def copiar(self, texto: str) -> None:
        if texto:
            QGuiApplication.clipboard().setText(texto)
            self.notificacao.emit("Linha digitável copiada!")

    @staticmethod
    def _linha_csv(item: LinhaResultado) -> list[object]:
        b = item.beneficiario
        e = item.empresa
        return [
            item.caminho.name, item.pagina or "", item.status, item.tipo,
            item.emissor, item.vencimento, formatar_valor_csv(item.valor),
            formatar_linha(item.linha), item.codigo, item.mensagem,
            b.documento_formatado if b else "", b.tipo if b else "",
            e.razao_social, e.nome_fantasia, e.situacao_cadastral, e.municipio, e.uf,
            e.email, e.telefone, e.cnae_principal, e.porte_empresa,
            e.opcao_simples, e.opcao_mei,
        ]

    @Slot(QUrl)
    def exportarCsv(self, url: QUrl) -> None:
        destino = Path(url.toLocalFile())
        try:
            with destino.open("w", newline="", encoding="utf-8-sig") as f:
                escritor = csv.writer(f, delimiter=";")
                escritor.writerow(_CABECALHO)
                for item in self._model.itens():
                    escritor.writerow(self._linha_csv(item))
            self.notificacao.emit(f"Exportado para {destino.name}")
        except OSError as exc:
            self.notificacao.emit(f"Falha ao exportar: {exc}")

    @Slot()
    def limpar(self) -> None:
        if not self.processando:
            self._model.limpar()
            self.estadoChanged.emit()
