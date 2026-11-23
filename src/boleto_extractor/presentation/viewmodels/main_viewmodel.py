import csv
import re
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from boleto_extractor.application.services.matching_service import (
    ROTULOS,
    ItemSincronizacao,
    ResultadoSincronizacao,
    StatusSincronizacao,
)
from boleto_extractor.application.services.matching_service import (
    sincronizar as executar_sincronizacao,
)
from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.core.config import settings
from boleto_extractor.domain.entities.extraction_result import ExtractionResult
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus
from boleto_extractor.infrastructure.erp.erp_parcela_repository import ErpParcelaRepository
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
    "Documento ERP (pagparc_documento)", "Status ERP", "Parcela ERP", "Detalhe ERP",
]
_MAX_TENTATIVAS = 3


def _parse_data(texto: str) -> date | None:
    """Aceita dd/mm/aaaa, ddmmaaaa ou ISO aaaa-mm-dd (vindo do calendário)."""
    texto = (texto or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        try:
            return date.fromisoformat(texto)
        except ValueError:
            return None
    dig = re.sub(r"\D", "", texto)
    if len(dig) != 8:
        return None
    try:
        return datetime.strptime(dig, "%d%m%Y").date()
    except ValueError:
        return None


def _parse_documento(texto: str) -> int | None:
    """Número do documento (pagparc_documento). Mantém só dígitos."""
    dig = re.sub(r"\D", "", texto or "")
    return int(dig) if dig else None


# ---------------- Worker de sincronização ----------------
class _SinaisSincronizacao(QObject):
    concluido = Signal(object, str)  # (list[ResultadoSincronizacao], erro)


class _SincronizacaoWorker(QRunnable):
    def __init__(self, repo: ErpParcelaRepository, itens: list[ItemSincronizacao]) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.signals = _SinaisSincronizacao()
        self._repo = repo
        self._itens = itens

    def run(self) -> None:
        try:
            parcelas = self._repo.parcelas_dos_documentos(i.documento for i in self._itens)
            self.signals.concluido.emit(executar_sincronizacao(self._itens, parcelas), "")
        except Exception as exc:  # noqa: BLE001 - a interface nunca pode quebrar
            self.signals.concluido.emit([], f"Erro no banco: {exc}")


class MainViewModel(QObject):
    estadoChanged = Signal()
    notificacao = Signal(str)
    senhaChanged = Signal()
    sincronizandoChanged = Signal()
    erpChanged = Signal()

    def __init__(
        self,
        use_case: ExtractBoletoUseCase,
        repositorio: ErpParcelaRepository | None = None,
        parent: QObject | None = None,
        *,
        erp_ativo: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._use_case = use_case
        self._repo = repositorio
        self._erp_ativo = erp_ativo
        self._erp_ok = self._calcular_erp_ok()
        self._model = ResultListModel(self)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(settings.max_workers)
        self._workers: dict[int, ExtractionWorker] = {}
        self._proximo_id = 0
        self._total = 0
        self._concluidos = 0
        self._fila_senha: list[tuple[int, Path]] = []
        self._tentativas = 0
        self._erro_senha = ""
        self._atendidos = 0
        self._sincronizando = False
        self._worker_sinc: _SincronizacaoWorker | None = None

    # ---------------- ERP dinâmico ----------------
    def _calcular_erp_ok(self) -> bool:
        if self._repo is None:
            return False
        if self._erp_ativo is None:
            return True
        try:
            return bool(self._erp_ativo())
        except Exception:  # noqa: BLE001
            return False

    def _repo_ativo(self) -> ErpParcelaRepository | None:
        return self._repo if self._calcular_erp_ok() else None

    @Slot()
    def atualizarErp(self) -> None:
        """Chamado pelo QML após salvar/fechar as configurações."""
        if self._repo is not None and not self._sincronizando:
            for nome in ("recarregar", "fechar"):
                metodo = getattr(self._repo, nome, None)
                if callable(metodo):
                    try:
                        metodo()
                    except Exception:  # noqa: BLE001
                        pass
                    break
        novo = self._calcular_erp_ok()
        if novo != self._erp_ok:
            self._erp_ok = novo
            self.erpChanged.emit()

    @Property(bool, notify=erpChanged)
    def erpConfigurado(self) -> bool:
        return self._erp_ok

    # ---------------- Propriedades gerais ----------------
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
        if total:
            texto += f"   •   Total: {formatar_valor(total)}"
        ok = m.contar_erp(StatusSincronizacao.ENCONTRADO.value)
        pagos = m.contar_erp(StatusSincronizacao.JA_PAGO.value)
        if ok or pagos:
            texto += f"   •   🔗 ERP: {ok} encontrado(s), {pagos} já pago(s)"
        return texto

    @Property(int, notify=estadoChanged)
    def quantidade(self) -> int:
        return self._model.rowCount()

    # ---------------- Propriedades da sincronização ----------------
    @Property(bool, notify=sincronizandoChanged)
    def sincronizando(self) -> bool:
        return self._sincronizando

    def _set_sincronizando(self, valor: bool) -> None:
        self._sincronizando = valor
        self.sincronizandoChanged.emit()

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

    # ---------------- Edição para a sincronização ----------------
    @Slot(int, str)
    def definirDocumento(self, linha: int, texto: str) -> None:
        item = self._model.item(linha)
        if item is None or not item.elegivel or self._sincronizando:
            return
        novo = _parse_documento(texto)
        campos: dict[str, object] = {"erro_documento": False}
        if novo != item.documento_erp:
            campos |= {"documento_erp": novo, "sincronizacao": None}
        self._model.alterar(linha, **campos)
        self.estadoChanged.emit()

    @Slot(str, bool, result=int)
    def aplicarDocumentoTodos(self, texto: str, sobrescrever: bool) -> int:
        """Aplica o mesmo documento (pagparc_documento) a todos os boletos válidos."""
        if self._sincronizando:
            self.notificacao.emit("⚠ Aguarde o fim da sincronização com o ERP.")
            return 0
        novo = _parse_documento(texto)
        if novo is None:
            self.notificacao.emit("⚠ Informe o número do documento.")
            return 0

        alterados = preservados = 0
        for linha, it in enumerate(self._model.itens()):
            if not it.elegivel:
                continue
            if it.documento_erp is not None and it.documento_erp != novo and not sobrescrever:
                preservados += 1
                continue
            campos: dict[str, object] = {"erro_documento": False}
            if it.documento_erp != novo:
                campos |= {"documento_erp": novo, "sincronizacao": None}
                alterados += 1
            self._model.alterar(linha, **campos)

        if not alterados and not preservados:
            self.notificacao.emit("Nenhum boleto válido para receber o documento.")
        else:
            extra = f" ({preservados} já preenchido(s) mantido(s))" if preservados else ""
            self.notificacao.emit(f"📄 Documento {novo} aplicado a {alterados} item(ns){extra}")
        self.estadoChanged.emit()
        return alterados

    @Slot(int, str)
    def definirVencimento(self, linha: int, texto: str) -> None:
        item = self._model.item(linha)
        if item is None or not item.elegivel or item.vencimento_travado or self._sincronizando:
            return
        digitos = re.sub(r"\D", "", texto or "")
        nova = _parse_data(texto)
        if digitos and nova is None:
            self._model.alterar(linha, erro_data=True)
            self.notificacao.emit(f"⚠ Data inválida na linha {linha + 1}")
            return
        campos: dict[str, object] = {"erro_data": False}
        if nova != item.vencimento_manual:
            campos |= {"vencimento_manual": nova, "sincronizacao": None}
        self._model.alterar(linha, **campos)
        self.estadoChanged.emit()

    # ---------------- Sincronização ----------------
    @Slot()
    def sincronizar(self) -> None:
        self.atualizarErp()
        repo = self._repo_ativo()
        if repo is None:
            if self._repo is None:
                self.notificacao.emit("⛔ Repositório do ERP não inicializado (verifique o app.py).")
            else:
                self.notificacao.emit(
                    "⚠ Marque \"Integrar com o banco MySQL do ERP\" em ⚙ e salve antes de sincronizar."
                )
            return
        if self._sincronizando or self.processando:
            return

        elegiveis = [(i, it) for i, it in enumerate(self._model.itens()) if it.elegivel]
        if not elegiveis:
            self.notificacao.emit("Nenhum boleto válido para sincronizar.")
            return

        pendentes = sem_valor = 0
        itens: list[ItemSincronizacao] = []
        for linha, it in elegiveis:
            if it.valor is None:
                sem_valor += 1
                continue
            venc = it.vencimento_efetivo
            erro_doc, erro_data = it.documento_erp is None, venc is None
            self._model.alterar(linha, erro_documento=erro_doc, erro_data=erro_data)
            if erro_doc or erro_data:
                pendentes += 1
                continue
            itens.append(ItemSincronizacao(it.chave, it.documento_erp, venc, it.valor))

        if pendentes:
            self.notificacao.emit(
                f"⚠ {pendentes} linha(s) sem documento ou vencimento. Preencha os campos em vermelho."
            )
            return
        if not itens:
            self.notificacao.emit("Nenhum boleto com valor para sincronizar.")
            return

        self._set_sincronizando(True)
        aviso = f" ({sem_valor} sem valor ignorado(s))" if sem_valor else ""
        self.notificacao.emit(f"Sincronizando com o ERP…{aviso}")
        worker = _SincronizacaoWorker(repo, itens)
        worker.signals.concluido.connect(self._ao_sincronizar)
        self._worker_sinc = worker
        self._pool.start(worker)

    @Slot(object, str)
    def _ao_sincronizar(self, resultados: list[ResultadoSincronizacao], erro: str) -> None:
        self._worker_sinc = None
        self._set_sincronizando(False)
        if erro:
            self.notificacao.emit(f"⛔ {erro}")
            return
        self._model.aplicar_sincronizacao({r.chave: r for r in resultados})
        ok = sum(1 for r in resultados if r.status == StatusSincronizacao.ENCONTRADO)
        self.notificacao.emit(f"🔗 Sincronização concluída: {ok}/{len(resultados)} encontrado(s)")
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
        s = item.sincronizacao
        venc = item.vencimento_efetivo
        return [
            item.caminho.name, item.pagina or "", item.status, item.tipo,
            item.emissor, venc.strftime("%d/%m/%Y") if venc else item.vencimento,
            formatar_valor_csv(item.valor),
            formatar_linha(item.linha), item.codigo, item.mensagem,
            b.documento_formatado if b else "", b.tipo if b else "",
            e.razao_social, e.nome_fantasia, e.situacao_cadastral, e.municipio, e.uf,
            e.email, e.telefone, e.cnae_principal, e.porte_empresa,
            e.opcao_simples, e.opcao_mei,
            item.documento_erp if item.documento_erp is not None else "",
            ROTULOS[s.status] if s else "",
            s.parcela.rotulo if s and s.parcela else "",
            s.detalhe if s else "",
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
        if not self.processando and not self._sincronizando:
            self._model.limpar()
            self.pularTodasSenhas()
            self.estadoChanged.emit()
