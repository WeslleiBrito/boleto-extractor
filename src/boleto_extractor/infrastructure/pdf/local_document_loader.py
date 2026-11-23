from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np
import pymupdf

from boleto_extractor.core.config import settings
from boleto_extractor.core.exceptions import DocumentLoadError
from boleto_extractor.core.types import ImageArray
from boleto_extractor.infrastructure.pdf.pdf_senha import senhas_pdf


class LocalDocumentLoader:
    """Carrega documentos PDF e imagens diretamente na memória."""

    def __init__(self, dpi: int | None = None) -> None:
        self._dpi = dpi or settings.dpi

    def carregar(self, arquivo: Path) -> Iterator[ImageArray]:
        arquivo = arquivo.resolve()

        self._validar_arquivo(arquivo)

        extensao = arquivo.suffix.lower()

        if extensao == ".pdf":
            yield from self._carregar_pdf(arquivo)
        else:
            yield self._carregar_imagem(arquivo)

    def _validar_arquivo(self, arquivo: Path) -> None:
        if not arquivo.exists():
            raise DocumentLoadError(f"Arquivo não encontrado: {arquivo}")

        if not arquivo.is_file():
            raise DocumentLoadError(f"O caminho informado não é um arquivo: {arquivo}")

        if arquivo.suffix.lower() not in settings.supported_extensions:
            raise DocumentLoadError(f"Formato não suportado: {arquivo.suffix}")

    def _carregar_pdf(self, arquivo: Path) -> Iterator[ImageArray]:
        try:
            with senhas_pdf.abrir(arquivo) as documento:
                if documento.page_count == 0:
                    raise DocumentLoadError("O documento PDF não possui páginas.")

                for pagina in documento:
                    pixmap = pagina.get_pixmap(
                        dpi=self._dpi,
                        colorspace=pymupdf.csRGB,
                        alpha=False,
                    )
                    imagem = np.frombuffer(pixmap.samples, dtype=np.uint8)
                    imagem = imagem.reshape(pixmap.height, pixmap.width, 3)
                    yield np.ascontiguousarray(imagem)

        except DocumentLoadError:
            raise  # inclui PdfProtegidoError

        except Exception as exc:
            raise DocumentLoadError(
                f"Não foi possível processar o PDF: {arquivo.name}"
            ) from exc

    def _carregar_imagem(self, arquivo: Path) -> ImageArray:
        try:
            dados = np.fromfile(arquivo, dtype=np.uint8)
            imagem = cv2.imdecode(dados, cv2.IMREAD_COLOR)

            if imagem is None:
                raise DocumentLoadError(f"Não foi possível decodificar: {arquivo.name}")

            imagem_rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
            return np.ascontiguousarray(imagem_rgb)

        except DocumentLoadError:
            raise

        except Exception as exc:
            raise DocumentLoadError(f"Falha ao carregar a imagem: {arquivo.name}") from exc
