from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.domain.entities.extraction_result import ExtractionResult
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus
from boleto_extractor.infrastructure.pdf.pdf_senha import senhas_pdf


class WorkerSignals(QObject):
    concluido = Signal(int, object)  # (job_id, tuple[ExtractionResult, ...])
    protegido = Signal(int, str)     # (job_id, caminho)


class ExtractionWorker(QRunnable):
    """Executa a extração fora da thread da interface."""

    def __init__(self, job_id: int, arquivo: Path, use_case: ExtractBoletoUseCase) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.signals = WorkerSignals()
        self._job_id = job_id
        self._arquivo = arquivo
        self._use_case = use_case

    def run(self) -> None:
        # PDF protegido sem senha conhecida: vai para a fila de senha, sem extrair
        if senhas_pdf.precisa_senha(self._arquivo):
            self.signals.protegido.emit(self._job_id, str(self._arquivo))
            return

        try:
            resultados = self._use_case.executar(self._arquivo)
        except Exception as exc:  # noqa: BLE001 - a interface nunca pode quebrar
            resultados = (
                ExtractionResult(
                    arquivo=self._arquivo,
                    status=ExtractionStatus.ERROR,
                    mensagens=(f"Erro inesperado: {exc}",),
                ),
            )
        self.signals.concluido.emit(self._job_id, resultados)
