from pathlib import Path

from boleto_extractor.infrastructure.pdf.pdf_senha import senhas_pdf


class PyMuPdfTextExtractor:
    """Extrai a camada de texto de PDFs digitais. Imagens/PDF escaneado retornam vazio."""

    def extrair_paginas(self, arquivo: Path) -> tuple[str, ...]:
        if arquivo.suffix.lower() != ".pdf":
            return ()
        try:
            with senhas_pdf.abrir(arquivo) as doc:
                return tuple(str(p.get_text()) for p in doc)
        except Exception:
            return ()
