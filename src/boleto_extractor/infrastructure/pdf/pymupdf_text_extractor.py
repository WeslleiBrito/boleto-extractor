from pathlib import Path

import pymupdf


class PyMuPdfTextExtractor:
    """Extrai a camada de texto de PDFs digitais. Imagens/PDF escaneado retornam vazio."""

    def extrair_paginas(self, arquivo: Path) -> tuple[str, ...]:
        if arquivo.suffix.lower() != ".pdf":
            return ()
        try:
            with pymupdf.open(arquivo) as doc:  # type: ignore[no-untyped-call]
                return tuple(str(p.get_text()) for p in doc)
        except Exception:
            return ()
