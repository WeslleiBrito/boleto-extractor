import json
import sqlite3
import threading
import time
from dataclasses import asdict, fields
from pathlib import Path

from boleto_extractor.core.config import settings
from boleto_extractor.domain.entities.beneficiario import DadosEmpresa

STATUS_OK = "ok"
STATUS_NAO_ENCONTRADO = "nao_encontrado"
_CAMPOS = {f.name for f in fields(DadosEmpresa)}


class SqliteCnpjCache:
    """Cache persistente de consultas. Se o SQLite falhar, opera como sem cache."""

    def __init__(self, caminho: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._con: sqlite3.Connection | None = None
        try:
            arq = caminho or settings.data_dir / "cache_cnpj.sqlite"
            arq.parent.mkdir(parents=True, exist_ok=True)
            self._con = sqlite3.connect(arq, check_same_thread=False)
            self._con.execute(
                "CREATE TABLE IF NOT EXISTS cnpj ("
                " cnpj TEXT PRIMARY KEY, status TEXT NOT NULL,"
                " dados TEXT, consultado_em REAL NOT NULL)"
            )
            self._con.commit()
        except Exception:
            self._con = None

    def obter(self, cnpj: str) -> tuple[str, DadosEmpresa | None] | None:
        """None = não está em cache (ou expirou)."""
        if self._con is None:
            return None
        try:
            with self._lock:
                row = self._con.execute(
                    "SELECT status, dados, consultado_em FROM cnpj WHERE cnpj = ?", (cnpj,)
                ).fetchone()
            if not row:
                return None
            status, dados, quando = str(row[0]), row[1], float(row[2])
            ttl = settings.cache_ttl_ok if status == STATUS_OK else settings.cache_ttl_nao_encontrado
            if time.time() - quando > ttl:
                return None
            if status != STATUS_OK:
                return status, None
            bruto = json.loads(dados or "{}")
            return status, DadosEmpresa(**{k: str(v) for k, v in bruto.items() if k in _CAMPOS})
        except Exception:
            return None

    def salvar(self, cnpj: str, status: str, dados: DadosEmpresa | None) -> None:
        if self._con is None:
            return
        try:
            payload = json.dumps(asdict(dados) if dados else {}, ensure_ascii=False)
            with self._lock:
                self._con.execute(
                    "INSERT OR REPLACE INTO cnpj VALUES (?, ?, ?, ?)",
                    (cnpj, status, payload, time.time()),
                )
                self._con.commit()
        except Exception:
            pass
