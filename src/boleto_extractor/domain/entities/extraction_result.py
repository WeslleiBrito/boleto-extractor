from dataclasses import dataclass
from pathlib import Path

from boleto_extractor.domain.entities.beneficiario import Beneficiario
from boleto_extractor.domain.entities.boleto import Boleto
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    arquivo: Path
    status: ExtractionStatus
    boleto: Boleto | None = None
    confianca: float | None = None
    mensagens: tuple[str, ...] = ()
    pagina: int | None = None
    beneficiario: Beneficiario | None = None

    def __post_init__(self) -> None:
        if self.confianca is not None and not 0.0 <= self.confianca <= 1.0:
            raise ValueError("A confiança deve estar entre 0.0 e 1.0.")

        if self.status == ExtractionStatus.SUCCESS and self.boleto is None:
            raise ValueError("Uma extração bem-sucedida precisa possuir um boleto.")
