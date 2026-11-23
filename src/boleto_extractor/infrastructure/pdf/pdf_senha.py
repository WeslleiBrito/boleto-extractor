from __future__ import annotations

import json
import threading
from pathlib import Path

import pymupdf

from boleto_extractor.core.exceptions import DocumentLoadError

_SERVICO = "BoletoExtractor-PDF"
_CHAVE = "senhas"
_MAX_LEMBRADAS = 30


class PdfProtegidoError(DocumentLoadError):
    """Nenhuma senha informada pelo usuário abre o PDF."""

    def __init__(self, arquivo: Path) -> None:
        super().__init__(f"PDF protegido por senha: {arquivo.name}")
        self.arquivo = arquivo


class SenhasPdf:
    """
    Guarda apenas senhas digitadas pelo usuário:
    - por arquivo (memória, só nesta sessão);
    - "usar nos próximos" (memória, só nesta sessão);
    - "lembrar" (cofre do Windows, somente se o usuário marcar).
    Nunca grava senha em log, CSV ou configuração exportada.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._por_arquivo: dict[str, str] = {}
        self._sessao: list[str] = []
        self._lembradas: list[str] = self._ler_cofre()

    @staticmethod
    def _chave(arquivo: Path | str) -> str:
        return str(Path(arquivo).resolve()).lower()

    # ---------------- Cofre do Windows ----------------
    @staticmethod
    def _ler_cofre() -> list[str]:
        try:
            import keyring
            return list(json.loads(keyring.get_password(_SERVICO, _CHAVE) or "[]"))
        except Exception:
            return []

    def _gravar_cofre(self) -> None:
        try:
            import keyring
            keyring.set_password(_SERVICO, _CHAVE, json.dumps(self._lembradas[:_MAX_LEMBRADAS]))
        except Exception:
            pass

    def esquecer_lembradas(self) -> None:
        with self._lock:
            self._lembradas = []
            self._sessao = []
            self._gravar_cofre()

    # ---------------- Abertura ----------------
    def _candidatas(self, arquivo: Path | str) -> list[str]:
        with self._lock:
            todas = [self._por_arquivo.get(self._chave(arquivo)), *self._sessao, *self._lembradas]
        return [s for s in dict.fromkeys(todas) if s]

    def abrir(self, arquivo: Path | str) -> pymupdf.Document:
        """Abre o PDF; se protegido, usa só senhas informadas. Lança PdfProtegidoError."""
        doc = pymupdf.open(arquivo)  # type: ignore[no-untyped-call]
        if not doc.needs_pass:
            return doc
        for senha in self._candidatas(arquivo):
            if doc.authenticate(senha):
                with self._lock:
                    self._por_arquivo[self._chave(arquivo)] = senha
                return doc
        doc.close()
        raise PdfProtegidoError(Path(arquivo))

    def precisa_senha(self, arquivo: Path | str) -> bool:
        if Path(arquivo).suffix.lower() != ".pdf":
            return False
        try:
            self.abrir(arquivo).close()
            return False
        except PdfProtegidoError:
            return True
        except Exception:
            return False  # outros erros são reportados pelo loader

    def informar(
        self,
        arquivo: Path | str,
        senha: str,
        usar_nos_proximos: bool = False,
        lembrar: bool = False,
    ) -> bool:
        """Testa a senha digitada. Só guarda se ela abrir o arquivo."""
        if not senha:
            return False
        try:
            with pymupdf.open(arquivo) as doc:  # type: ignore[no-untyped-call]
                if doc.needs_pass and not doc.authenticate(senha):
                    return False
        except Exception:
            return False

        with self._lock:
            self._por_arquivo[self._chave(arquivo)] = senha
            if usar_nos_proximos and senha not in self._sessao:
                self._sessao.insert(0, senha)
            if lembrar:
                self._lembradas = [senha, *(s for s in self._lembradas if s != senha)]
                self._gravar_cofre()
        return True


senhas_pdf = SenhasPdf()
