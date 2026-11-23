import csv
from pathlib import Path

from PySide6.QtCore import Property, QObject, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.core.config import settings
from boleto_extractor.domain.entities.extraction_result import ExtractionResult
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus
from boleto_extractor.infrastructure.pdf.pdf_senha import senhas_pdf
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
_MAX_TENTATIVAS = 3


class MainViewModel(QObject):
    estadoChanged = Signal()
    notificacao = Signal(str)
    senhaChanged = Signal()

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
        # Fila de PDFs protegidos aguardando senha
        self._fila_senha: list[tuple[int, Path]] = []
        self._tentativas = 0
        self._erro_senha = ""
        self._atendidos = 0  # para "Arquivo X de Y"

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

    # ---------------- Propriedades da janela de senha ----------------
    @Property(bool, notify=senhaChanged)
    def senhaPendente(self) -> bool:
        return bool(self._fila_senha)

    @Property(str, notify=senhaChanged)
    def senhaArquivo(self) -> str:
        return self._fila_senha[0][1].name if self._fila_senha else ""

    @Property(str, notify=senhaChanged)
    def senhaPosicao(self) -> str:
        if not self._fila_senha:
            return ""
        total = self._atendidos + len(self._fila_senha)
        return f"Arquivo {self._atendidos + 1} de {total}"

    @Property(int, notify=senhaChanged)
    def senhaRestantes(self) -> int:
        return len(self._fila_senha)

    @Property(str, notify=senhaChanged)
    def senhaErro(self) -> str:
        return self._erro_senha

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
            self._iniciar(job_id, arquivo)

        self.estadoChanged.emit()

    def _iniciar(self, job_id: int, arquivo: Path) -> None:
        worker = ExtractionWorker(job_id, arquivo, self._use_case)
        worker.signals.concluido.connect(self._ao_concluir)
        worker.signals.protegido.connect(self._ao_protegido)
        self._workers[job_id] = worker
        self._total += 1
        self._pool.start(worker)

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

    def _contar_concluido(self) -> None:
        self._concluidos += 1
        if self._concluidos >= self._total:
            self._total = self._concluidos = 0
            self.notificacao.emit("Processamento concluído.")
        self.estadoChanged.emit()

    @Slot(int, object)
    def _ao_concluir(self, job_id: int, resultados: tuple[ExtractionResult, ...]) -> None:
        self._workers.pop(job_id, None)
        self._model.atualizar(job_id, resultados)
        self._contar_concluido()

    @Slot(int, str)
    def _ao_protegido(self, job_id: int, caminho: str) -> None:
        self._workers.pop(job_id, None)
        self._model.marcar_protegido(job_id)
        if all(j != job_id for j, _ in self._fila_senha):
            self._fila_senha.append((job_id, Path(caminho)))
            self.senhaChanged.emit()
        self._contar_concluido()

    # ---------------- Fila de senha ----------------
    def _reprocessar(self, job_id: int, arquivo: Path) -> None:
        self._model.reabrir(job_id)
        self._iniciar(job_id, arquivo)
        self.estadoChanged.emit()

    def _avancar(self) -> None:
        self._fila_senha.pop(0)
        self._atendidos += 1
        self._tentativas = 0
        self._erro_senha = ""
        if not self._fila_senha:
            self._atendidos = 0
        self.senhaChanged.emit()

    @Slot(str, bool, bool, result=bool)
    def informarSenha(self, senha: str, usar_nos_proximos: bool, lembrar: bool) -> bool:
        if not self._fila_senha:
            return False
        job_id, arquivo = self._fila_senha[0]

        if not senhas_pdf.informar(arquivo, senha, usar_nos_proximos, lembrar):
            self._tentativas += 1
            if self._tentativas >= _MAX_TENTATIVAS:
                self.notificacao.emit(f"🔒 {arquivo.name}: tentativas esgotadas. Arquivo pulado.")
                self._avancar()
            else:
                self._erro_senha = f"Senha incorreta ({self._tentativas}/{_MAX_TENTATIVAS})."
                self.senhaChanged.emit()
            return False

        self._avancar()
        self._reprocessar(job_id, arquivo)
        abertos = 1

        # A mesma senha pode abrir os próximos arquivos do mesmo emissor
        if usar_nos_proximos:
            for item in list(self._fila_senha):
                if not senhas_pdf.precisa_senha(item[1]):
                    self._fila_senha.remove(item)
                    self._atendidos += 1
                    self._reprocessar(*item)
                    abertos += 1
            if not self._fila_senha:
                self._atendidos = 0
            self.senhaChanged.emit()

        self.notificacao.emit(f"🔓 {abertos} arquivo(s) desbloqueado(s)")
        return True

    @Slot()
    def pularSenha(self) -> None:
        if self._fila_senha:
            self._avancar()

    @Slot()
    def pularTodasSenhas(self) -> None:
        self._fila_senha.clear()
        self._atendidos = 0
        self._tentativas = 0
        self._erro_senha = ""
        self.senhaChanged.emit()

    @Slot(int)
    def informarSenhaLinha(self, linha: int) -> None:
        """Chamado pelo botão 🔒 da tabela, para tentar de novo um arquivo pulado."""
        item = self._model.item(linha)
        if item is None or not item.protegido:
            return
        self._fila_senha = [(j, a) for j, a in self._fila_senha if j != item.job_id]
        self._fila_senha.insert(0, (item.job_id, item.caminho))
        self._tentativas = 0
        self._erro_senha = ""
        self.senhaChanged.emit()

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
            self.pularTodasSenhas()
            self.estadoChanged.emit()
